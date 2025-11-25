from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,QSizePolicy,
                                QLineEdit,
                                QFileDialog, QHBoxLayout, QSlider, QScrollArea, QCheckBox, QGridLayout)


from PySide6.QtGui import QPixmap, QImage, QPalette, QPainter, QPen, QMouseEvent,QResizeEvent

from PySide6.QtCore import Qt, Signal
from PIL import Image, ImageQt

from Imaging.SnippingTool import SnippingWindow

import numpy as np
#import cv2
import io

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPixmap, QMouseEvent

class ImageEditor(QWidget):

    task_completed = Signal(str,QImage)

    def __init__(self):

        super().__init__()
        self.setWindowTitle("Image Editor")
        self.setProperty('class','window-background-layer')

        self.image = None                # PIL image
        self.original_image = None       # Store original image
        self.original_image_name = None  # To store the image name from QTextEdit        

        self.cropping = False
        self.crop_start = None
        self.crop_end = None
        self.crop_rect = None

        container = QWidget()
        #container.setStyleSheet('background-color:green;')

        self.image_label = QLabel(container)
        self.image_label.setText('No image\nloaded')
        self.image_label.setProperty('class','image-box')
        self.image_label.setMinimumSize(250,250)
        self.image_label.mousePressEvent = self.start_crop
        self.image_label.mouseMoveEvent = self.update_crop
        self.image_label.mouseReleaseEvent = self.finish_crop        
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setBackgroundRole(QPalette.ColorRole.Base)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(container)
        self.scroll_area.setMinimumSize(250,250)

        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.resizeEvent = self.on_scroll_area_resized
        rotate_box = QHBoxLayout()
        rotate_box.addWidget(QLabel('Rotate      '))
        rotate_input = QLineEdit('90')
        rotate__left = QPushButton('+ ⟲')
        rotate_right = QPushButton('- ⟲')
        rotate_box.addWidget(rotate_input)
        rotate_box.addWidget(rotate__left)
        rotate_box.addWidget(rotate_right)

        rotate__left.clicked.connect(lambda _: self.rotate_image(+int(rotate_input.text())))
        rotate_right.clicked.connect(lambda _: self.rotate_image(-int(rotate_input.text())))

        flip_box = QHBoxLayout()
        btn_flip_horizontal = QPushButton("Horizontal")
        btn_flip_horizontal.clicked.connect(lambda _: self.flip_image(Image.Transpose.FLIP_LEFT_RIGHT))

        btn_flip_vertical = QPushButton("Vertical")
        btn_flip_vertical.clicked.connect(lambda _: self.flip_image(Image.Transpose.FLIP_TOP_BOTTOM))

        flip_box.addWidget(QLabel('Flip                                                           '))
        flip_box.addWidget(btn_flip_horizontal)
        flip_box.addWidget(btn_flip_vertical)
        zoom_box = QHBoxLayout()
        zoom_input = QLineEdit('10')
        btn1 = QPushButton('+')
        btn1.setProperty('class','mini')
        
        btn2 = QPushButton("-")
        btn2.setProperty('class','mini')       
        
        btn1.clicked.connect(lambda: (
            self.width_slider.setValue(int(zoom_input.text()) + self.width_slider.value()),
            self.height_slider.setValue(int(zoom_input.text()) + self.height_slider.value())
            ))
        btn2.clicked.connect(lambda: (
            self.width_slider.setValue(-int(zoom_input.text()) + self.width_slider.value()),
            self.height_slider.setValue(-int(zoom_input.text()) + self.height_slider.value())
            ))
        

        zoom_box.addWidget(QLabel('Zoom (%)'))
        zoom_box.addWidget(zoom_input)
        zoom_box.addWidget(btn1)
        zoom_box.addWidget(btn2)
        
        fit_box = QHBoxLayout()
        
        fit_btn = QPushButton('Fit')
        fit_w_btn = QPushButton('Fit width')
        fit_h_btn = QPushButton('Fit height')
        crop_button = QPushButton("Crop")

        fit_box.addWidget(fit_btn)
        fit_box.addWidget(fit_w_btn)
        fit_box.addWidget(fit_h_btn)
        fit_box.addWidget(crop_button)

        crop_button.clicked.connect(self.toggle_crop_mode)
        fit_btn.clicked.connect(self.fit_image)
        fit_w_btn.clicked.connect(self.fit_width)
        fit_h_btn.clicked.connect(self.fit_height)

        save_box = QHBoxLayout()
        clear_btn = QPushButton('Clear')
        load_btn = QPushButton("Load")
        snip_btn = QPushButton('Snip')
        save_btn = QPushButton("Save")
        close_btn = QPushButton("Close")
        save_box.addWidget(load_btn)
        save_box.addWidget(snip_btn)
        save_box.addWidget(clear_btn)
        save_box.addWidget(save_btn)
        save_box.addWidget(close_btn)
        
        # quality
        quality_box = QHBoxLayout()
        transparent_btn = QPushButton("Remove Background")
        enhance_btn = QPushButton("Enhance")
        restore_btn = QPushButton("Restore")

        quality_box.addWidget(restore_btn)
        quality_box.addWidget(enhance_btn)
        quality_box.addWidget(transparent_btn)

        # Sliders
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 255)
        self.alpha_slider.setValue(255)
        self.alpha_slider.valueChanged.connect(lambda alpha: self.update_alpha_from_slider(alpha))

        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(10, 500)
        self.width_slider.setValue(100)
        self.width_slider.valueChanged.connect(self.update_resize_from_sliders)

        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(10, 500)
        self.height_slider.setValue(100)
        self.height_slider.valueChanged.connect(self.update_resize_from_sliders)

        self.keep_aspect_checkbox = QCheckBox("Keep Aspect Ratio")
        self.keep_aspect_checkbox.setChecked(False)


        # Layout
        layout = QGridLayout()
        # add main area for original image
        layout.addWidget(self.scroll_area,0,0)
        
        controls = QVBoxLayout()
        controls.addLayout(rotate_box)
        controls.addLayout(zoom_box)
        controls.addLayout(fit_box)
        controls.addLayout(flip_box)

        controls.addWidget(QLabel("Transparency:"))
        controls.addWidget(self.alpha_slider)
        controls.addWidget(QLabel("Resize Width (%):"))
        controls.addWidget(self.width_slider)
        controls.addWidget(QLabel("Resize Height (%):"))
        controls.addWidget(self.height_slider)
        controls.addWidget(self.keep_aspect_checkbox)
        controls.addLayout(quality_box)

        controls.addLayout(save_box)
        controls.addStretch(1)

        # add controls to right edge    
        layout.addLayout(controls,0,1)
        layout.setColumnStretch(0,1)
        self.setLayout(layout)

        # Connect signals to slots
        load_btn.clicked.connect(self.load_from_file)
        snip_btn.clicked.connect(self.run_snipping_tool)
        save_btn.clicked.connect(self.save_image)
        clear_btn.clicked.connect(self.clear_image)
        close_btn.clicked.connect(self.close)
        transparent_btn.clicked.connect(self.make_background_transparent)
        #enhance_btn.clicked.connect(self.enhance_quality)
        restore_btn.clicked.connect(self.restore_original_image)
    
    def toggle_crop_mode(self):
        self.cropping = not self.cropping
        self.setCursor(Qt.CursorShape.CrossCursor if self.cropping else Qt.CursorShape.ArrowCursor)

    def start_crop(self, event:QMouseEvent):
        
        if not self.image: self.cropping = False
        
        if self.cropping:
            sz1 = self.image.size
            sz2 = self.image_label.size()
            dif_x = int((sz2.width() - sz1[0])/2)
            dif_y = int((sz2.height() - sz1[1])/2)
            
            if dif_x < 0: dif_x = 0#event.position().toPoint().x()
            if dif_y < 0: dif_y = 0#event.position().toPoint().y()

            self.crop_start = event.position().toPoint() - QPoint(dif_x, dif_y)

    def update_crop(self, event:QMouseEvent):
        
        if self.cropping and self.crop_start:

            sz1 = self.image.size
            sz2 = self.image_label.size()
            dif_x = int((sz2.width() - sz1[0])/2)
            dif_y = int((sz2.height() - sz1[1])/2)
            
            if dif_x < 0: dif_x = 0 #event.position().toPoint().x()
            if dif_y < 0: dif_y = 0 #event.position().toPoint().y()

            self.crop_end = event.position().toPoint() - QPoint(dif_x, dif_y)
            
            self.crop_rect = QRect(self.crop_start, self.crop_end).normalized()
            self.display_image()

    def finish_crop(self, event):
        
        if self.cropping and self.crop_rect:
            # Map crop_rect to image coordinates
            #label_size = self.image_label.size()
            pixmap = self.image_label.pixmap()            
            
            if pixmap:
                #img_w, img_h = self.image.size
                x_scale = 1
                y_scale = 1
        
                x1 = int(self.crop_rect.left() * x_scale)
                y1 = int(self.crop_rect.top() * y_scale)
                x2 = int(self.crop_rect.right() * x_scale)
                y2 = int(self.crop_rect.bottom() * y_scale)

                self.image = self.image.crop((x1 , y1, x2, y2))

                self.crop_start = self.crop_end = self.crop_rect = None
                self.cropping = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.display_image()


    def clear_image(self):
        self.image = None                # PIL image
        self.original_image = None       # Store original image
        self.original_image_name = None  # To store the image name from QTextEdit
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("No image\nloaded")
        #self.image_label.setFixedSize(self.scroll_area.size())

    def close(self):
        name, img = self.get_edited_image()
        self.task_completed.emit(name,img)  # emit final image
        super().close()

    def load_from_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_name:
            self.image = Image.open(file_name).convert("RGBA")
            
            self.original_image = self.image.copy()
            self.original_image_name = None
            self.reset_sliders()
            self.display_image()

    def load_from_resource(self, resource):
        
        if isinstance(resource, (QPixmap, QImage)):
            if isinstance(resource, QPixmap):
                resource = resource.toImage()

            self.image = ImageQt.fromqimage(resource.convertToFormat(QImage.Format.Format_RGBA8888))
            
            self.original_image = self.image.copy()
            self.original_image_name = None
            self.reset_sliders()
            self.display_image()
        
    def display_image(self):
        
        if self.image:
            qimage = ImageQt.ImageQt(self.image)
            pixmap = QPixmap.fromImage(qimage)
            # Drow crop box
            if self.cropping and self.crop_rect:
                painter = QPainter(pixmap)
                pen = QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                self.cropping  = True
                
                painter.drawRect(self.crop_rect)
                painter.end()
                

            self.image_label.setPixmap(pixmap)
            self.image_label.setFixedSize(pixmap.size())

            self.update_display_area()


    def update_display_area(self):
        container:QWidget = self.image_label.parent()
        container.setFixedSize(self.image_label.size())
        
        self.image_label.move(0,0)
        
        if self.image_label.width() * self.image_label.height() < self.scroll_area.viewport().width() * self.scroll_area.viewport().height():
                
                dif_x = self.scroll_area.viewport().width() - self.image_label.width()
                dif_y = self.scroll_area.viewport().height() - self.image_label.height()
                container.setFixedSize(self.scroll_area.viewport().size())

                self.image_label.move(int(dif_x/2), int(dif_y/2))
        
    def on_scroll_area_resized(self,event:QResizeEvent): self.update_display_area()

    def fit_image(self):

        self.fit_height()

        self.fit_width()

    def fit_width(self):

        w = self.scroll_area.width()
        
        w_s = int((w) * 100/ self.original_image.width)

        self.width_slider.setValue(w_s)

    def fit_height(self):

        h = self.scroll_area.height()
        
        h_s = int((h) * 100/self.original_image.height)

        self.height_slider.setValue(h_s)
    

    def update_resize_from_sliders(self):
        
        if self.image and self.original_image:
            
            width_percent = self.width_slider.value()
            height_percent = self.height_slider.value()
            
            if self.keep_aspect_checkbox.isChecked():
                height_percent = width_percent
                self.height_slider.blockSignals(True)
                self.height_slider.setValue(width_percent)
                self.height_slider.blockSignals(False)
            
            orig_w, orig_h = self.original_image.size
            
            new_size = (int(orig_w * width_percent / 100), int(orig_h * height_percent / 100))
            
            self.image = self.image.resize(new_size, Image.Resampling.LANCZOS)
            
            self.display_image()

    def rotate_image(self, degree:int):
        if self.image:
            
            self.image = self.image.rotate(degree, expand=True)
            self.display_image()

    def flip_image(self,flip: Image.Transpose):
        
        if self.image:
            self.image = self.image.transpose(flip)
            self.display_image()

    def update_alpha_from_slider(self, alpha:int):
        if self.image:
            r, g, b, a = self.image.split()
            a = Image.new("L", self.image.size, color=alpha)
            self.image = Image.merge("RGBA", (r, g, b, a))
            self.display_image()

    def make_background_transparent(self):
        if self.image:
            img = np.array(self.image)
            r, g, b, a = img[..., 0], img[..., 1], img[..., 2], img[..., 3]
            background_mask = (r > 240) & (g > 240) & (b > 240)
            img[..., 3][background_mask] = 0
            self.image = Image.fromarray(img, mode='RGBA')
            self.display_image()

    def enhance_quality(self):
        pass
        """if self.image:
            cv_img = cv2.cvtColor(np.array(self.image), cv2.COLOR_RGBA2BGRA)

            cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 10, 10, 7, 21)
            cv_img = cv2.detailEnhance(cv_img, sigma_s=10, sigma_r=0.15)

            # Sharpening
            sharpen_kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
            cv_img = cv2.filter2D(cv_img, -1, sharpen_kernel)

            # Convert back
            self.image = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA))

            
            self.display_image()
        """

    def restore_original_image(self):
        if self.original_image:
            self.image = self.original_image.copy()
            self.reset_sliders()
            self.display_image()

    def reset_sliders(self):
        self.alpha_slider.setValue(255)
        self.width_slider.setValue(100)
        self.height_slider.setValue(100)

    def get_edited_image(self):
        
        if self.image:
            buffer = io.BytesIO()
            self.image.save(buffer, format="PNG")
            buffer.seek(0)
            qimg = QImage.fromData(buffer.read())

            image_name = f"image_{id(qimg)}"
            return image_name, qimg
        return '', None
     
    def save_image(self):
        if self.image:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if file_path:
                # Ensure the extension is correct
                if not file_path.lower().endswith(('png', 'jpg', 'jpeg', 'bmp')):
                    file_path += '.png'
                
                self.image.save(file_path)

    def run_snipping_tool(self):
        
        self.hide()
        snipping_window = SnippingWindow(self)
        snipping_window.screen_captured.connect(lambda data:
            (
                self.load_from_resource(data),
                self.show()
            ))

        snipping_window.screen_capture_canceled.connect(self.show)

        snipping_window.showFullScreen()  # Ensure full coverage
        snipping_window.activateWindow()
        snipping_window.raise_()


from PySide6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)  # Create the application
    window = ImageEditor()  # Create the main window
    window.show()  # Show the window
    sys.exit(app.exec())  # Start the application event loop
