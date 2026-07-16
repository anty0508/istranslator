from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

RADIUS = 18
H_MARGIN = 14
V_MARGIN = 9
MAX_WIDTH = 560
FONT_PX = 15
BG_COLOR = QColor(20, 22, 28, 178)  # 0.7 opacity
BORDER_COLOR = QColor(150, 160, 190, 110)


class OverlayTooltip(QFrame):
    def __init__(self, timeout_ms=8000):
        super().__init__()
        self._timeout = timeout_ms
        self._anchor = QPoint(0, 0)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.ToolTip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(H_MARGIN, V_MARGIN, H_MARGIN, V_MARGIN)

        font = QFont()
        font.setPixelSize(FONT_PX)

        self.body = QLabel("", self)
        self.body.setFont(font)
        self.body.setWordWrap(True)
        self.body.setStyleSheet("color: rgba(248, 250, 252, 255); background: transparent;")
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.body)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(BORDER_COLOR, 1))
        painter.setBrush(BG_COLOR)
        painter.drawRoundedRect(rect, RADIUS, RADIUS)

    def set_timeout(self, timeout_ms):
        self._timeout = timeout_ms

    def _fit(self, text):
        fm = self.body.fontMetrics()
        max_text = MAX_WIDTH - 2 * H_MARGIN
        lines = text.split("\n") if text else [""]
        natural = max((fm.horizontalAdvance(line) for line in lines), default=0)
        self.body.setFixedWidth(min(natural + 2, max_text))
        self.body.setText(text)
        self.adjustSize()
        self._reposition()

    def begin(self):
        from PyQt6.QtGui import QCursor

        self._anchor = QCursor.pos()
        self._fit("…")
        self.show()
        self.raise_()
        self._timer.stop()

    def update_text(self, text):
        self._fit(text)
        if not self.isVisible():
            self.show()
        if self._timeout and self._timeout > 0:
            self._timer.start(self._timeout)

    def _reposition(self):
        pos = self._anchor
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()

        x = pos.x() + 16
        y = pos.y() + 20
        w = self.width()
        h = self.height()

        if x + w > geo.right():
            x = geo.right() - w - 8
        if y + h > geo.bottom():
            y = pos.y() - h - 12
        x = max(geo.left() + 8, x)
        y = max(geo.top() + 8, y)

        self.move(x, y)

    def mousePressEvent(self, event):
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
