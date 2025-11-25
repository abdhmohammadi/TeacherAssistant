
from io import BytesIO
from PySide6.QtGui import QPixmap,QImage,QPainter, QIcon
from PySide6.QtCore import QBuffer,QByteArray
import base64
from PIL import Image
from scipy.ndimage import sobel
import pymupdf
import os
import numpy as np
import json
from PySide6.QtSvg import QSvgRenderer

def create_icon_from_svg(svg_string:str, width=64, height=64): return QIcon(create_svg_pixmap(svg_string, width=64, height=64))

def load_icons_from_json(file_path)->dict:
    """Load icon data from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            
            return dict(json.load(f))
    
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON: {e}")
        return {}

  
def create_svg_pixmap(svg_data: str, width=64, height=64) -> QPixmap:
    """Convert SVG string data to a QPixmap of given size."""
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)  # Transparent background

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    return QPixmap.fromImage(image)


    # Function to convert QPixmap to binary data

def convert_qpixmap_to_binary(qpixmap):
        qimage = qpixmap.toImage()
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        qimage.save(buffer, "PNG")
        binary_data = buffer.data().data()
        return binary_data

"""

def bytea_to_pixmap(bytea_data):
        try:
            if bytea_data:
                if isinstance(bytea_data, memoryview):
                    bytea_data = bytea_data.tobytes()
                
                pixmap = QPixmap()
                pixmap.loadFromData(bytea_data)
                return pixmap
            
        except Exception as e:
            print(f"Image loading error: {e}")
        return QPixmap()


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
"""
def pdf_to_base64(pdf_path):
    from PIL import Image  # Pillow for saving images

    # Open the PDF file
    pdf_document = pymupdf.open(pdf_path)
    pages = []
    # Iterate through each page
    for page_number in range(len(pdf_document)):
        # Get the page
        page = pdf_document.load_page(page_number)
    
        # Set the zoom factor for high quality (e.g., 4x)
        zoom = 4  # Higher zoom means higher resolution
        mat = pymupdf.Matrix(zoom, zoom)
    
        # Render the page to an image (pixmap)
        pix = page.get_pixmap(matrix=mat)
    
        # Convert the pixmap to a PIL Image
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        pages.append(base64.b64encode(buffered.getvalue()).decode("utf-8"))
    
    return pages

def pdf_to_image(pdf_path):

    images =[]
    try:
        # Open the PDF file using PyMuPDF
        pdf_document = pymupdf.open(pdf_path)

        # Iterate through each page in the PDF
        for page_num in range(len(pdf_document)):
                # Load the page
                page = pdf_document.load_page(page_num)

                # Render the page to a pixmap
                pix = page.get_pixmap(matrix=pymupdf.Matrix(3, 3)) # High resolution
                # Save the QPixmap with best quality (PNG is lossless)
                #images.append(pix)
                pix.save("output_image.png", "PNG")
                # Convert the Pixmap to a QImage
                image_format = QImage.Format.Format_RGB888 if pix.alpha == 0 else QImage.Format.Format_RGBA8888
                img = Image.fromqpixmap(pix)
                qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, image_format)
                
                # Convert QImage to QPixmap
                pixmap = QPixmap.fromImage(qimage)
                images.append(pixmap)

    except Exception as e:
            print(f"Error processing PDF: {e}")
    return images


# ccrop image with white background
def crop_white_background_margins(input_image_path, output_directory,
                       keep_top=0, keep_right=0, keep_bottom=0, keep_left=0,
                       edge_threshold=10, tolerance=30, margin_threshold=0.99):
    
    """
    Crop white margins from an image using a hybrid approach.
    
    Args:
        image_path (str): Path to the input image.
        output_path (str): Path to save the cropped image.
        edge_threshold (int): Threshold for detecting edges. Default is 10.
        tolerance (int): Tolerance for near-white pixels (0-255). Default is 30.
        margin_threshold (float): Threshold for considering a row/column as a margin (0-1). Default is 0.99.
    """
    # Open the image
    image = Image.open(input_image_path)
    
    # Convert the image to grayscale for edge detection
    grayscale_image = image.convert('L')
    
    # Convert the grayscale image to a NumPy array
    img_array = np.array(grayscale_image)
    
    # Compute the Sobel edge detection for horizontal and vertical edges
    edges_x = sobel(img_array, axis=0)  # Horizontal edges
    edges_y = sobel(img_array, axis=1)  # Vertical edges
    
    # Combine the edges
    edges = np.sqrt(edges_x**2 + edges_y**2)
    
    # Normalize the edges to 0-255
    edges = (edges / edges.max() * 255).astype(np.uint8)
    
    # Find the top margin using edge detection
    top = 0
    for y in range(edges.shape[0]):
        if np.any(edges[y, :] > edge_threshold):
            break
        top = y + 1
    top -= keep_top
    # Find the left margin using edge detection
    left = 0
    for x in range(edges.shape[1]):
        if np.any(edges[:, x] > edge_threshold):
            break
        left = x + 1
    
    left-=keep_left

    # Find the right margin using edge detection
    right = edges.shape[1]
    for x in range(edges.shape[1] - 1, -1, -1):
        if np.any(edges[:, x] > edge_threshold):
            break
        right = x
    right+=keep_right
    # Convert the original image to RGB for pixel-based bottom margin detection
    rgb_image = image.convert('RGB')
    rgb_array = np.array(rgb_image)
    
    # Function to check if a row is mostly white
    def is_white_row(row, tolerance, threshold):
        white_pixels = np.all(np.abs(row - 255) <= tolerance, axis=-1)
        white_percentage = np.mean(white_pixels)
        return white_percentage >= threshold
    
    # Find the bottom margin using pixel-based detection
    bottom = rgb_array.shape[0]
    for y in range(rgb_array.shape[0] - 1, -1, -1):
        if not is_white_row(rgb_array[y, :, :], tolerance, margin_threshold):
            break
        bottom = y
    
    bottom+=keep_bottom

    
    # Crop the image using the calculated margins
    if top < bottom and left < right:
    
        file_extension = os.path.splitext(input_image_path)[1]
        output_path = os.path.join(output_directory,'cropped-output'+ file_extension)
        cropped_image = image.crop((left, top, right, bottom))
        cropped_image.save(output_path)

        return output_path



def detect_background_color(image):
    """
    Detect the background color by analyzing the corners of the image.
    
    Args:
        image (PIL.Image): The input image.
    
    Returns:
        tuple: The background color as an RGB tuple.
    """
    # Get the pixel values from the corners of the image
    corners = [
        image.getpixel((0, 0)),  # Top-left corner
        image.getpixel((0, image.height - 1)),  # Bottom-left corner
        image.getpixel((image.width - 1, 0)),  # Top-right corner
        image.getpixel((image.width - 1, image.height - 1))  # Bottom-right corner
    ]
    
    # Find the most common color in the corners (assumed to be the background color)
    background_color = max(set(corners), key=corners.count)
    return background_color


def crop_colored_background_margins(input_image_path, output_directory, tolerance=30, margin_threshold=0.99,
                                    keep_top=0, keep_right=0, keep_bottom=0, keep_left=0):
    """
    Crop margins from an image based on the detected background color.
    
    Args:
        image_path (str): Path to the input image.
        output_path (str): Path to save the cropped image.
        tolerance (int): Tolerance for color matching. Default is 30.
        margin_threshold (float): Threshold for considering a row/column as a margin (0-1). Default is 0.99.
    """
    # Open the image
    image = Image.open(input_image_path)
    
    # Convert the image to RGB if it's not already
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Detect the background color
    background_color = detect_background_color(image)
    
    # Convert the image to a NumPy array for easier processing
    img_array = np.array(image)
    
    # Get the width and height of the image
    height, width, _ = img_array.shape
    
    # Function to check if a row or column is mostly background
    def is_margin(slice, background_color, tolerance, threshold):
        # Calculate the percentage of pixels that match the background color
        background_pixels = np.all(np.abs(slice - background_color) <= tolerance, axis=-1)
        background_percentage = np.mean(background_pixels)
        return background_percentage >= threshold
    
    # Find the top margin
    top = 0
    for y in range(height):
        if not is_margin(img_array[y, :, :], background_color, tolerance, margin_threshold):
            break
        top = y + 1
    
    top -= keep_top

    # Find the bottom margin
    bottom = height
    for y in range(height - 1, -1, -1):
        if not is_margin(img_array[y, :, :], background_color, tolerance, margin_threshold):
            break
        bottom = y
    
    bottom += keep_bottom

    # Find the left margin
    left = 0
    for x in range(width):
        if not is_margin(img_array[:, x, :], background_color, tolerance, margin_threshold):
            break
        left = x + 1
    left -=keep_left

    # Find the right margin
    right = width
    for x in range(width - 1, -1, -1):
        if not is_margin(img_array[:, x, :], background_color, tolerance, margin_threshold):
            break
        right = x
    
    right += keep_right

    # Crop the image using the calculated margins
    if top < bottom and left < right:
        file_extension = os.path.splitext(input_image_path)[1]
        output_path = os.path.join(output_directory,'cropped-output'+ file_extension)
        
        cropped_image = image.crop((left, top, right, bottom))
        
        cropped_image.save(output_path)

        print(f"Cropped image saved to {output_path}")
    else:
        print("No white margins to crop.")




#crop_white_margins
#crop_colored_background_margins('C:/Users/AbdhM/AppData/Local/MyJobAssistant/edu-resource.png',
#                                'C:/Users/AbdhM/AppData/Local/MyJobAssistant/',
#                                tolerance=200,margin_threshold=0.50)
#crop_white_margins
#print(crop_white_background_margins('C:/Users/AbdhM/AppData/Local/MyJobAssistant/edu-resource.png',
#                                'C:/Users/AbdhM/AppData/Local/MyJobAssistant/',
#                                edge_threshold=10,tolerance=10,margin_threshold=0.99))