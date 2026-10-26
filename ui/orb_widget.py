import math
import random
import time
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, QSettings
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QPen,
    QBrush, QCursor, QPainterPath, QAction, QGuiApplication, QFont, QPolygonF
)
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtMultimedia import QMediaPlayer

def lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linearly interpolates between two QColor instances."""
    t = max(0.0, min(1.0, t))
    r = int(c1.red() + (c2.red() - c1.red()) * t)
    g = int(c1.green() + (c2.green() - c1.green()) * t)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
    a = int(c1.alpha() + (c2.alpha() - c1.alpha()) * t)
    return QColor(r, g, b, a)

class FloatingOrb(QWidget):
    """
    Okum Living Floating Orb Mascot:
    - Roams unpredictably for the first 10 seconds of application startup.
    - Gracefully curves and docks into the bottom-left corner of the screen.
    - Fully draggable: hold and drag anywhere across any screen; anchors at dropped position.
    - Translucent organic aesthetic: feathered soft edges with NO hard solid circle outlines.
    - No floating stars/particles cluttering the view.
    - Music Mode: Smoothly transitions from Solar Ember (Gold) to a calm, focused Indigo.
      No dramatic throbbing/pulsing, so you stay completely focused on your work.
    - Hover music satellites arc (Shuffle, Prev, Play/Pause, Next) when music is playing.
    - Voice Assistant state reactions (Listening, Thinking, Speaking).
    - Calming low-energy ember sleep state during user inactivity.
    """
    def __init__(self, toggle_callback=None, open_music_callback=None,
                 toggle_board_callback=None, activity_callback=None,
                 toggle_mini_music_callback=None, exit_callback=None):
        super().__init__()
        self.toggle_callback = toggle_callback or (lambda: None)
        self.open_music_callback = open_music_callback
        self.toggle_board_callback = toggle_board_callback
        self.activity_callback = activity_callback
        self.toggle_mini_music_callback = toggle_mini_music_callback
        self.exit_callback = exit_callback

        # Frameless, translucent desktop tool window that stays on top
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

        # 140x140 allows space for the 48px orb + fanning satellite controls
        self.widget_size = 140
        self.setFixedSize(self.widget_size, self.widget_size)

        # Base relative center of orb inside widget
        self.orb_rel_x = 44.0
        self.orb_rel_y = 96.0
        self.orb_radius = 24.0

        # Locomotion & State Machine
        # States: 'ROAMING' (0-10s), 'DOCKING' (curving to corner), 'DOCKED' (anchored)
        self.state = 'ROAMING'
        self.ticks = 0
        self.roam_target_ticks = 400  # 10 seconds at 40 FPS (25ms per tick)

        # Free roaming dynamics
        self.cur_x = 0.0
        self.cur_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.roam_speed = 3.2
        self.next_waypoint_ticks = 0

        # Anchor dock coordinates
        self.dock_x = 24.0
        self.dock_y = 600.0

        # Dragging support
        self._is_dragging = False
        self._has_dragged = False
        self._drag_offset = QPoint()

        # Animation Phases
        self.breathe_phase = 0.0
        self.plasma_rot = 0.0
        self.hover_progress = 0.0
        self.satellites_visible = False
        self.hovered_satellite = None

        # Voice Assistant & Music States
        self.voice_state = 'IDLE'  # 'IDLE', 'LISTENING', 'THINKING', 'SPEAKING'
        self.is_music_playing = False
        self.music_gold_progress = 0.0  # 0.0 = Base Indigo, 1.0 = Music Gold

        # Inactivity & Sleep
        self.is_sleeping = False
        self.inactivity_ticks = 0
        self.sleep_threshold = 40 * 120  # 2 minutes of inactivity

        # Translucency (Option A: ~0.58 base opacity)
        self.settings = QSettings("Okum", "Mascot")
        try:
            self.base_opacity = float(self.settings.value("orb_opacity", 0.58))
        except Exception:
            self.base_opacity = 0.58
        self.current_opacity = self.base_opacity
        self._mouse_hovering = False

        # Main animation timer at 40 FPS (25ms interval)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._game_loop)
        self.anim_timer.start(25)

        self.setToolTip("Okum Living Orb — Click to open Notes & AI | Drag to move | Right-click for options")

    def position_initial(self):
        """Initializes startup roaming and calculates bottom-left dock position."""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.dock_x = float(screen.x() + 24)
        self.dock_y = float(screen.y() + screen.height() - self.height() - 20)

        # Start from a pleasant position on screen
        init_x = float(screen.x() + screen.width() // 2 + random.randint(-160, 160))
        init_y = float(screen.y() + screen.height() // 2 + random.randint(-120, 120))
        self.move(int(init_x), int(init_y))
        self.cur_x = init_x
        self.cur_y = init_y
        self.state = 'ROAMING'
        self.ticks = 0
        self.is_sleeping = False
        self.inactivity_ticks = 0
        self._pick_new_roam_target()

    def _pick_new_roam_target(self):
        """Picks unpredictable roaming destinations during the initial 10 seconds."""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        margin = 48
        min_x = screen.x() + margin
        max_x = screen.x() + screen.width() - margin - self.width()
        min_y = screen.y() + margin
        max_y = screen.y() + screen.height() - margin - self.height()

        self.target_x = random.uniform(min_x, max_x)
        self.target_y = random.uniform(min_y, max_y)
        self.roam_speed = random.uniform(2.6, 4.6)
        self.next_waypoint_ticks = random.randint(45, 95)

    def set_voice_state(self, state):
        """Updates voice assistant interaction state ('IDLE', 'LISTENING', 'THINKING', 'SPEAKING')."""
        self.voice_state = state.upper()
        self.inactivity_ticks = 0
        if self.is_sleeping:
            self.is_sleeping = False
        if self.voice_state == "LISTENING":
            self.setToolTip("Okum — Listening to you...")
        elif self.voice_state == "THINKING":
            self.setToolTip("Okum — Thinking...")
        elif self.voice_state == "SPEAKING":
            self.setToolTip("Okum — Speaking...")
        else:
            self.setToolTip("Okum Living Orb — Click to open Notes & AI | Drag to move | Right-click for options")
        self.update()

    def set_music_playing(self, is_playing):
        """Syncs music playback state for smooth indigo transition and satellite reveal."""
        self.is_music_playing = bool(is_playing)
        if self.is_music_playing and self.is_sleeping:
            self.is_sleeping = False
            self.inactivity_ticks = 0
        self.update()

    def cleanup(self):
        """Clean shutdown handler."""
        try:
            self.anim_timer.stop()
            self.hide()
        except Exception:
            pass

    def _game_loop(self):
        self.ticks += 1
        self.inactivity_ticks += 1
        self.breathe_phase = (self.breathe_phase + 0.05) % (2 * math.pi)
        self.plasma_rot = (self.plasma_rot + 0.025) % (2 * math.pi)

        # Smooth, elegant color transition to Warm Gold when music is playing (Default is calm Indigo)
        target_gold = 1.0 if self.is_music_playing else 0.0
        diff_gold = target_gold - self.music_gold_progress
        if abs(diff_gold) > 0.01:
            self.music_gold_progress += diff_gold * 0.06
        else:
            self.music_gold_progress = target_gold

        # Check sleep timeout (only if idle, no music, not dragging)
        if (not self.is_sleeping and not self._is_dragging and 
            self.inactivity_ticks > self.sleep_threshold and 
            self.voice_state == 'IDLE' and not self.is_music_playing):
            self.is_sleeping = True

        # Locomotion State Machine (only when user is not manually dragging)
        if not self._is_dragging:
            if self.state == 'ROAMING':
                # Phase 1: Free unpredictable roam for first 10 seconds
                self.next_waypoint_ticks -= 1
                dx = self.target_x - self.cur_x
                dy = self.target_y - self.cur_y
                dist = math.hypot(dx, dy)

                if dist < 12.0 or self.next_waypoint_ticks <= 0:
                    self._pick_new_roam_target()
                else:
                    angle = math.atan2(dy, dx)
                    step = min(self.roam_speed, dist)
                    self.cur_x += math.cos(angle) * step
                    self.cur_y += math.sin(angle) * step
                    self.move(int(self.cur_x), int(self.cur_y))

                # 10s completed -> transition to docking
                if self.ticks >= self.roam_target_ticks:
                    self.state = 'DOCKING'

            elif self.state == 'DOCKING':
                # Phase 2: Natural curved glide into bottom-left corner
                dx = self.dock_x - self.cur_x
                dy = self.dock_y - self.cur_y
                dist = math.hypot(dx, dy)

                if dist < 4.0:
                    self.cur_x = self.dock_x
                    self.cur_y = self.dock_y
                    self.move(int(self.cur_x), int(self.cur_y))
                    self.state = 'DOCKED'
                else:
                    swoop_offset = math.sin(dist * 0.015) * 3.5
                    angle = math.atan2(dy, dx)
                    dock_speed = max(2.2, min(6.5, dist * 0.045))
                    self.cur_x += math.cos(angle) * dock_speed - math.sin(angle) * swoop_offset
                    self.cur_y += math.sin(angle) * dock_speed + math.cos(angle) * swoop_offset
                    self.move(int(self.cur_x), int(self.cur_y))

            elif self.state == 'DOCKED':
                # Phase 3: Anchored firmly at user's dock position
                # Harmonic levitation happens inside paintEvent
                if int(self.x()) != int(self.dock_x) or int(self.y()) != int(self.dock_y):
                    self.move(int(self.dock_x), int(self.dock_y))

        # Satellite arc smooth expansion / contraction
        target_sat = 1.0 if (self._mouse_hovering and self.is_music_playing and not self._is_dragging) else 0.0
        diff_sat = target_sat - self.hover_progress
        if abs(diff_sat) > 0.01:
            self.hover_progress += diff_sat * 0.16
        else:
            self.hover_progress = target_sat
        self.satellites_visible = (self.hover_progress > 0.04)

        # Smooth opacity transition
        target_op = min(0.92, self.base_opacity + 0.30) if self._mouse_hovering else self.base_opacity
        if self.is_sleeping:
            target_op = max(0.28, self.base_opacity - 0.28)
        diff_op = target_op - self.current_opacity
        if abs(diff_op) > 0.01:
            self.current_opacity += diff_op * 0.1
        else:
            self.current_opacity = target_op

        self.update()

    def _get_satellite_configs(self):
        """
        Returns list of (key, QRectF, tooltip) for the 4 satellite buttons.
        Dynamically adapts quadrant based on position relative to screen edges.
        """
        if self.hover_progress <= 0.01:
            return []

        cx = self.orb_rel_x
        cy = self.orb_rel_y
        if self.state == 'DOCKED' and not self._is_dragging:
            cy += math.sin(self.breathe_phase) * 3.2
            cx += math.cos(self.breathe_phase * 0.7) * 1.5

        # Arc radius & button dimensions
        arc_radius = 58.0 * self.hover_progress
        btn_r = 12.5  # 25px diameter

        # Detect position relative to screen edges to orient arc smoothly
        screen = QGuiApplication.primaryScreen().availableGeometry()
        near_right = (self.x() > screen.x() + screen.width() - 200)
        near_top = (self.y() < screen.y() + 180)

        # Default: Bottom-Left (fan up and to the right)
        base_angles = [
            ('shuffle', -math.radians(82), "Shuffle: Toggle"),
            ('prev', -math.radians(52), "Previous Track"),
            ('play', -math.radians(22), "Play / Pause"),
            ('next', math.radians(8), "Next Track"),
        ]

        if near_right and not near_top:
            # Near right edge: fan up and to the left
            base_angles = [
                ('shuffle', -math.radians(98), "Shuffle: Toggle"),
                ('prev', -math.radians(128), "Previous Track"),
                ('play', -math.radians(158), "Play / Pause"),
                ('next', -math.radians(188), "Next Track"),
            ]
        elif near_top and not near_right:
            # Near top edge: fan down and to the right
            base_angles = [
                ('shuffle', math.radians(8), "Shuffle: Toggle"),
                ('prev', math.radians(38), "Previous Track"),
                ('play', math.radians(68), "Play / Pause"),
                ('next', math.radians(98), "Next Track"),
            ]
        elif near_top and near_right:
            # Top-right corner: fan down and to the left
            base_angles = [
                ('shuffle', math.radians(172), "Shuffle: Toggle"),
                ('prev', math.radians(142), "Previous Track"),
                ('play', math.radians(112), "Play / Pause"),
                ('next', math.radians(82), "Next Track"),
            ]

        res = []
        for key, angle, tip in base_angles:
            bx = cx + math.cos(angle) * arc_radius
            by = cy + math.sin(angle) * arc_radius
            rect = QRectF(bx - btn_r, by - btn_r, btn_r * 2, btn_r * 2)
            res.append((key, rect, tip))
        return res

    # Mouse & Dragging Events
    def enterEvent(self, event):
        self._mouse_hovering = True
        self.inactivity_ticks = 0
        if self.is_sleeping:
            self.is_sleeping = False
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_hovering = False
        self.hovered_satellite = None
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()

            # 1. Check if clicked a satellite button
            if self.satellites_visible:
                for key, rect, _ in self._get_satellite_configs():
                    if rect.contains(pos):
                        self._on_satellite_click(key)
                        event.accept()
                        return

            # 2. Check if clicked inside the orb -> start drag
            cx = self.orb_rel_x
            cy = self.orb_rel_y
            if math.hypot(pos.x() - cx, pos.y() - cy) <= self.orb_radius + 14:
                self._is_dragging = True
                self._has_dragged = False
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
                event.accept()
                return

        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position()

        # Handle dragging
        if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            if not self._has_dragged and (new_pos - self.pos()).manhattanLength() > 3:
                self._has_dragged = True

            self.move(new_pos)
            self.cur_x = float(new_pos.x())
            self.cur_y = float(new_pos.y())
            self.dock_x = float(new_pos.x())
            self.dock_y = float(new_pos.y())
            self.state = 'DOCKED'
            event.accept()
            return

        # Handle satellite hovering
        old_hov = self.hovered_satellite
        self.hovered_satellite = None

        if self.satellites_visible:
            for key, rect, tip in self._get_satellite_configs():
                if rect.contains(pos):
                    self.hovered_satellite = key
                    self.setToolTip(tip)
                    break

        if not self.hovered_satellite:
            self.setToolTip("Okum Living Orb — Click to open Notes & AI | Drag to move | Right-click for options")

        if self.hovered_satellite != old_hov:
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if self._is_dragging:
                self._is_dragging = False
                if not self._has_dragged:
                    # Normal click without dragging -> toggle quick window
                    self.toggle_callback()
                else:
                    # Dropped at user's desired position
                    self.cur_x = float(self.x())
                    self.cur_y = float(self.y())
                    self.dock_x = self.cur_x
                    self.dock_y = self.cur_y
                    self.state = 'DOCKED'
                    self.settings.setValue("dock_x", self.dock_x)
                    self.settings.setValue("dock_y", self.dock_y)
                event.accept()
                return

    def _on_satellite_click(self, key):
        """Executes music action directly without shifting the orb."""
        from services.music_service import MusicService
        ms = MusicService.get_instance()
        if not ms:
            return

        if key == 'play':
            ms.toggle_play_pause()
        elif key == 'next':
            ms.next_track()
        elif key == 'prev':
            ms.previous_track()
        elif key == 'shuffle':
            ms.toggle_shuffle()

        self.update()

    def _show_context_menu(self, global_pos):
        """Preserves all critical right-click functions in a sleek menu."""
        menu = QMenu(self)
        is_gold = (self.music_gold_progress > 0.5)

        border_col = "rgba(245, 158, 11, 0.5)" if is_gold else "rgba(99, 102, 241, 0.45)"
        sel_col = "rgba(245, 158, 11, 0.35)" if is_gold else "rgba(99, 102, 241, 0.35)"

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: rgba(18, 14, 26, 245);
                border: 1px solid {border_col};
                border-radius: 8px;
                padding: 4px;
                color: #f3f4f6;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {sel_col};
                color: #ffffff;
            }}
        """)

        act_notes = QAction("📝 Quick Assistant & Notes", menu)
        act_notes.triggered.connect(self.toggle_callback)
        menu.addAction(act_notes)

        if self.open_music_callback:
            act_music = QAction("🎵 Music Library", menu)
            act_music.triggered.connect(self.open_music_callback)
            menu.addAction(act_music)

        if self.toggle_mini_music_callback:
            act_mini = QAction("🎛️ Floating Mini Player", menu)
            act_mini.triggered.connect(self.toggle_mini_music_callback)
            menu.addAction(act_mini)

        if self.toggle_board_callback:
            act_board = QAction("🎨 Canvas Whiteboard", menu)
            act_board.triggered.connect(self.toggle_board_callback)
            menu.addAction(act_board)

        menu.addSeparator()

        act_roam = QAction("🔄 Re-run Roam & Dock", menu)
        act_roam.triggered.connect(self.position_initial)
        menu.addAction(act_roam)

        act_sleep = QAction("🌙 Wake / Sleep Toggle", menu)
        act_sleep.triggered.connect(self._toggle_sleep)
        menu.addAction(act_sleep)

        menu.addSeparator()

        if self.exit_callback:
            act_exit = QAction("❌ Exit Okum", menu)
            act_exit.triggered.connect(self.exit_callback)
            menu.addAction(act_exit)

        menu.exec(global_pos)

    def _toggle_sleep(self):
        self.is_sleeping = not self.is_sleeping
        self.inactivity_ticks = 0 if not self.is_sleeping else self.sleep_threshold + 10
        self.update()

    def set_orb_opacity(self, val):
        self.base_opacity = float(val)
        self.settings.setValue("orb_opacity", self.base_opacity)
        self.update()

    def set_mascot_opacity(self, val):
        self.set_orb_opacity(val)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        alpha_mult = self.current_opacity

        # Orb center with harmonic floating levitation
        cx = self.orb_rel_x
        cy = self.orb_rel_y
        if self.state == 'DOCKED' and not self._is_dragging:
            cy += math.sin(self.breathe_phase) * 3.2
            cx += math.cos(self.breathe_phase * 0.7) * 1.5

        # CALM RADIUS: No dramatic beat expansion or throbbing when music plays
        # Only speech ripples on active TTS voice speaking
        r = self.orb_radius
        if self.is_sleeping:
            r = self.orb_radius * 0.88

        # --- Color Palettes ---
        # 1. Base Indigo / Deep Violet (Default resting theme)
        indigo_aura = QColor(99, 102, 241, int(105 * alpha_mult))    # Indigo-500
        indigo_core = QColor(199, 210, 254, int(230 * alpha_mult))   # Indigo-200
        indigo_mid  = QColor(99, 102, 241, int(185 * alpha_mult))
        indigo_dark = QColor(67, 56, 202, int(115 * alpha_mult))     # Indigo-700

        # 2. Warm Gold / Solar Amber (Active during music playback)
        gold_aura = QColor(245, 158, 11, int(105 * alpha_mult))
        gold_core = QColor(254, 240, 138, int(230 * alpha_mult))
        gold_mid  = QColor(245, 158, 11, int(190 * alpha_mult))
        gold_dark = QColor(217, 119, 6, int(115 * alpha_mult))

        # Interpolate based on music state (0.0 = Indigo, 1.0 = Gold)
        m_t = self.music_gold_progress
        idle_aura = lerp_color(indigo_aura, gold_aura, m_t)
        idle_core = lerp_color(indigo_core, gold_core, m_t)
        idle_mid  = lerp_color(indigo_mid, gold_mid, m_t)
        idle_dark = lerp_color(indigo_dark, gold_dark, m_t)

        # Voice interaction overrides (temporary active states)
        if self.voice_state == 'LISTENING':
            aura_col = QColor(20, 184, 166, int(115 * alpha_mult))    # Vibrant Teal
            core_col = QColor(94, 234, 212, int(230 * alpha_mult))
            mid_col  = QColor(20, 184, 166, int(190 * alpha_mult))
            dark_col = QColor(15, 118, 110, int(115 * alpha_mult))
        elif self.voice_state == 'SPEAKING':
            aura_col = QColor(244, 63, 94, int(125 * alpha_mult))     # Solar Rose
            core_col = QColor(253, 164, 175, int(240 * alpha_mult))
            mid_col  = QColor(244, 63, 94, int(195 * alpha_mult))
            dark_col = QColor(190, 18, 60, int(115 * alpha_mult))
        elif self.voice_state == 'THINKING':
            aura_col = QColor(139, 92, 246, int(115 * alpha_mult))    # Astral Violet
            core_col = QColor(196, 181, 253, int(230 * alpha_mult))
            mid_col  = QColor(139, 92, 246, int(190 * alpha_mult))
            dark_col = QColor(109, 40, 217, int(115 * alpha_mult))
        elif self.is_sleeping:
            aura_col = QColor(67, 56, 202, int(35 * alpha_mult))      # Dim indigo slumber
            core_col = QColor(99, 102, 241, int(85 * alpha_mult))
            mid_col  = QColor(67, 56, 202, int(70 * alpha_mult))
            dark_col = QColor(49, 46, 129, int(50 * alpha_mult))
        else:
            aura_col = idle_aura
            core_col = idle_core
            mid_col  = idle_mid
            dark_col = idle_dark

        # 1. OUTER SOFT AMBIENT AURA (No hard pen lines)
        aura_r = r * 1.85
        aura_grad = QRadialGradient(cx, cy, aura_r)
        aura_grad.setColorAt(0.0, aura_col)
        aura_grad.setColorAt(0.50, QColor(aura_col.red(), aura_col.green(), aura_col.blue(), int(aura_col.alpha() * 0.32)))
        aura_grad.setColorAt(1.0, QColor(aura_col.red(), aura_col.green(), aura_col.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(aura_grad))
        painter.drawEllipse(QPointF(cx, cy), aura_r, aura_r)

        # 2. VOICE SPEAKING EXPANDING SOUND WAVE RIPPLE (Only when active TTS is speaking)
        if self.voice_state == 'SPEAKING':
            ripple_r = r + ((self.ticks * 1.3) % 20.0)
            ripple_alpha = int(max(0, 160 * (1.0 - (ripple_r - r) / 20.0) * alpha_mult))
            painter.setPen(QPen(QColor(244, 63, 94, ripple_alpha), 1.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), ripple_r, ripple_r)

        # 3. TRANSLUCENT FROSTED BODY (Completely feathered edge - NO hard solid circle line)
        glass_grad = QRadialGradient(cx - r * 0.28, cy - r * 0.28, r * 1.25)
        g_top = lerp_color(QColor(224, 231, 255, int(85 * alpha_mult)), QColor(255, 237, 213, int(85 * alpha_mult)), m_t)
        g_mid = lerp_color(QColor(67, 56, 202, int(50 * alpha_mult)), QColor(180, 83, 9, int(50 * alpha_mult)), m_t)
        g_edge = lerp_color(QColor(49, 46, 129, int(45 * alpha_mult)), QColor(120, 53, 15, int(45 * alpha_mult)), m_t)
        glass_grad.setColorAt(0.0, g_top)
        glass_grad.setColorAt(0.58, g_mid)
        glass_grad.setColorAt(0.90, g_edge)
        glass_grad.setColorAt(1.0, QColor(g_edge.red(), g_edge.green(), g_edge.blue(), 0))  # Smooth fade to 0 alpha
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glass_grad))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 4. INNER LIVING PLASMA NUCLEUS (Smooth rotating fluid gradient)
        core_r = r * 0.62
        plasma_x = cx + math.cos(self.plasma_rot) * (r * 0.15)
        plasma_y = cy + math.sin(self.plasma_rot) * (r * 0.15)
        plasma_grad = QRadialGradient(plasma_x, plasma_y, core_r)
        plasma_grad.setColorAt(0.0, core_col)
        plasma_grad.setColorAt(0.48, mid_col)
        plasma_grad.setColorAt(0.85, dark_col)
        plasma_grad.setColorAt(1.0, QColor(dark_col.red(), dark_col.green(), dark_col.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(plasma_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # 5. SOFT SPECULAR CRESCENT HIGHLIGHT (Organic 3D depth)
        spec_r = r * 0.32
        spec_x = cx - r * 0.30
        spec_y = cy - r * 0.30
        spec_grad = QRadialGradient(spec_x, spec_y, spec_r)
        spec_grad.setColorAt(0.0, QColor(255, 255, 255, int(150 * alpha_mult)))
        spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(spec_grad))
        painter.drawEllipse(QPointF(spec_x, spec_y), spec_r, spec_r * 0.65)

        # 6. SATELLITE MUSIC CONTROLS ARC (When music is playing & hovered)
        if self.satellites_visible:
            self._draw_satellites(painter, alpha_mult)

    def _draw_satellites(self, painter: QPainter, alpha_mult: float):
        """Renders crisp vector satellite buttons matching current theme tint."""
        from services.music_service import MusicService
        ms = MusicService.get_instance()
        is_playing = bool(ms and ms.player and ms.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        is_shuffle = bool(ms and getattr(ms, 'is_shuffle', False))

        prog = self.hover_progress
        is_gold = (self.music_gold_progress > 0.5)

        for key, rect, _ in self._get_satellite_configs():
            is_hov = (self.hovered_satellite == key)
            btn_alpha = int((240 if is_hov else 190) * prog * alpha_mult)
            border_alpha = int((255 if is_hov else 150) * prog * alpha_mult)

            # Circular pill button background
            bg_grad = QRadialGradient(rect.center(), rect.width() / 2)
            if is_hov:
                if is_gold:
                    bg_grad.setColorAt(0.0, QColor(245, 158, 11, btn_alpha))
                    bg_grad.setColorAt(1.0, QColor(180, 83, 9, btn_alpha))
                    border_pen = QPen(QColor(254, 240, 138, border_alpha), 1.5)
                else:
                    bg_grad.setColorAt(0.0, QColor(99, 102, 241, btn_alpha))
                    bg_grad.setColorAt(1.0, QColor(67, 56, 202, btn_alpha))
                    border_pen = QPen(QColor(199, 210, 254, border_alpha), 1.5)
            else:
                bg_grad.setColorAt(0.0, QColor(24, 18, 30, btn_alpha))
                bg_grad.setColorAt(1.0, QColor(14, 10, 18, btn_alpha))
                border_col = QColor(245, 158, 11, border_alpha) if is_gold else QColor(99, 102, 241, border_alpha)
                border_pen = QPen(border_col, 1.1)

            painter.setPen(border_pen)
            painter.setBrush(QBrush(bg_grad))
            painter.drawEllipse(rect)

            # Draw razor-sharp vector icon with QPainterPath
            bx = rect.center().x()
            by = rect.center().y()
            icon_col = QColor(255, 255, 255, int(245 * prog))
            if key == 'shuffle' and is_shuffle and not is_hov:
                icon_col = QColor(251, 191, 36, int(250 * prog)) if is_gold else QColor(165, 180, 252, int(250 * prog))

            painter.setPen(QPen(icon_col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(QBrush(icon_col) if key in ('play', 'next', 'prev') else Qt.BrushStyle.NoBrush)

            if key == 'shuffle':
                # Two crossed arrows
                p1 = QPainterPath()
                p1.moveTo(bx - 5.0, by - 3.5)
                p1.lineTo(bx - 1.5, by - 3.5)
                p1.lineTo(bx + 2.0, by + 3.5)
                p1.lineTo(bx + 5.0, by + 3.5)
                painter.drawPath(p1)

                p2 = QPainterPath()
                p2.moveTo(bx - 5.0, by + 3.5)
                p2.lineTo(bx - 1.5, by + 3.5)
                p2.lineTo(bx - 0.5, by + 1.8)
                painter.drawPath(p2)

                p3 = QPainterPath()
                p3.moveTo(bx + 0.5, by - 1.8)
                p3.lineTo(bx + 2.0, by - 3.5)
                p3.lineTo(bx + 5.0, by - 3.5)
                painter.drawPath(p3)

                p_arr1 = QPainterPath()
                p_arr1.moveTo(bx + 3.2, by - 5.2)
                p_arr1.lineTo(bx + 5.5, by - 3.5)
                p_arr1.lineTo(bx + 3.2, by - 1.8)
                painter.drawPath(p_arr1)

                p_arr2 = QPainterPath()
                p_arr2.moveTo(bx + 3.2, by + 1.8)
                p_arr2.lineTo(bx + 5.5, by + 3.5)
                p_arr2.lineTo(bx + 3.2, by + 5.2)
                painter.drawPath(p_arr2)

            elif key == 'prev':
                painter.drawLine(QPointF(bx - 4.8, by - 4.2), QPointF(bx - 4.8, by + 4.2))
                t1 = QPolygonF([QPointF(bx - 0.5, by - 4.2), QPointF(bx - 4.5, by), QPointF(bx - 0.5, by + 4.2)])
                painter.drawPolygon(t1)
                t2 = QPolygonF([QPointF(bx + 4.5, by - 4.2), QPointF(bx + 0.5, by), QPointF(bx + 4.5, by + 4.2)])
                painter.drawPolygon(t2)

            elif key == 'play':
                if is_playing:
                    painter.fillRect(QRectF(bx - 3.4, by - 4.2, 2.4, 8.4), icon_col)
                    painter.fillRect(QRectF(bx + 1.0, by - 4.2, 2.4, 8.4), icon_col)
                else:
                    tri = QPolygonF([QPointF(bx - 2.8, by - 4.8), QPointF(bx + 4.4, by), QPointF(bx - 2.8, by + 4.8)])
                    painter.drawPolygon(tri)

            elif key == 'next':
                t1 = QPolygonF([QPointF(bx - 4.5, by - 4.2), QPointF(bx - 0.5, by), QPointF(bx - 4.5, by + 4.2)])
                painter.drawPolygon(t1)
                t2 = QPolygonF([QPointF(bx + 0.5, by - 4.2), QPointF(bx + 4.5, by), QPointF(bx + 0.5, by + 4.2)])
                painter.drawPolygon(t2)
                painter.drawLine(QPointF(bx + 4.8, by - 4.2), QPointF(bx + 4.8, by + 4.2))
