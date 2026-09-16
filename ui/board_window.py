import os
import sys
from datetime import datetime
from PyQt6.QtCore import Qt, QPoint, QRectF, QSize, QByteArray, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QPixmap, QIcon, QCursor, QGuiApplication,
    QRadialGradient, QBrush
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QFrame, QButtonGroup, QMenu
)

SVG_PEN = '<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>'
SVG_ERASER = '<path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21"/><path d="M22 21H7"/><path d="m5 11 9 9"/>'
SVG_CAMERA = '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>'
SVG_TRASH = '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
SVG_CLOSE = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
SVG_GRIP = '<circle cx="9" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="15" cy="18" r="1.5"/>'

PALETTE_COLORS = [
    ("#6366f1", "Indigo"),
    ("#10b981", "Emerald"),
    ("#f59e0b", "Amber"),
    ("#ef4444", "Crimson"),
    ("#06b6d4", "Cyan"),
    ("#ffffff", "White"),
]

THICKNESS_LEVELS = [
    (2, "Fine (2px)"),
    (4, "Medium (4px)"),
    (8, "Bold (8px)"),
    (14, "Broad (14px)"),
]

def create_svg_icon(svg_inner, stroke_color='#f3f4f6', fill_color='none', size=16, stroke_width=2):
    svg_xml = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">
    {svg_inner}
    </svg>'''
    renderer = QSvgRenderer(QByteArray(svg_xml.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def create_pen_cursor(color, thickness):
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Outer ring
    painter.setPen(QPen(QColor(15, 18, 30, 200), 1.5))
    painter.setBrush(QColor(color))
    radius = max(3.0, min(8.0, thickness / 2.0 + 2.0))
    painter.drawEllipse(QPoint(12, 12), int(radius), int(radius))
    
    # Center crosshair dot
    painter.setPen(QPen(QColor(255, 255, 255, 220), 1.0))
    painter.drawPoint(12, 12)
    painter.end()
    return QCursor(pix, 12, 12)

def create_eraser_cursor(thickness):
    size = max(24, thickness + 4)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Eraser circle outline with dash
    pen = QPen(QColor(244, 63, 94, 230), 1.5, Qt.PenStyle.DashLine)
    painter.setPen(pen)
    painter.setBrush(QColor(244, 63, 94, 40))
    r = int(thickness / 2)
    center = int(size / 2)
    painter.drawEllipse(QPoint(center, center), r, r)
    painter.end()
    return QCursor(pix, center, center)

class OkumBoardCanvas(QWidget):
    def __init__(self, toolbar):
        super().__init__()
        self.toolbar = toolbar
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)
        
        # State
        self.current_tool = 'marker' # 'marker' or 'eraser'
        self.marker_color = QColor(99, 102, 241) # Default Indigo
        self.marker_thickness = 4
        self.eraser_thickness = 24
        
        self._drawing = False
        self._last_point = QPoint()
        
        screen_geo = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        
        # Persistent Drawing Pixmap
        self.canvas_pixmap = QPixmap(screen_geo.size())
        self.canvas_pixmap.fill(Qt.GlobalColor.transparent)
        
        self._update_cursor()

    def set_tool(self, tool_name):
        self.current_tool = tool_name
        self._update_cursor()

    def set_color(self, hex_color):
        self.marker_color = QColor(hex_color)
        self._update_cursor()

    def set_thickness(self, px):
        self.marker_thickness = px
        self._update_cursor()

    def _update_cursor(self):
        if self.current_tool == 'marker':
            self.setCursor(create_pen_cursor(self.marker_color, self.marker_thickness))
        elif self.current_tool == 'eraser':
            self.setCursor(create_eraser_cursor(self.eraser_thickness))

    def clear_canvas(self):
        self.canvas_pixmap.fill(Qt.GlobalColor.transparent)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.canvas_pixmap)

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if self.toolbar and self.toolbar.isVisible() and self.toolbar.geometry().contains(pos):
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._last_point = pos
            self._draw_stroke(self._last_point, self._last_point)
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        # Seamlessly switch to clickable ArrowCursor whenever entering toolbar bounds
        if self.toolbar and self.toolbar.isVisible() and self.toolbar.geometry().contains(pos):
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if not self._drawing:
                event.ignore()
                return
        else:
            if not self._drawing:
                self._update_cursor()

        if self._drawing and event.buttons() == Qt.MouseButton.LeftButton:
            current_point = pos
            self._draw_stroke(self._last_point, current_point)
            self._last_point = current_point
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = False
            event.accept()

    def _draw_stroke(self, p1, p2):
        painter = QPainter(self.canvas_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.current_tool == 'marker':
            pen = QPen(
                self.marker_color,
                self.marker_thickness,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            )
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif self.current_tool == 'eraser':
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(
                Qt.GlobalColor.transparent,
                self.eraser_thickness,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            )
            painter.setPen(pen)
            painter.drawLine(p1, p2)

        painter.end()

        # Update affected bounding rect with padding
        margin = max(self.marker_thickness, self.eraser_thickness) + 4
        x = min(p1.x(), p2.x()) - margin
        y = min(p1.y(), p2.y()) - margin
        w = abs(p1.x() - p2.x()) + margin * 2
        h = abs(p1.y() - p2.y()) + margin * 2
        self.update(x, y, w, h)


class OkumBoardToolbar(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(48)
        self.setObjectName("OkumBoardToolbar")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self.color_index = 0
        self.thickness_index = 1 # 4px
        
        self._dragging = False
        self._drag_pos = QPoint()

        self._init_ui()
        self._position_on_screen()

    def enterEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.manager and self.manager.canvas:
            self.manager.canvas.setCursor(Qt.CursorShape.ArrowCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.manager and self.manager.canvas:
            self.manager.canvas._update_cursor()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())
        bg_color = QColor(18, 22, 38, 245)
        border_pen = QPen(QColor(99, 102, 241, 150), 1.5)

        painter.setPen(border_pen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 12.0, 12.0)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Drag Handle Grip
        self.lbl_grip = QLabel(self)
        self.lbl_grip.setPixmap(create_svg_icon(SVG_GRIP, stroke_color="#6b7280", size=14).pixmap(14, 14))
        self.lbl_grip.setToolTip("Drag toolbar anywhere on screen")
        self.lbl_grip.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        layout.addWidget(self.lbl_grip)

        # Tool group (Marker vs Eraser)
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        # Marker Tool Button
        self.btn_marker = QPushButton(self)
        self.btn_marker.setIcon(create_svg_icon(SVG_PEN, stroke_color="#f3f4f6", size=16))
        self.btn_marker.setIconSize(QSize(16, 16))
        self.btn_marker.setFixedSize(32, 32)
        self.btn_marker.setCheckable(True)
        self.btn_marker.setChecked(True)
        self.btn_marker.setObjectName("btnBoardTool")
        self.btn_marker.setToolTip("Marker (Draw on Screen)")
        self.btn_marker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_marker.clicked.connect(self._select_marker)
        self.tool_group.addButton(self.btn_marker, 0)
        layout.addWidget(self.btn_marker)

        # Eraser Tool Button
        self.btn_eraser = QPushButton(self)
        self.btn_eraser.setIcon(create_svg_icon(SVG_ERASER, stroke_color="#f3f4f6", size=16))
        self.btn_eraser.setIconSize(QSize(16, 16))
        self.btn_eraser.setFixedSize(32, 32)
        self.btn_eraser.setCheckable(True)
        self.btn_eraser.setObjectName("btnBoardTool")
        self.btn_eraser.setToolTip("Eraser (Contact Erase)")
        self.btn_eraser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eraser.clicked.connect(self._select_eraser)
        self.tool_group.addButton(self.btn_eraser, 1)
        layout.addWidget(self.btn_eraser)

        # Sep
        sep1 = QFrame(self)
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: rgba(255, 255, 255, 0.15); margin: 6px 1px;")
        layout.addWidget(sep1)

        # Color Palette Button
        self.btn_color = QPushButton(self)
        self.btn_color.setFixedSize(32, 32)
        self.btn_color.setObjectName("btnBoardTool")
        self.btn_color.setToolTip(f"Color: {PALETTE_COLORS[self.color_index][1]} (Click to Cycle)")
        self.btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color.clicked.connect(self._cycle_color)
        self._update_color_button_icon()
        layout.addWidget(self.btn_color)

        # Thickness Selector Button
        self.btn_thickness = QPushButton(self)
        self.btn_thickness.setFixedSize(32, 32)
        self.btn_thickness.setObjectName("btnBoardTool")
        self.btn_thickness.setToolTip(f"Thickness: {THICKNESS_LEVELS[self.thickness_index][1]} (Click to Cycle)")
        self.btn_thickness.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_thickness.clicked.connect(self._cycle_thickness)
        self._update_thickness_button_icon()
        layout.addWidget(self.btn_thickness)

        # Sep
        sep2 = QFrame(self)
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: rgba(255, 255, 255, 0.15); margin: 6px 1px;")
        layout.addWidget(sep2)

        # Screenshot Button
        self.btn_screenshot = QPushButton(self)
        self.btn_screenshot.setIcon(create_svg_icon(SVG_CAMERA, stroke_color="#38bdf8", size=16))
        self.btn_screenshot.setIconSize(QSize(16, 16))
        self.btn_screenshot.setFixedSize(32, 32)
        self.btn_screenshot.setObjectName("btnBoardTool")
        self.btn_screenshot.setToolTip("Take Full Screenshot (Saved to ~/Pictures/OkumScreenshots/)")
        self.btn_screenshot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_screenshot.clicked.connect(self.manager.take_screenshot)
        layout.addWidget(self.btn_screenshot)

        # Clear Canvas Button
        self.btn_clear = QPushButton(self)
        self.btn_clear.setIcon(create_svg_icon(SVG_TRASH, stroke_color="#f87171", size=16))
        self.btn_clear.setIconSize(QSize(16, 16))
        self.btn_clear.setFixedSize(32, 32)
        self.btn_clear.setObjectName("btnBoardTool")
        self.btn_clear.setToolTip("Clear All Annotations")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.manager.clear_canvas)
        layout.addWidget(self.btn_clear)

        # Sep
        sep3 = QFrame(self)
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color: rgba(255, 255, 255, 0.15); margin: 6px 1px;")
        layout.addWidget(sep3)

        # Close Board Button
        self.btn_close = QPushButton(self)
        self.btn_close.setIcon(create_svg_icon(SVG_CLOSE, stroke_color="#94a3b8", size=16))
        self.btn_close.setIconSize(QSize(16, 16))
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setObjectName("btnHeaderControl")
        self.btn_close.setToolTip("Close Okum Board")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.manager.close_board)
        layout.addWidget(self.btn_close)

    def _position_on_screen(self):
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - 360) // 2
        y = screen.height() - 110
        self.move(x, y)

    def _select_marker(self):
        self.manager.canvas.set_tool('marker')

    def _select_eraser(self):
        self.manager.canvas.set_tool('eraser')

    def _cycle_color(self):
        self.color_index = (self.color_index + 1) % len(PALETTE_COLORS)
        hex_val, name = PALETTE_COLORS[self.color_index]
        self.btn_color.setToolTip(f"Color: {name} (Click to Cycle)")
        self._update_color_button_icon()
        self.manager.canvas.set_color(hex_val)
        if self.manager.canvas.current_tool != 'marker':
            self.btn_marker.setChecked(True)
            self.manager.canvas.set_tool('marker')

    def _update_color_button_icon(self):
        hex_val, _ = PALETTE_COLORS[self.color_index]
        pix = QPixmap(18, 18)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(15, 18, 30), 1.2))
        p.setBrush(QColor(hex_val))
        p.drawEllipse(1, 1, 16, 16)
        p.end()
        self.btn_color.setIcon(QIcon(pix))

    def _cycle_thickness(self):
        self.thickness_index = (self.thickness_index + 1) % len(THICKNESS_LEVELS)
        px, name = THICKNESS_LEVELS[self.thickness_index]
        self.btn_thickness.setToolTip(f"Thickness: {name} (Click to Cycle)")
        self._update_thickness_button_icon()
        self.manager.canvas.set_thickness(px)
        if self.manager.canvas.current_tool != 'marker':
            self.btn_marker.setChecked(True)
            self.manager.canvas.set_tool('marker')

    def _update_thickness_button_icon(self):
        px, _ = THICKNESS_LEVELS[self.thickness_index]
        pix = QPixmap(20, 20)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(243, 244, 246))
        r = max(2, min(8, px // 2 + 1))
        p.drawEllipse(QPoint(10, 10), r, r)
        p.end()
        self.btn_thickness.setIcon(QIcon(pix))


class OkumBoardManager:
    _instance = None

    def __init__(self):
        self.toolbar = OkumBoardToolbar(self)
        self.canvas = OkumBoardCanvas(self.toolbar)
        self.is_active = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = OkumBoardManager()
        return cls._instance

    def show_board(self):
        self.is_active = True
        self.canvas.show()
        self.canvas.raise_()
        self.toolbar.show()
        self.toolbar.raise_()

    def hide_board(self):
        self.is_active = False
        self.canvas.hide()
        self.toolbar.hide()

    def toggle_board(self):
        if self.is_active:
            self.hide_board()
        else:
            self.show_board()

    def clear_canvas(self):
        self.canvas.clear_canvas()

    def take_screenshot(self):
        # Hide toolbar briefly to capture clean desktop with annotations
        self.toolbar.hide()
        QTimer.singleShot(150, self._capture_screenshot_proc)

    def _capture_screenshot_proc(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.toolbar.show()
            return

        pix = screen.grabWindow(0)
        
        # Save to ~/Pictures/OkumScreenshots/
        shots_dir = os.path.expanduser('~/Pictures/OkumScreenshots')
        os.makedirs(shots_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"okum_board_{timestamp}.png"
        filepath = os.path.join(shots_dir, filename)
        pix.save(filepath, "PNG")

        self.toolbar.show()
        self.toolbar.raise_()
        print(f"Okum Board Screenshot saved: {filepath}")

    def close_board(self):
        self.hide_board()
        self.clear_canvas()
