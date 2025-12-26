
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QBuffer,QByteArray
import base64

def pixmap_to_base64(pixmap:QPixmap):
    # Convert QPixmap to QImage
    image = pixmap.toImage()

    # Convert QImage to bytes
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")  # Save as PNG format
    buffer.close()

    # Convert bytes to base64
    base64_data = base64.b64encode(byte_array.data()).decode("utf-8")
    
    return base64_data


def bytea_to_pixmap(bytea_data):

    if bytea_data:
        if isinstance(bytea_data, memoryview): 
            bytea_data = bytea_data.tobytes()
                
        pixmap = QPixmap()
        pixmap.loadFromData(bytea_data)
        return pixmap
    
    return QPixmap()
