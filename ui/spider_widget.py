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

        # Mascot dimensions (88x88 provides ample room for articulated legs while remaining neat)
        self.setFixedSize(88, 88)

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

        # Draw subtle soft ground shadow
        shadow_path = QPainterPath()
        shadow_path.addEllipse(QPointF(0, 4), 26, 30)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 75))

        # 8 Articulated Legs Definitions (Anatomy from concept sketch)
        # 4 on Left (x < 0), 4 on Right (x > 0)
        # Legs: 0:L1, 1:L2, 2:L3, 3:L4, 4:R1, 5:R2, 6:R3, 7:R4
        # Base attach angles, segment lengths, joint resting bends
        leg_configs = [
            # side, attach_y, base_angle, len1, len2, len3, gait_group
            (-1, -6, -65, 12, 14, 16, 0), # L1 front-reaching
            (-1, -2, -25, 13, 14, 15, 1), # L2 mid-front
            (-1,  3,  25, 13, 13, 14, 0), # L3 mid-rear
            (-1,  8,  65, 14, 16, 18, 1), # L4 rear-reaching
            ( 1, -6, -65, 12, 14, 16, 1), # R1 front-reaching
            ( 1, -2, -25, 13, 14, 15, 0), # R2 mid-front
            ( 1,  3,  25, 13, 13, 14, 1), # R3 mid-rear
            ( 1,  8,  65, 14, 16, 18, 0), # R4 rear-reaching
        ]

        # Draw 8 Articulated Legs
        for side, att_y, base_deg, l1, l2, l3, gait_grp in leg_configs:
            # Calculate gait cycle swing
            if self._is_dragging:
                # Dangle/wiggle when picked up
                wiggle = math.sin(self.drag_wiggle + side * 1.5 + att_y) * 12.0
                swing_deg = wiggle
                knee_lift = -2.0 + math.cos(self.drag_wiggle * 1.5) * 3.0
            elif self.state == 'CRAWLING':
                # Alternating tetrapod gait
                phase_offset = 0.0 if gait_grp == 0 else math.pi
                swing_deg = math.sin(self.walk_phase + phase_offset) * 14.0
                knee_lift = max(0.0, math.sin(self.walk_phase + phase_offset)) * 4.0
            else:
                # Idle subtle micro-settle
                swing_deg = math.sin(self.breathe_phase * 0.5 + att_y) * 1.5
                knee_lift = 0.0

            # Attach point on cephalothorax edge
            root_x = side * 8.0
            root_y = att_y

            eff_deg = base_deg + swing_deg
            rad = math.radians(eff_deg)

            # Segment 1 (Coxa / Femur)
            j1_x = root_x + side * (math.cos(rad) * l1)
            j1_y = root_y + math.sin(rad) * l1 - knee_lift

            # Segment 2 (Tibia - bends outwards and down)
            knee_angle = rad + math.radians(25 if side < 0 else -25)
            j2_x = j1_x + side * (math.cos(knee_angle) * l2)
            j2_y = j1_y + math.sin(knee_angle) * l2 + (2.0 if att_y > 0 else -1.0)

            # Segment 3 (Metatarsus / Tarsus tip - claw reaching ground)
            claw_angle = knee_angle + math.radians(35 if side < 0 else -35)
            tip_x = j2_x + side * (math.cos(claw_angle) * l3)
            tip_y = j2_y + math.sin(claw_angle) * l3 + (6.0 if att_y > 0 else 2.0)

            # Draw leg segments with chitin shading & joints
            leg_pen = QPen(QColor(18, 22, 38), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(leg_pen)
            painter.drawLine(QPointF(root_x, root_y), QPointF(j1_x, j1_y))

            leg_pen2 = QPen(QColor(30, 36, 60), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(leg_pen2)
            painter.drawLine(QPointF(j1_x, j1_y), QPointF(j2_x, j2_y))

            leg_pen3 = QPen(QColor(55, 65, 95), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(leg_pen3)
            painter.drawLine(QPointF(j2_x, j2_y), QPointF(tip_x, tip_y))

            # Joint highlight knurl
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(99, 102, 241, 160)) # subtle indigo joint dot
            painter.drawEllipse(QPointF(j1_x, j1_y), 1.6, 1.6)
            painter.drawEllipse(QPointF(j2_x, j2_y), 1.3, 1.3)

        # Abdomen (Opisthosoma) - Posterior plump body
        ab_y = 13.0
        ab_w = 21.0
        ab_h = 27.0 + math.sin(self.breathe_phase) * 0.8 # subtle breathing pulse

        ab_grad = QRadialGradient(-2.0, ab_y - 4.0, ab_h)
        ab_grad.setColorAt(0.0, QColor(40, 48, 76))
        ab_grad.setColorAt(0.5, QColor(22, 26, 44))
        ab_grad.setColorAt(1.0, QColor(10, 12, 20))

        painter.setPen(QPen(QColor(99, 102, 241, 90), 1.2)) # Sleek indigo rim
        painter.setBrush(ab_grad)
        painter.drawEllipse(QPointF(0, ab_y), ab_w / 2.0, ab_h / 2.0)

        # Abdomen decorative dorsal markings (Okum bio-luminescent chevron)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(99, 102, 241, 80))
        painter.drawEllipse(QPointF(0, ab_y - 2), 3.0, 5.0)
        painter.setBrush(QColor(56, 189, 248, 120)) # Small cyan core
        painter.drawEllipse(QPointF(0, ab_y + 4), 2.0, 3.0)

        # Cephalothorax (Prosoma) - Head & chest
        ceph_y = -3.0
        ceph_w = 17.0
        ceph_h = 16.0

        # Head tilt angle
        painter.save()
        painter.translate(0, ceph_y)
        painter.rotate(math.degrees(self.head_tilt))

        ceph_grad = QRadialGradient(-1.0, -3.0, 12.0)
        ceph_grad.setColorAt(0.0, QColor(48, 56, 88))
        ceph_grad.setColorAt(0.6, QColor(24, 28, 48))
        ceph_grad.setColorAt(1.0, QColor(12, 14, 24))

        painter.setPen(QPen(QColor(99, 102, 241, 120), 1.2))
        painter.setBrush(ceph_grad)
        painter.drawEllipse(QPointF(0, 0), ceph_w / 2.0, ceph_h / 2.0)

        # Pedipalps (front feelers)
        pp_swing = math.sin(self.pedipalp_phase) * 3.0
        painter.setPen(QPen(QColor(30, 36, 60), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(-3.0, -7.0), QPointF(-5.0, -13.0 + pp_swing))
        painter.drawLine(QPointF(-5.0, -13.0 + pp_swing), QPointF(-3.5, -16.0 + pp_swing))
        painter.drawLine(QPointF(3.0, -7.0), QPointF(5.0, -13.0 - pp_swing))
        painter.drawLine(QPointF(5.0, -13.0 - pp_swing), QPointF(3.5, -16.0 - pp_swing))

        # Cute Spider Eyes (Cluster: 2 large cute glowing eyes + 4 small perimeter eyes)
        # 1. Main Large Eyes (Glowing Cyan / Electric Blue with white catchlight reflection)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(56, 189, 248)) # Vivid Cyan
        painter.drawEllipse(QPointF(-2.8, -5.0), 2.0, 2.0)
        painter.drawEllipse(QPointF(2.8, -5.0), 2.0, 2.0)

        # White glint reflection (makes them look cute and alive!)
        painter.setBrush(QColor(255, 255, 255, 230))
        painter.drawEllipse(QPointF(-2.2, -5.6), 0.7, 0.7)
        painter.drawEllipse(QPointF(3.4, -5.6), 0.7, 0.7)

        # 2. Secondary Lateral Eyes (Small glowing dots)
        painter.setBrush(QColor(165, 180, 252, 190)) # Soft Lavender
        painter.drawEllipse(QPointF(-5.2, -4.0), 1.1, 1.1)
        painter.drawEllipse(QPointF(5.2, -4.0), 1.1, 1.1)
        painter.drawEllipse(QPointF(-4.5, -6.5), 0.9, 0.9)
        painter.drawEllipse(QPointF(4.5, -6.5), 0.9, 0.9)

        painter.restore() # Cephalothorax
        painter.restore() # Global translated & rotated
