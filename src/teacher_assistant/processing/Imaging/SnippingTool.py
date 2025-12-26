
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog,QLabel
from PySide6.QtCore import Qt, QRect,Signal
from PySide6.QtGui import QPainter, QColor,QKeyEvent,QPixmap
from PIL import Image

class SnippingTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Snipping Tool | v1.0")
        self.setGeometry(100, 100, 400, 200)

        # Create a button to start snipping
        self.snip_button = QPushButton("Start Snipping", self)
        self.snip_button.clicked.connect(self.start_snipping)
        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.save_screenshot)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.snip_button)
        layout.addWidget(self.save_button)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.display_label = QLabel()
        layout.addWidget(self.display_label)
        layout.addStretch()

    def start_snipping(self):
        self.hide()  # Hide the main window
        self.snipping_window = SnippingWindow(self)
        self.snipping_window.showFullScreen()  # Ensure full coverage
        self.snipping_window.activateWindow()
        self.snipping_window.raise_()
    
    def keyPressEvent(self, event: QKeyEvent):
        #Override to detect ESC key press.#
        if event.key() == Qt.Key.Key_Escape:
            print("Snipping canceled")  # Debugging
            self.show()  # Close the snipping window
    def show_screenshot(self,pixmap:QPixmap):
        self.display_label.resize(pixmap.size())
        
        self.display_label.setPixmap(pixmap)


    def save_screenshot(self):#, pixmap):
        # Open a file dialog to save the screenshot
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "", "PNG Files (*.png);;JPEG Files (*.jpg)", options=options
        )
        if file_name:
            # Convert QPixmap to PIL Image and save in high quality
            image =self.display_label.pixmap()# pixmap.toImage()
            image = Image.fromqimage(image)
            
            # Save as PNG for better quality (lossless format)
            image.save(file_name, "PNG")


class SnippingWindow(QWidget): 
    
    screen_captured = Signal(QPixmap) 
    screen_capture_canceled = Signal(QWidget)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(QApplication.primaryScreen().geometry())  # Full screen size
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.start_point = None
        self.end_point = None

    def keyPressEvent(self, event: QKeyEvent):
        # Override to detect ESC key press.
        if event.key() == Qt.Key.Key_Escape:
            print("Snipping canceled")  # Debugging
            self.close()  # Close the snipping window
            self.screen_capture_canceled.emit(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
        painter.setRenderHint(QPainter.RenderHint.NonCosmeticBrushPatterns)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.VerticalSubpixelPositioning)

        # Draw semi-transparent black overlay without alpha blending issues
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 1))  # Adjust opacity for visibility
        painter.drawRect(self.rect())
        
        # Draw selection rectangle
        if self.start_point and self.end_point:
            rect = QRect(self.start_point, self.end_point).normalized()

            # Remove overlay from the selected area (only for visual effect)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, QColor(0, 0, 0, 0))

            # Draw a visible red border
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QColor(255, 0, 0, 255))  # Red border
            painter.drawRect(rect)

        super().paintEvent(event)

    def mousePressEvent(self, event):
        self.start_point = event.position().toPoint()
        self.end_point = event.position().toPoint()
        self.update()

    def mouseMoveEvent(self, event):
        self.end_point = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end_point = event.position().toPoint()
        self.capture_selection()
        self.close()

    def capture_selection(self):
        # Get screen instance
        screen = QApplication.primaryScreen()

        # Convert points to global coordinates
        start_screen = self.mapToGlobal(self.start_point)
        end_screen = self.mapToGlobal(self.end_point)

        # Create a QRect from the selection area
        rect = QRect(start_screen, end_screen).normalized()

        # Capture the selected region (behind the overlay) and remove red rectangle
        pixmap = screen.grabWindow(0, rect.x()+1, rect.y()+1, rect.width()-2, rect.height()-2)

        # Ensure that the capture does not introduce unwanted artifacts
        #pixmap = self.fix_pixmap_quality(pixmap)

        self.close()
        self.screen_captured.emit(pixmap)
        # Pass the screenshot to the main window for saving
        #self.parent().show_screenshot(pixmap)
        #self.parent().show()

    def fix_pixmap_quality(self, pixmap):
        # Fix any issues with quality after capture (e.g., extra color, low resolution)
        # Optionally scale it for high-DPI screens
        screen = QApplication.primaryScreen()
        device_pixel_ratio = screen.devicePixelRatio()

        if device_pixel_ratio > 1:
            # Scale the pixmap for high-DPI
            pixmap = pixmap.scaled(pixmap.size() * device_pixel_ratio,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)

        # Ensure the image maintains quality by returning the pixmap
        return pixmap
