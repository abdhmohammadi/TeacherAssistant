#import pypandoc
#import pymupdf

from PySide6.QtCore import QMarginsF
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

from PySide6.QtGui import ( QPageLayout, QPageSize)

from PySide6.QtWidgets import ( QWidget,QPushButton,QVBoxLayout,QMainWindow, QTabWidget)
           
from PySideAbdhUI.Notify import PopupNotifier

class PdfGeneratorApp(QMainWindow):
    
    def __init__(self, parent=None, html_source='', answer_html=''):
        
        super().__init__(parent)
        self.setWindowTitle("HTML to PDF Generator")
        self.setGeometry(100, 100, 900, 600)

        central = QWidget()
        central.setProperty('class', 'window-background-layer')
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # ---- Quiz Tab ----
        tab1 = QWidget()
        layout1 = QVBoxLayout()
        self.preview_source = QWebEngineView()
        self.preview_source.setHtml(html_source)
        layout1.addWidget(self.preview_source)

        self.generate_button = QPushButton("Generate PDF")
        self.generate_button.clicked.connect(self.generate_pdf)
        layout1.addWidget(self.generate_button)
        tab1.setLayout(layout1)
        self.tabs.addTab(tab1, "Quiz")

        # ---- Answers Tab (conditionally) ----
        if answer_html:                     # Pythonic check for non-empty, non-None
            tab2 = QWidget()
            layout2 = QVBoxLayout()
            self.preview_answer = QWebEngineView()
            self.preview_answer.setHtml(answer_html)
            layout2.addWidget(self.preview_answer)
            tab2.setLayout(layout2)
            self.tabs.addTab(tab2, "Answers")


    def generate_pdf(self):
        # Create a QWebEnginePage for PDF generation
        page = QWebEnginePage()
        # Load the HTML content into the page
        html = self.html_source + '<br>' + self.html_answer
        page.setHtml(html)
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
                    #stream.write(self.html_source)
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
