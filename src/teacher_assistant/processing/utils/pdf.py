#import pypandoc
#import pymupdf

from PySide6.QtCore import QMarginsF
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

from PySide6.QtGui import ( QPageLayout, QPageSize)

from PySide6.QtWidgets import ( QWidget,QPushButton,QVBoxLayout,QMainWindow )
           
from PySideAbdhUI.Notify import PopupNotifier

class PdfGeneratorApp(QMainWindow):

    def __init__(self,parent =None, html_content=''):
        super().__init__(parent)
        self.html_content = html_content
        #self.output_pdf = output_pdf

        # Set up the UI
        self.setWindowTitle("HTML to PDF Generator")
        self.setGeometry(100, 100, 900, 600)

        # Create a central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add a QWebEngineView for preview
        self.preview_view = QWebEngineView()
        
        self.preview_view.setHtml(self.html_content)
        layout.addWidget(self.preview_view)

        # Add a button to generate the PDF
        self.generate_button = QPushButton("Generate PDF")
        self.generate_button.clicked.connect(self.generate_pdf)
        layout.addWidget(self.generate_button)

    def generate_pdf(self):
        # Create a QWebEnginePage for PDF generation
        page = QWebEnginePage()
        # Load the HTML content into the page
        page.setHtml(self.html_content)

        # Wait for the page to load completely before printing
        def print_to_pdf(finished):
            if finished:
                print("HTML content loaded successfully.")
                print(f"Attempting to save PDF file")

                # Set up custom margins and page layout
                # 0.5 inches for edges required
                # Margins in millimeters (left, top, right, bottom)
                margins = QMarginsF(24, 5, 24, 5) 
                page_layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                          QPageLayout.Orientation.Portrait,
                                          margins)

                from PySide6.QtWidgets import QFileDialog
                options = QFileDialog.Options()
                file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDFs (*.pdf);", options=options)
                if file_name:
                    # Save the rendered content to a PDF file with custom layout

                    page.printToPdf(file_name, page_layout)
                    #output_html = os.path.dirname(os.path.abspath(file_name)) + '\\Edu.html'
                    #stream = open(output_html, encoding="utf-8",mode='w')
                    #stream.write(self.html_content)
                    #stream.close()
                    #print("PDF saved successfully.")
                    #helpers.open_file_os(file_name)

                    PopupNotifier.Notify(self,'PDF','PDF saved successfully.\n'+file_name)

                # Quit the application after generating the PDF
                #QTimer.singleShot(1000, QApplication.instance().quit)
            else:
                print("Error: HTML content failed to load.")

        # Connect the loadFinished signal to print_to_pdf
        page.loadFinished.connect(print_to_pdf)
