# MyJobAssistant/utils/helpers.py
import os
import sys
import webbrowser
import subprocess
from PySide6.QtWidgets import QApplication
import re
from PySide6.QtGui import QPixmap

from processing.utils import image_tools
#from processing.utils import image_tools
#from utils import image_tools
# A4 paper is part of the ISO 216 standard, which defines paper sizes based on a consistent aspect ratio.
# The height of an A4 sheet is calculated as: Height = Width × 2^0.5


def get_application_dir():
    # Check if the application is frozen (packaged)
    if getattr(sys, 'frozen', False):
        # Use the directory of the executable when packaged
        return QApplication.applicationDirPath()
    else:
        # Use the directory of the script when running in development
        return os.path.dirname(os.path.abspath(sys.argv[0]))
def compile_latex(tex_path:str, compile='pdflatex'):

        # Run pdflatex and parse output
        process = subprocess.Popen([compile, tex_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Print output in real-time
        print("Compiling LaTeX document...")
        for line in process.stdout:
            print(line, end="")

        # Wait for the process to finish
        process.wait()

        # Check the result
        if process.returncode == 0:
            print("\nCompilation successful!")
        else:
            print("\nCompilation failed!")
            print(process.stderr.read())


def run_latex(source:str, compile='xelatex',output_pdf_name:str='output.pdf'):

        # Install TeX Live (with XeLaTeX support)
        # Install Persian Fonts (e.g., "XB Zar")
        # In texlive 2023 and later copy disired fonts to :
        # C:\texlive\2023\texmf-dist\fonts\truetype
        # Use xelatex for Compilation
        #   When compiling the LaTeX document, always use xelatex instead of pdflatex,
        #   because xepersian only works with XeTeX.
        # --------------------------------------------------------------------
        # 📌 Summary of Required Packages
        # --------------------------------------------------------------------
        # Component	                Description
        # --------------------------------------------------------------------
        # TeX Live / MacTeX	        Provides XeLaTeX and LaTeX packages
        # texlive-xetex	            Adds XeLaTeX support
        # texlive-lang-arabic	    Required for xepersian package
        # texlive-fonts-extra	    Ensures extra fonts for XeLaTeX
        # Persian Fonts (XB Zar)	Required for proper Persian text rendering
        # --------------------------------------------------------------------

        # --------------------------------------------------------------------
        # Step 1: generating pdf from latex
        # --------------------------------------------------------------------
        
        # directory to cash
        curdir = os.curdir
        appdata_dir = os.getenv('LOCALAPPDATA')
        app_dir = os.path.join(appdata_dir, 'MyJobAssistant')
        
        # Create the directory if it doesn't exist
        os.makedirs(app_dir, exist_ok=True)
        os.chdir(app_dir)

        pdf_path = os.path.join(app_dir, 'TeX-Source.tex')
        # writes latex content
        with open(pdf_path, "w", encoding="utf-8") as f: f.write(source)

        # Compiling tex document:
        # We want to show real-time output from pdflatex (e.g., warnings, errors, or status messages).
        # we can use subprocess and print the output line by line.
        
        compile_latex(pdf_path,compile=compile)
        # Below line is very simple to use, but we can not control real-time output
        # os.system(f"{compile} {pdf_path}")

        pdf_path = os.path.join(app_dir, output_pdf_name)
        
        print(f"PDF generated: {pdf_path}")

        # --------------------------------------------------------------------
        # Step 2: converting pdf to image
        # --------------------------------------------------------------------
        png_path = os.path.join(app_dir, 'edu-resource.png')
        
        image_tools.pdf_to_image(pdf_path,png_path)

        print(f"PNG generated: {png_path}")

        # --------------------------------------------------------------------
        # Step 3: croping png
        # --------------------------------------------------------------------
        outpath = image_tools.crop_white_background_margins(png_path, app_dir,
                                edge_threshold=10,tolerance=10,margin_threshold=0.99)
        
        print(f"Crop generated: {outpath}")
        # --------------------------------------------------------------------
        # Step 4: return value: 
        # --------------------------------------------------------------------
        pixmap = QPixmap(outpath)
        # Scale the pixmap for high-DPI
        #pixmap = pixmap.scaled(QSize(self.resource_width,self.resource_height),#* device_pixel_ratio,
        #                       Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        base64_image = image_tools.pixmap_to_base64(pixmap)

        html_content = f"""<img src="data:image/png;base64,{base64_image}"/>"""
        
        os.chdir(curdir)
        curdir = os.curdir
        print(curdir)

        return html_content

def is_latex(text):
    
    # Check if the text contains LaTeX commands.
    
    latex_patterns = [
        r'\\documentclass\{*\}',  # LaTeX document class
        r'\\begin\{document\}.*?\\end\{document\}',  # Start of document
        r'\\section\{',  # Section command
        r'\\[a-zA-Z]+\{',  # Any LaTeX command with curly braces
    ]
    # Use re.DOTALL to allow .*? to match across multiple lines
    return any(re.search(pattern, text, re.DOTALL| re.IGNORECASE) for pattern in latex_patterns)


def is_html(text:str):
    
    # Check if the text contains HTML tags.
    
    html_patterns = [
        r'<html>.*?</html>',  # HTML tag
        r'<head>.*?</head>',  # Head tag
        r'<body>.*?</body>',  # Body tag
        r'<div>',  # Div tag
        r'<p>',  # Paragraph tag
        r'<[a-zA-Z]+>',  # Any HTML tag
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in html_patterns)

# Check if the text is plain text (no formatting, HTML tags, or LaTeX commands).
def is_rtf(text:str): 
    
    pattern = r'<meta\s+[^>]*name\s*=\s*["\']qrichtext["\'][^>]*(?:/?>|</meta>)'
    # Find all matches in the string
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

    html = is_html(text)
    ltx = is_latex(text)
    # If the text is not LaTeX or HTML format, or if it is HTML and contains <meta name"qrichtext" ../> 
    # we say it is raw data
    return not (ltx or html) or (html and len(matches)>0)


def is_pdf(text:str): 
    pattern = r'<meta\s+[^>]*name\s*=\s*["\']pdf["\'][^>]*(?:/?>|</meta>)'
    # Find all matches in the string
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

    return not is_latex(text) and (is_html(text) and len(matches)>0)

def open_file_os(file_path):
    # Open file using os module - most portable way
    try:
        # Windows
        if sys.platform.startswith('win'):
            os.startfile(file_path)
        # macOS
        elif sys.platform.startswith('darwin'):
            subprocess.run(['open', file_path])
        # Linux
        else:
            subprocess.run(['xdg-open', file_path])
        return True
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return False

def open_pdf_webbrowser(pdf_path):
    """Open PDF using webbrowser module"""
    try:
        webbrowser.open(pdf_path)
        return True
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return False

def open_pdf_platform_specific(pdf_path):
    """Open PDF using platform-specific commands"""
    try:
        if sys.platform.startswith('win'):
            # Windows using shell command
            subprocess.run(['cmd', '/c', 'start', '', pdf_path], shell=True)
        elif sys.platform.startswith('darwin'):
            # macOS
            subprocess.run(['open', pdf_path])
        else:
            # Linux systems
            # Try different commands in case some are not installed
            commands = ['xdg-open', 'evince', 'okular', 'acroread']
            for cmd in commands:
                try:
                    subprocess.run([cmd, pdf_path])
                    break
                except FileNotFoundError:
                    continue
        return True
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return False

A4_width_mm = 210
A4_height_mm = 297

class Converters:

    @staticmethod
    def get_A4_size_pixels(): return (Converters.convert_mm_to_pixels(210.0), Converters.convert_mm_to_pixels(297.0))
    
    @staticmethod
    def convert_mm_to_pixels(mm:float):

        # Convert millimeters to inches (1 inch = 25.4 mm)
        inches = mm / 25.4
        # Get the screen's DPI
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()

        # Convert inches to pixels
        return inches * dpi

    @staticmethod
    def inchs_to_pixels(inches:float):
        # Get the screen's DPI
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()

        # Convert inches to pixels
        return inches * dpi

