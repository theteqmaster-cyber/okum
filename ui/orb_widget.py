import math
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QFont, QCursor
from PyQt6.QtWidgets import QWidget

class FloatingOrb(QWidget):
    def __init__(self, toggle_callback):
        super().__init__()
        self.toggle_callback = toggle_callback
        
        # Window attributes for native OS floating desktop widget
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setFixedSize(64, 64)

        # Dragging variables
        self._dragging = False
        self._drag_position = QPoint()
        self._click_threshold = False

        # Pulse animation timer
        self._pulse_phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_pulse)
        self.timer.start(50)

        # Move default position to bottom right of primary screen
        self.setToolTip("Click to open Okum Quick Assistant (Notes & Ask LLM) — Drag to move")

    def _animate_pulse(self):
        self._pulse_phase = (self._pulse_phase + 0.05) % (2 * math.pi)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._click_threshold = False
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_position
            self._click_threshold = True
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if not self._click_threshold:
                # Simple click without drag
                self.toggle_callback()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())
        center_x = rect.width() / 2
        center_y = rect.height() / 2
        radius = 24.0

        # Glassmorphic Base Backdrop (Almost transparent dark glass with light highlight border)
        glass_bg = QColor(15, 18, 30, 160)  # ~62% dark translucent glass backdrop
        glass_border = QPen(QColor(255, 255, 255, 50), 1.2)  # Frosted glass rim
        painter.setPen(glass_border)
        painter.setBrush(glass_bg)
        painter.drawEllipse(QPointF(center_x, center_y), radius + 7, radius + 7)

        # Outer pulse ring
        pulse_scale = 1.0 + 0.15 * math.sin(self._pulse_phase)
        ring_radius = radius * pulse_scale + 4

        ring_pen = QPen(QColor(99, 102, 241, 120))
        ring_pen.setWidthF(1.8)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), ring_radius, ring_radius)

        # Core Radial Gradient Orb
        gradient = QRadialGradient(center_x - 6, center_y - 6, radius + 10)
        gradient.setColorAt(0.0, QColor(139, 92, 246)) # Violet
        gradient.setColorAt(0.6, QColor(99, 102, 241)) # Indigo
        gradient.setColorAt(1.0, QColor(6, 182, 212))  # Cyan

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # Inner Icon/Symbol (Okum "O" Core)
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.drawEllipse(QPointF(center_x, center_y), 5.0, 5.0)

        # Status Dot (Green = Active)
        painter.setBrush(QColor(16, 185, 129)) # Green
        painter.setPen(QPen(QColor(15, 18, 30), 1.5))
        painter.drawEllipse(QPointF(center_x + radius - 4, center_y - radius + 4), 4.5, 4.5)
