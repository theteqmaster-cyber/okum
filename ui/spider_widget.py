import math
import random
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QPen,
    QBrush, QCursor, QPainterPath, QAction, QGuiApplication
)
from PyQt6.QtWidgets import QWidget, QMenu

class FloatingSpider(QWidget):
    """
    Okum Desktop Spider Mascot:
    A cute, small articulated spider that crawls unpredictably across the desktop
    with realistic leg gait, idle twitching, and interactive drag/click response.
    """
    def __init__(self, toggle_callback, open_music_callback=None, toggle_board_callback=None):
        super().__init__()
        self.toggle_callback = toggle_callback
        self.open_music_callback = open_music_callback
        self.toggle_board_callback = toggle_board_callback

        # Frameless, translucent desktop tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Mascot dimensions (96x96 provides ample room for articulated legs while remaining neat)
        self.setFixedSize(96, 96)

        # Crawling & Behavior State
        self.state = 'IDLE'           # 'IDLE', 'TURNING', 'CRAWLING', 'DRAGGING'
        self.free_roam_enabled = True # Can be toggled via right-click
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

        # Main Animation Timer (40 FPS = 25ms interval for silky smooth locomotion)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._game_loop)
        self.anim_timer.start(25)

        self.setToolTip("Okum Spider — Click to open Notes & AI | Drag to move | Right-click for options")

    def position_initial(self):
        screen = QGuiApplication.primaryScreen().geometry()
        init_x = screen.width() - 110
        init_y = screen.height() - 150
        self.move(init_x, init_y)
        self.cur_x = float(init_x)
        self.cur_y = float(init_y)

    def _game_loop(self):
        self.breathe_phase = (self.breathe_phase + 0.05) % (2 * math.pi)

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
                    self.state = 'CRAWLING'
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
                else:
                    # Smoothly advance position
                    step = min(self.crawl_speed, dist)
                    self.cur_x += math.cos(self.heading_angle) * step
                    self.cur_y += math.sin(self.heading_angle) * step
                    self.move(int(self.cur_x), int(self.cur_y))

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
        screen = QGuiApplication.primaryScreen().geometry()
        margin = 60
        max_x = max(margin, screen.width() - 120)
        max_y = max(margin, screen.height() - 140)

        # 25% chance to just turn in place and look around
        if random.random() < 0.25:
            self.target_angle = random.uniform(-math.pi, math.pi)
            self.state = 'TURNING'
            return

        # Pick random distance and direction
        dist = random.uniform(80, 380)
        angle = random.uniform(-math.pi, math.pi)

        new_x = self.cur_x + math.cos(angle) * dist
        new_y = self.cur_y + math.sin(angle) * dist

        # Clamp inside screen boundaries
        new_x = max(margin, min(max_x, new_x))
        new_y = max(margin, min(max_y, new_y))

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
            self.crawl_speed = random.uniform(1.2, 1.8) # Slow stealth crawl
        elif speed_dice < 0.80:
            self.crawl_speed = random.uniform(2.4, 3.8) # Normal natural speed
        else:
            self.crawl_speed = random.uniform(4.5, 6.5) # Quick spider dart

        self.crawl_ticks = 0
        dist_to_go = math.hypot(actual_dx, actual_dy)
        self.max_crawl_ticks = int(dist_to_go / max(0.5, self.crawl_speed)) + 40

        self.state = 'TURNING'

    # Mouse Events
    def enterEvent(self, event):
        self._mouse_hovering = True
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_hovering = False
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

        if self.toggle_board_callback:
            act_board = QAction("🖌️ Okum Screen Board", menu)
            act_board.triggered.connect(self.toggle_board_callback)
            menu.addAction(act_board)

        menu.addSeparator()

        roam_label = "⏸️ Pause Crawling" if self.free_roam_enabled else "▶️ Resume Crawling"
        act_roam = QAction(roam_label, menu)
        act_roam.triggered.connect(self._toggle_free_roam)
        menu.addAction(act_roam)

        act_reset = QAction("📌 Reset to Corner", menu)
        act_reset.triggered.connect(self.position_initial)
        menu.addAction(act_reset)

        menu.exec(global_pos)

    def _toggle_free_roam(self):
        self.free_roam_enabled = not self.free_roam_enabled
        if not self.free_roam_enabled:
            self.state = 'IDLE'

    # Realistic Procedural Vector Painting
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

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

        ab_path = QPainterPath()
        ab_path.addEllipse(QPointF(0, ab_y), ab_rx, ab_ry)

        ab_grad = QRadialGradient(-2.5, ab_y - 4.0, 16.0)
        ab_grad.setColorAt(0.0, QColor(36, 42, 68))     # Deep navy-indigo highlight
        ab_grad.setColorAt(0.55, QColor(18, 22, 36))    # Sleek dark chitin
        ab_grad.setColorAt(1.0, QColor(9, 11, 18))      # Near obsidian rim

        painter.setPen(QPen(QColor(99, 102, 241, 110), 1.2)) # Subtle sleek indigo rim
        painter.setBrush(ab_grad)
        painter.drawPath(ab_path)

        # Subtle dorsal specular gleam on abdomen (gives 3D curvature)
        gleam_path = QPainterPath()
        gleam_path.addEllipse(QPointF(-2.0, ab_y - 5.0), 4.5, 6.0)
        gleam_grad = QRadialGradient(-2.0, ab_y - 5.0, 6.0)
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
