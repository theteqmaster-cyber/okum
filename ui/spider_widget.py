import math
import random
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, QSettings
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QPen,
    QBrush, QCursor, QPainterPath, QAction, QGuiApplication, QPixmap
)
from ui.orb_widget import FloatingOrb

# Alias for full system backward compatibility
FloatingSpider = FloatingOrb

class _LegacySpider(QWidget):
    """
    Okum Desktop Spider Mascot:
    A cute, small articulated spider that crawls unpredictably across the desktop
    with realistic leg gait, idle twitching, and interactive drag/click response.
    """
    def __init__(self, toggle_callback, open_music_callback=None, toggle_board_callback=None, activity_callback=None, toggle_mini_music_callback=None, exit_callback=None):
        super().__init__()
        self.toggle_callback = toggle_callback
        self.open_music_callback = open_music_callback
        self.toggle_board_callback = toggle_board_callback
        self.activity_callback = activity_callback
        self.toggle_mini_music_callback = toggle_mini_music_callback
        self.exit_callback = exit_callback

        # Frameless, translucent desktop tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        # Mascot dimensions (96x96 provides ample room for articulated legs while remaining neat)
        self.setFixedSize(96, 96)

        # Crawling & Behavior State
        self.state = 'IDLE'           # 'IDLE', 'TURNING', 'CRAWLING', 'DRAGGING'
        self.free_roam_enabled = True # Can be toggled via right-click
        self.is_look_around = False
        self._stuck_ticks = 0
        self._last_moved_win_pos = QPoint()

        # Dynamic Abdomen Glow state (active when windows are open or music is playing)
        self.abdomen_glow = 0.0
        self.is_active_session = False
        self.voice_state = 'IDLE'     # 'IDLE', 'LISTENING', 'THINKING', 'SPEAKING'
        self.heading_angle = -math.pi / 2 # Facing upwards initially
        self.target_angle = self.heading_angle
        
        self.cur_x = 0.0
        self.cur_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.crawl_speed = 2.0

        # Autonomous AI timers
        self.idle_ticks = 0
        self.target_idle_ticks = random.randint(50, 150) # 2.5 - 7.5s at 20Hz
        self.crawl_ticks = 0
        self.max_crawl_ticks = 0

        # Animation Phases
        self.walk_phase = 0.0
        self.breathe_phase = 0.0
        self.pedipalp_phase = 0.0
        self.head_tilt = 0.0
        self.drag_wiggle = 0.0

        # Dragging variables
        self._is_dragging = False
        self._drag_offset = QPoint()
        self._has_dragged = False
        self._mouse_hovering = False

        # Opacity & Ghost Mode (transparency for unobtrusive productivity)
        self.settings = QSettings("Okum", "Mascot")
        try:
            self.base_opacity = float(self.settings.value("spider_opacity", 0.50))
        except Exception:
            self.base_opacity = 0.50
        self.current_opacity = self.base_opacity
        self.target_opacity = self.base_opacity

        # Main Animation Timer (40 FPS = 25ms interval for silky smooth locomotion)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._game_loop)
        self.anim_timer.start(25)

        self.setToolTip("Okum Spider — Click to open Notes & AI | Drag to move | Right-click for options")

    def position_initial(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        init_x = screen.x() + screen.width() - 110
        init_y = screen.y() + screen.height() - 150
        self.move(init_x, init_y)
        self.cur_x = float(init_x)
        self.cur_y = float(init_y)
        self.target_x = self.cur_x
        self.target_y = self.cur_y
        self.state = 'IDLE'
        self.idle_ticks = 0
        self.is_look_around = False
        self._stuck_ticks = 0
        self._last_moved_win_pos = self.pos()

    def set_voice_state(self, state):
        """Updates voice interaction state ('IDLE', 'LISTENING', 'THINKING', 'SPEAKING')."""
        self.voice_state = state.upper()
        if self.voice_state == "LISTENING":
            self.setToolTip("Okum — Listening to you...")
        elif self.voice_state == "THINKING":
            self.setToolTip("Okum — Thinking...")
        elif self.voice_state == "SPEAKING":
            self.setToolTip("Okum — Speaking...")
        else:
            self.setToolTip("Okum Spider — Click to open Notes & AI | Drag to move | Right-click for options")
        self.update()

    def _game_loop(self):
        self.breathe_phase = (self.breathe_phase + 0.05) % (2 * math.pi)

        # Smooth ease in / ease out transition for mascot opacity
        diff_op = self.target_opacity - self.current_opacity
        if abs(diff_op) > 0.01:
            self.current_opacity += diff_op * 0.08
        else:
            self.current_opacity = self.target_opacity

        # Poll activity (window open or music playing) or voice interaction state
        is_active = False
        if self.voice_state != 'IDLE':
            is_active = True
        elif self.activity_callback:
            try:
                is_active = bool(self.activity_callback())
            except Exception:
                is_active = False
        elif getattr(self, 'manual_glow_override', None) is not None:
            is_active = bool(self.manual_glow_override)

        self.is_active_session = is_active
        target_glow = 1.0 if is_active else 0.0

        diff = target_glow - self.abdomen_glow
        if abs(diff) > 0.01:
            # Smooth ease in / ease out transition (~0.5s at 40 FPS)
            self.abdomen_glow += diff * 0.08
        else:
            self.abdomen_glow = target_glow

        if self._is_dragging:
            self.drag_wiggle = (self.drag_wiggle + 0.25) % (2 * math.pi)
            self.update()
            return

        # Autonomous state machine (only when free roam is active and user is not hovering)
        if self.free_roam_enabled and not self._mouse_hovering:
            if self.state == 'IDLE':
                self.idle_ticks += 1
                # Small realistic twitches while idle
                if random.random() < 0.03:
                    self.head_tilt = random.uniform(-0.15, 0.15)
                    self.pedipalp_phase = random.uniform(0, math.pi)

                if self.idle_ticks >= self.target_idle_ticks:
                    self._plan_next_action()

            elif self.state == 'TURNING':
                diff = (self.target_angle - self.heading_angle + math.pi) % (2 * math.pi) - math.pi
                if abs(diff) < 0.1:
                    self.heading_angle = self.target_angle
                    if self.is_look_around:
                        # Finished looking around; return peacefully to IDLE
                        self.state = 'IDLE'
                        self.is_look_around = False
                        self.idle_ticks = 0
                        self.target_idle_ticks = random.randint(60, 180)
                    else:
                        self.state = 'CRAWLING'
                        self._stuck_ticks = 0
                        self._last_moved_win_pos = self.pos()
                else:
                    turn_step = 0.12 if diff > 0 else -0.12
                    self.heading_angle += turn_step
                    self.walk_phase += 0.1

            elif self.state == 'CRAWLING':
                self.crawl_ticks += 1
                # Check distance to target
                dx = self.target_x - self.cur_x
                dy = self.target_y - self.cur_y
                dist = math.hypot(dx, dy)

                if dist < 5.0 or self.crawl_ticks >= self.max_crawl_ticks:
                    # Arrived at destination
                    self.state = 'IDLE'
                    self.idle_ticks = 0
                    self.target_idle_ticks = random.randint(60, 200) # Rest for 2.5 - 8 seconds
                    self._stuck_ticks = 0
                else:
                    # Next candidate position
                    step = min(self.crawl_speed, dist)
                    cand_x = self.cur_x + math.cos(self.heading_angle) * step
                    cand_y = self.cur_y + math.sin(self.heading_angle) * step

                    # Strict boundary checks against screen available workarea
                    screen = QGuiApplication.primaryScreen().availableGeometry()
                    margin = 40
                    min_x = screen.x() + margin
                    max_x = screen.x() + screen.width() - margin - self.width()
                    min_y = screen.y() + margin
                    max_y = screen.y() + screen.height() - margin - self.height()

                    # If candidate position would cross desktop edge, stop gracefully
                    if cand_x < min_x or cand_x > max_x or cand_y < min_y or cand_y > max_y:
                        self.cur_x = max(min_x, min(max_x, cand_x))
                        self.cur_y = max(min_y, min(max_y, cand_y))
                        nx, ny = int(self.cur_x), int(self.cur_y)
                        if nx != self.x() or ny != self.y():
                            self.move(nx, ny)
                        self.state = 'IDLE'
                        self.idle_ticks = 0
                        self.target_idle_ticks = random.randint(60, 180)
                        self._stuck_ticks = 0
                    else:
                        self.cur_x = cand_x
                        self.cur_y = cand_y
                        nx, ny = int(self.cur_x), int(self.cur_y)
                        if nx != self.x() or ny != self.y():
                            self.move(nx, ny)

                        # Physical movement / stuck verification
                        curr_win_pos = self.pos()
                        if curr_win_pos == self._last_moved_win_pos:
                            self._stuck_ticks += 1
                            if self._stuck_ticks >= 6: # Blocked by an obstacle or window manager constraint
                                self.state = 'IDLE'
                                self.idle_ticks = 0
                                self.target_idle_ticks = random.randint(60, 160)
                                self._stuck_ticks = 0
                        else:
                            self._last_moved_win_pos = curr_win_pos
                            self._stuck_ticks = 0

                        # Advance leg walking gait
                        gait_speed = 0.12 * (self.crawl_speed / 2.0)
                        self.walk_phase = (self.walk_phase + gait_speed) % (2 * math.pi)
                        self.pedipalp_phase = (self.pedipalp_phase + 0.18) % (2 * math.pi)

                        # Occasional sudden pause (unpredictable spider behavior)
                        if random.random() < 0.008 and self.crawl_ticks > 25:
                            self.state = 'IDLE'
                            self.idle_ticks = 0
                            self.target_idle_ticks = random.randint(20, 50) # Brief 1s pause

        self.update()

    def _plan_next_action(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        margin = 40
        min_x = screen.x() + margin
        max_x = max(min_x + 50, screen.x() + screen.width() - margin - self.width())
        min_y = screen.y() + margin
        max_y = max(min_y + 50, screen.y() + screen.height() - margin - self.height())

        # Ensure cur_x and cur_y are synchronized with current actual position
        self.cur_x = float(self.x())
        self.cur_y = float(self.y())

        # 25% chance to just turn in place and look around
        if random.random() < 0.25:
            self.target_angle = random.uniform(-math.pi, math.pi)
            self.is_look_around = True
            self.state = 'TURNING'
            return

        self.is_look_around = False

        # Pick random distance and direction
        dist = random.uniform(80, 360)
        angle = random.uniform(-math.pi, math.pi)

        new_x = self.cur_x + math.cos(angle) * dist
        new_y = self.cur_y + math.sin(angle) * dist

        # Clamp inside screen available boundaries
        new_x = max(min_x, min(max_x, new_x))
        new_y = max(min_y, min(max_y, new_y))

        # Real angle towards clamped target
        actual_dx = new_x - self.cur_x
        actual_dy = new_y - self.cur_y

        if math.hypot(actual_dx, actual_dy) < 30:
            self.idle_ticks = 0
            self.target_idle_ticks = random.randint(30, 80)
            return

        self.target_x = new_x
        self.target_y = new_y
        self.target_angle = math.atan2(actual_dy, actual_dx)

        # Random speed variations: stealth crawl, normal walk, or quick dash
        speed_dice = random.random()
        if speed_dice < 0.35:
            self.crawl_speed = random.uniform(1.4, 2.0) # Slow stealth crawl
        elif speed_dice < 0.80:
            self.crawl_speed = random.uniform(2.4, 3.8) # Normal natural speed
        else:
            self.crawl_speed = random.uniform(4.5, 6.0) # Quick spider dart

        self.crawl_ticks = 0
        dist_to_go = math.hypot(actual_dx, actual_dy)
        self.max_crawl_ticks = int(dist_to_go / max(0.5, self.crawl_speed)) + 40

        self.state = 'TURNING'

    def cleanup(self):
        """Cleanup handler on application shutdown."""
        try:
            self.anim_timer.stop()
            self.hide()
        except Exception:
            pass

    def set_mascot_opacity(self, val):
        """Sets base opacity, updates targets, and persists to QSettings."""
        self.base_opacity = float(val)
        self.target_opacity = min(1.0, max(0.85, self.base_opacity)) if self._mouse_hovering else self.base_opacity
        self.settings.setValue("spider_opacity", self.base_opacity)
        self.update()

    # Mouse Events
    def enterEvent(self, event):
        self._mouse_hovering = True
        self.target_opacity = min(1.0, max(0.85, self.base_opacity))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_hovering = False
        self.target_opacity = self.base_opacity
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._has_dragged = False
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self._has_dragged = True
            self.move(new_pos)
            self.cur_x = float(new_pos.x())
            self.cur_y = float(new_pos.y())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if not self._has_dragged:
                # Left click without dragging toggles Okum window
                self.toggle_callback()
            else:
                # Settled at new position
                self.cur_x = float(self.x())
                self.cur_y = float(self.y())
                self.target_x = self.cur_x
                self.target_y = self.cur_y
                self.is_look_around = False
                self._stuck_ticks = 0
                self._last_moved_win_pos = self.pos()
                self.state = 'IDLE'
                self.idle_ticks = 0
                self.target_idle_ticks = random.randint(80, 160)
            event.accept()

    def _show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(18, 22, 38, 250);
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 8px;
                padding: 4px;
                color: #f3f4f6;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(99, 102, 241, 0.35);
                color: #ffffff;
            }
        """)

        act_notes = QAction("📝 Quick Assistant & Notes", menu)
        act_notes.triggered.connect(self.toggle_callback)
        menu.addAction(act_notes)

        if self.open_music_callback:
            act_music = QAction("🎵 Music Player", menu)
            act_music.triggered.connect(self.open_music_callback)
            menu.addAction(act_music)

        if self.toggle_mini_music_callback:
            act_mini = QAction("🎧 Floating Mini Player", menu)
            act_mini.triggered.connect(self.toggle_mini_music_callback)
            menu.addAction(act_mini)

        if self.toggle_board_callback:
            act_board = QAction("🖌️ Okum Screen Board", menu)
            act_board.triggered.connect(self.toggle_board_callback)
            menu.addAction(act_board)

        menu.addSeparator()

        # Ghost Mode / Transparency Selector
        opacity_menu = menu.addMenu("👻 Ghost Mode & Opacity")
        opacities = [
            ("Ghost (30%)", 0.30),
            ("Translucent (50% - Gentle)", 0.50),
            ("Subtle (70%)", 0.70),
            ("Solid (100%)", 1.0),
        ]
        for label, val in opacities:
            act = QAction(label, opacity_menu)
            act.setCheckable(True)
            act.setChecked(abs(self.base_opacity - val) < 0.05)
            act.triggered.connect(lambda checked, v=val: self.set_mascot_opacity(v))
            opacity_menu.addAction(act)

        roam_label = "⏸️ Pause Crawling" if self.free_roam_enabled else "▶️ Resume Crawling"
        act_roam = QAction(roam_label, menu)
        act_roam.triggered.connect(self._toggle_free_roam)
        menu.addAction(act_roam)

        act_reset = QAction("📌 Reset to Corner", menu)
        act_reset.triggered.connect(self.position_initial)
        menu.addAction(act_reset)

        if self.exit_callback:
            menu.addSeparator()
            act_exit = QAction("❌ Exit Okum", menu)
            act_exit.triggered.connect(self.exit_callback)
            menu.addAction(act_exit)

        menu.exec(global_pos)

    def _toggle_free_roam(self):
        self.free_roam_enabled = not self.free_roam_enabled
        if not self.free_roam_enabled:
            self.state = 'IDLE'

    # Realistic Procedural Vector Painting
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.current_opacity)

        # Center and orientation
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        painter.save()
        painter.translate(cx, cy)
        # Orient facing towards heading (add 90 deg so 0 angle faces right)
        display_angle = math.degrees(self.heading_angle) + 90.0
        painter.rotate(display_angle)

        # (Ground shadow removed completely as requested by user)

        # Base resting leg coordinates relative to spider center (0,0)
        # Inspired directly by the user's anatomical blueprint and silhouette
        leg_templates = [
            # Pair 1: Front reaching high & inward (Leg 1)
            {
                'side': -1,
                'att': (-4.5, -7.0),
                'knee1': (-12.0, -18.0),
                'knee2': (-13.0, -29.0),
                'tip': (-6.5, -38.0),
                'gait_grp': 0
            },
            # Pair 2: Front-lateral reaching out & forward (Leg 2)
            {
                'side': -1,
                'att': (-6.5, -4.5),
                'knee1': (-18.0, -12.0),
                'knee2': (-26.0, -16.0),
                'tip': (-24.0, -3.0),
                'gait_grp': 1
            },
            # Pair 3: Lateral-rear reaching out & backward (Leg 3)
            {
                'side': -1,
                'att': (-6.8, -1.0),
                'knee1': (-19.0, 3.0),
                'knee2': (-27.0, 10.0),
                'tip': (-21.0, 24.0),
                'gait_grp': 0
            },
            # Pair 4: Rear reaching far back & curving inward (Leg 4)
            {
                'side': -1,
                'att': (-5.0, 2.5),
                'knee1': (-14.0, 13.0),
                'knee2': (-17.0, 27.0),
                'tip': (-7.5, 38.0),
                'gait_grp': 1
            },
        ]

        # Generate both sides symmetrically
        all_legs = []
        for l in leg_templates:
            all_legs.append(l) # Left
            r = {
                'side': 1,
                'att': (-l['att'][0], l['att'][1]),
                'knee1': (-l['knee1'][0], l['knee1'][1]),
                'knee2': (-l['knee2'][0], l['knee2'][1]),
                'tip': (-l['tip'][0], l['tip'][1]),
                'gait_grp': 1 - l['gait_grp']
            }
            all_legs.append(r)

        chitin_base = QColor(16, 18, 28)
        chitin_highlight = QColor(36, 42, 68)
        chitin_tip = QColor(50, 60, 95)

        # 1. DRAW 8 ARTICULATED LEGS
        for leg in all_legs:
            side = leg['side']
            att_x, att_y = leg['att']
            k1_x, k1_y = leg['knee1']
            k2_x, k2_y = leg['knee2']
            tip_x, tip_y = leg['tip']

            # Gait & interaction offsets
            if self._is_dragging:
                wiggle = math.sin(self.drag_wiggle + side * 1.5 + att_y) * 4.0
                k1_x += side * math.cos(self.drag_wiggle) * 1.5
                k2_x += side * math.sin(self.drag_wiggle) * 2.0
                tip_x += side * math.cos(self.drag_wiggle * 1.3) * 2.5
                tip_y += wiggle
            elif self.state == 'CRAWLING':
                phase_offset = 0.0 if leg['gait_grp'] == 0 else math.pi
                swing = math.sin(self.walk_phase + phase_offset)
                lift = max(0.0, math.sin(self.walk_phase + phase_offset))

                swing_dx = -side * swing * 3.5
                swing_dy = -swing * 4.0

                lift_dy = -lift * 4.0
                lift_dx = side * lift * 2.0

                k1_x += lift_dx * 0.5
                k1_y += lift_dy * 0.5
                k2_x += lift_dx + swing_dx * 0.5
                k2_y += lift_dy + swing_dy * 0.5
                tip_x += swing_dx
                tip_y += swing_dy
            else:
                idle_shift = math.sin(self.breathe_phase * 0.7 + att_y) * 0.8
                tip_x += side * idle_shift * 0.3
                tip_y += idle_shift * 0.5

            # Segment 1: Coxa -> Knee 1 (Femur)
            p1 = QPainterPath()
            p1.moveTo(att_x, att_y)
            p1.quadTo((att_x + k1_x) / 2.0 + side * 1.5, (att_y + k1_y) / 2.0, k1_x, k1_y)
            pen1 = QPen(chitin_base, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen1)
            painter.drawPath(p1)

            pen1_h = QPen(chitin_highlight, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen1_h)
            painter.drawPath(p1)

            # Segment 2: Knee 1 -> Knee 2 (Tibia)
            p2 = QPainterPath()
            p2.moveTo(k1_x, k1_y)
            p2.quadTo((k1_x + k2_x) / 2.0 + side * 1.0, (k1_y + k2_y) / 2.0, k2_x, k2_y)
            pen2 = QPen(chitin_base, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen2)
            painter.drawPath(p2)

            pen2_h = QPen(chitin_highlight, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen2_h)
            painter.drawPath(p2)

            # Segment 3: Knee 2 -> Claw Tip (Tarsus - tapering down to sharp claw)
            p3 = QPainterPath()
            p3.moveTo(k2_x, k2_y)
            p3.quadTo((k2_x + tip_x) / 2.0, (k2_y + tip_y) / 2.0, tip_x, tip_y)
            pen3 = QPen(chitin_base, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen3)
            painter.drawPath(p3)

            pen3_tip = QPen(chitin_tip, 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen3_tip)
            painter.drawPath(p3)

        # 2. DRAW ABDOMEN (Opisthosoma) - Behind cephalothorax
        ab_y = 12.0
        ab_rx = 11.5
        ab_ry = 14.5 + math.sin(self.breathe_phase * 0.6) * 0.4

        # Calculate dynamic bioluminescent glow (active when windows are open, music is playing, or voice active)
        eff_glow = 0.0
        if self.abdomen_glow > 0.005:
            glow_pulse = math.sin(self.breathe_phase * 1.4) * 0.12 + 0.88
            eff_glow = self.abdomen_glow * glow_pulse

            # Select aura & rim colors based on voice state
            if self.voice_state == "LISTENING":
                base_c = QColor(6, 182, 212)    # Electric Cyan
                high_c = QColor(103, 232, 249)
            elif self.voice_state == "THINKING":
                base_c = QColor(245, 158, 11)   # Warm Amber / Gold
                high_c = QColor(252, 211, 77)
            elif self.voice_state == "SPEAKING":
                base_c = QColor(217, 70, 239)   # Vibrant Fuchsia / Pink
                high_c = QColor(240, 171, 252)
            else:
                base_c = QColor(99, 102, 241)   # Deep Indigo
                high_c = QColor(129, 140, 248)

            # Soft diffuse ambient aura behind abdomen
            halo_path = QPainterPath()
            halo_path.addEllipse(QPointF(0, ab_y), ab_rx + 5.5 * eff_glow, ab_ry + 5.5 * eff_glow)
            halo_grad = QRadialGradient(0, ab_y, ab_ry + 5.5 * eff_glow)
            halo_grad.setColorAt(0.0, QColor(base_c.red(), base_c.green(), base_c.blue(), int(64 * eff_glow)))
            halo_grad.setColorAt(0.65, QColor(base_c.red(), base_c.green(), base_c.blue(), int(22 * eff_glow)))
            halo_grad.setColorAt(1.0, QColor(base_c.red(), base_c.green(), base_c.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo_grad)
            painter.drawPath(halo_path)
        else:
            base_c = QColor(99, 102, 241)
            high_c = QColor(129, 140, 248)

        ab_path = QPainterPath()
        ab_path.addEllipse(QPointF(0, ab_y), ab_rx, ab_ry)

        ab_grad = QRadialGradient(-2.5, ab_y - 4.0, 16.0)
        if eff_glow > 0.005:
            r0 = int(36 + (base_c.red() - 36) * 0.4 * eff_glow)
            g0 = int(42 + (base_c.green() - 42) * 0.4 * eff_glow)
            b0 = int(68 + (base_c.blue() - 68) * 0.4 * eff_glow)
            ab_grad.setColorAt(0.0, QColor(r0, g0, b0))
            ab_grad.setColorAt(0.55, QColor(18, 22, 36))
            ab_grad.setColorAt(1.0, QColor(9, 11, 18))

            rim_alpha = int(110 + 90 * eff_glow)
            painter.setPen(QPen(QColor(high_c.red(), high_c.green(), high_c.blue(), rim_alpha), 1.2 + 0.3 * eff_glow))
        else:
            ab_grad.setColorAt(0.0, QColor(36, 42, 68))     # Deep navy-indigo highlight
            ab_grad.setColorAt(0.55, QColor(18, 22, 36))    # Sleek dark chitin
            ab_grad.setColorAt(1.0, QColor(9, 11, 18))      # Near obsidian rim
            painter.setPen(QPen(QColor(99, 102, 241, 110), 1.2)) # Subtle sleek indigo rim

        painter.setBrush(ab_grad)
        painter.drawPath(ab_path)

        # Subtle dorsal specular gleam / bioluminescent core
        gleam_path = QPainterPath()
        gleam_path.addEllipse(QPointF(-2.0, ab_y - 5.0), 4.5, 6.0)
        gleam_grad = QRadialGradient(-2.0, ab_y - 5.0, 6.0)
        if eff_glow > 0.005:
            alpha_gleam = int(50 + 110 * eff_glow)
            gleam_grad.setColorAt(0.0, QColor(high_c.red(), high_c.green(), high_c.blue(), alpha_gleam))
            gleam_grad.setColorAt(0.65, QColor(base_c.red(), base_c.green(), base_c.blue(), int(32 * eff_glow)))
            gleam_grad.setColorAt(1.0, QColor(base_c.red(), base_c.green(), base_c.blue(), 0))
        else:
            gleam_grad.setColorAt(0.0, QColor(129, 140, 248, 50))
            gleam_grad.setColorAt(1.0, QColor(129, 140, 248, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gleam_grad)
        painter.drawPath(gleam_path)

        # 3. DRAW CEPHALOTHORAX (Prosoma / Head-Chest Hub)
        ceph_y = -3.0
        ceph_rx = 8.5
        ceph_ry = 8.0

        painter.save()
        painter.translate(0, ceph_y)
        painter.rotate(math.degrees(self.head_tilt))

        ceph_path = QPainterPath()
        ceph_path.addEllipse(QPointF(0, 0), ceph_rx, ceph_ry)

        ceph_grad = QRadialGradient(-1.5, -2.5, 11.0)
        ceph_grad.setColorAt(0.0, QColor(42, 50, 80))
        ceph_grad.setColorAt(0.65, QColor(20, 24, 38))
        ceph_grad.setColorAt(1.0, QColor(10, 12, 20))

        painter.setPen(QPen(QColor(99, 102, 241, 130), 1.2))
        painter.setBrush(ceph_grad)
        painter.drawPath(ceph_path)

        # Pedipalps (front feelers/arms reaching forward)
        pp_anim = math.sin(self.pedipalp_phase * 1.5) * 2.0 if self.state == 'CRAWLING' else math.sin(self.pedipalp_phase * 0.8) * 1.2
        painter.setPen(QPen(chitin_base, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(-2.5, -5.0), QPointF(-4.5, -10.0 + pp_anim))
        painter.drawLine(QPointF(-4.5, -10.0 + pp_anim), QPointF(-3.0, -13.0 + pp_anim))
        painter.drawLine(QPointF(2.5, -5.0), QPointF(4.5, -10.0 - pp_anim))
        painter.drawLine(QPointF(4.5, -10.0 - pp_anim), QPointF(3.0, -13.0 - pp_anim))

        # 4. CUTE JUMPING SPIDER EYES
        # Pair 1: Primary Large Center Eyes (Electric Blue/Cyan with shiny reflection)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(56, 189, 248)) # Vivid Cyan
        painter.drawEllipse(QPointF(-2.5, -3.8), 2.2, 2.2)
        painter.drawEllipse(QPointF(2.5, -3.8), 2.2, 2.2)

        # Large eye shiny specular catchlight (makes them look adorable & alive)
        painter.setBrush(QColor(255, 255, 255, 240))
        painter.drawEllipse(QPointF(-1.8, -4.4), 0.8, 0.8)
        painter.drawEllipse(QPointF(3.2, -4.4), 0.8, 0.8)

        # Pair 2: Lateral Secondary Eyes (Small soft glowing dots)
        painter.setBrush(QColor(165, 180, 252, 200)) # Lavender
        painter.drawEllipse(QPointF(-5.5, -2.5), 1.2, 1.2)
        painter.drawEllipse(QPointF(5.5, -2.5), 1.2, 1.2)

        painter.restore() # Cephalothorax
        painter.restore() # Global translated & rotated
