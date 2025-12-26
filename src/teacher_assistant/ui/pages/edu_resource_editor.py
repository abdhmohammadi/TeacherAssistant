import os
#import pypandoc
import pymupdf

from PySide6.QtGui import (Qt, QIcon,QPixmap, QColor, QTextCharFormat, QTextDocument, QTextCursor)

from PySide6.QtWidgets import (QFileDialog, QTextEdit, QGridLayout, QWidget, QLabel,QApplication, QMessageBox,
                               QPushButton, QHBoxLayout, QLineEdit, QMenu,QWidgetAction)

                
from PySideAbdhUI.Notify import PopupNotifier


from processing.Imaging.Tools import pixmap_to_base64
from processing.Imaging.SnippingTool import SnippingWindow
from utils import helpers
from processing.utils.image_tools import pdf_to_base64
from ui.widgets.widgets import RichTextEdit
from core.app_context import app_context

"""
# EduationalResourceEditor.py
# ###################################################################################################
#                                 EDUCATION RESOURCE EDITOR                                         #
# ################################################################################################### 
# This is an Editor for education resources like questions and other learning units, here           #
# we able to manage education resources as Plain Text, RTF, image, PDF, html and LaTeX.             #
# main technology to manage these contents is HTML script, However two usage of Html concept        # 
# is applyed here, first, as an editor to write learning unit, this type is pure usage of html      #
# script to create a learning unit, but it does not support the math formulas. second usage         #
# is to save and restore other datatypes in the database.                                           #
# We save all of other types in html format indexed by tag of 'meta' and name = 'qrichtext'         #
# (the 'meta' is a tag of html). this usage is more integrated with QTextEdit object and            #
# QTextDocument. Each script indexed by meta name='viewport' is raw script and is shown to user     #
# as pure Html script and other scripts indexted by mata name ='qrichtext' is shown as processed    #
# text, These scripts is ready to publish. However, it is possible to edit and it can be edited     #
# as normal text(without direct use of HTML or LaTeX codes).                                        #
# Supported text datatypes is listed as follow:                                                     #
#                                                                                                   #
# Plain Text: is directy written in QTextEdit and is converted to html by toHtml() method at        #
#             save time and when is read from database is loaded to the QTextEdit by calling        #
#             setHtml(...) method. this method does not support formated texts  and other           #
#             special scripts as math formola and image. it is proper to simple resources.          #
#                                                                                                   #
# Rich Text : Rich Text is a document that is saved by .rtf file extension, like Plain Text         #
#             is written directly in QTextEdit an is saved using toHtml() and is restored by        #
#             setHtml(...) method. it supports formatted texts, image contents and tables.          #
#             Also it able to support other more advanced properies against Plain Text.             #
#                                                                                                   #
# LaTeX     : The LaTeX script is written and saved as plain text. in saveing method of this        #
#             content is not used any conversion. It is saved by calling toPlainText() method.      #
#             Also at read time from database will been used setPlainText(...). this is row data,   #
#             befor using it must be processed by a LaTeX engine like PDFlatex, xelatex and etc.    #                                                                              #
#             The LaTeX raw script is recognized  at reading time by 'regular expresion processing' #
#             techniques over \\documentclass{...}, \\begin{document}... \\end{document} and other     #
#             keywords of LaTeX script.                                                             #
#                                                                                                   #
# Html      : is very similar to LaTeX, we use this script to write Html code directly. LaTex       #
#             and Html data are raw and must be processed befor useing. to process the Html code    #
#             it is enugh we reset content with setHtml(...). at first step we access to the        #
#             Html script of QTextEdit by toPlainText(), next we reset using setHtml(...).          #
#                                                                                                   #
# Image     : Image conent is converted to base64 string at load time and is updated by setting to  #
#             html tag <img src="data:image/png;base64,{base64_image}"/> then uses setHtml(...)     #
#             method to upload in QTextEdit document. after this step, at save and read time it is  #
#             considered as an Html content.                                                        #
#                                                                                                   #
# PDF       : In this code we supose the PDF contents has One page, we don't need more page to use  #
#             as a learning resource. if the loaded content has been more pages we use first page   #
#             and other pages is skipped. If we don't need to manipulation, PDF content can load as #
#             image. becuase of editing porpose, we can load as html raw string. all actions on the #
#             PDF content after load is like image and html.                                        #
#                                                                                                   #
# docx      : This file type currently is not fully supported. but It can load as  html using       #
#             'pypandoc' package. currently word documents that loaded by this method loses many    #
#             formating properties. however the docx files is loaded as html.                       #
#                                                                                                   #
# All of data is saved using HTML format with width = 6.19 inches, this value is avilable space for #
# edu-content in the A4 paper, because there are 0.5 inches space for left and right margin and 0.54#
# inches is used for columns 1 and 3 in the our 3-columns paper. Below is output table.             #
#                                                                                                   #
# │     ┌──────┬─────────────────────────────────────────────────────────────────────┬──────┐     │ #
# │ 0.5 │POINT │                              HEADER                                 │  ROW │ 0.5 │ #
# │     ├──────┼─────────────────────────────────────────────────────────────────────┼──────┤     │ #
# │     │ 0.54 │                       CONTENT - 6.19 INCHES                         │ 0.54 │     │ #
# │     ├──────┼─────────────────────────────────────────────────────────────────────┼──────┤     │ #
# │     │      │                               CONTENT                               │      │     │ #
# │     │      │                                                                     │      │     │ #
# │     │──────┼─────────────────────────────────────────────────────────────────────┼──────┤     │ #
# │     │  SUM │                               FOOTER                                │      │     │ #
# │     └──────┴─────────────────────────────────────────────────────────────────────┴──────┘     │ #
#                                                                                                   #
# The 6.19 inches must be converted to pixels. this coversion is done by DPI(dots per inches), final#
# pixels is equal to 6.19xDPI. to keep quality of images durng conversion, using of 'width=6.19dpi' #
# property of HTML script is good choise against other methods.                                     #
# For editable porpose the content is not saved as final version, It is save as raw data. In case   #
# of LaTeX script if a content be ready to use or publish, it had been provided by a command 'RUN-  #
# TEX' this command needs a latex engine to process. After processing it is saved as byte64 image   #
# in the html body or tag of <img ... width='6.19xDPI'/>.                                           #
#                                                                                                   #
#####################################################################################################
"""

class EducationalResourceEditor(QWidget):

    # Managed with QGridLayout
    # Grid divided into 5x6 (rows x columns)
    
    def __init__(self, cursor=None):

        super().__init__()
        self.db_cursor = cursor
        self.id = 0
        main_layout = QGridLayout(self)
        self.setContentsMargins(10,0,10,25)

        page_title = QLabel('RESOURCE EDITOR')
        page_title.setProperty('class','heading2')

        main_layout.addWidget(page_title,0,0,1,1,Qt.AlignmentFlag.AlignTop)
        
        self.content_description_input = RichTextEdit()        

        # 10 + 10 margins of tow edges and 15 pixel for scroll bar = 35 pixels
        self.content_description_input.setFixedWidth(app_context.EDU_ITEM_PIXELS + 35)

        self.content_description_input.setPlaceholderText("Content")
        self.content_description_input.setAcceptRichText(True)  # Enable rich text support
        main_layout.addWidget(self.content_description_input,2,0)
        
        self.answer_input = QTextEdit(self)
        # 10 + 10 margins of tow edges and 15 pixel for scroll bar = 35 pixels
        self.answer_input.setFixedWidth(app_context.EDU_ITEM_PIXELS + 35)  
        self.answer_input.setPlaceholderText("Answer")
        self.answer_input.setAcceptRichText(True)  # Enable rich text support
        main_layout.addWidget(self.answer_input,4,0)

        
        self.create_right_panel(main_layout)
        
        widget = self.create_content_commands()
        main_layout.addWidget(widget,1,0)
        widget = self.create_answer_commands()
        main_layout.addWidget(widget,3,0)


        btn = QPushButton('  DELETE')
        btn.setIcon(QIcon(':icons/trash-2.svg'))

        btn.setToolTip('Removes the current record form database')
        btn.clicked.connect(self.remove_record)
        main_layout.addWidget(btn,3,3,1,1,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop)
        
        save_button = QPushButton('  SAVE')
        save_button.setIcon(QIcon(':icons/database.svg'))
        save_button.clicked.connect(self.save_to_database)
        main_layout.addWidget(save_button,3,4,1,1,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop)


    def create_right_panel(self,layout:QGridLayout):

        self.Id_label = QLabel()
        self.Id_label.setProperty('class','caption')
        layout.addWidget(self.Id_label, 0,2,1,2,Qt.AlignmentFlag.AlignBottom)
        layout.setColumnStretch(3,1)
        back_button = QPushButton() 
        # Back Navigation
        back_button.setText('')
        back_button.setIcon(QIcon(':icons/chevron-left.svg'))
        back_button.setProperty('class','grouped_mini')
        back_button.setToolTip(app_context.ToolTips['Back'])
        back_button.clicked.connect(lambda _, direction='<':self.load_record(direction))

        layout.addWidget(back_button,0,4,1,1,Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignBottom)
        next_button = QPushButton()

        next_button.setText('')
        next_button.setIcon(QIcon(':icons/chevron-right.svg'))
        next_button.setProperty('class','grouped_mini')
        next_button.setToolTip(app_context.ToolTips['Next'])
        next_button.clicked.connect(lambda _ , direction='>':self.load_record(direction))
        
        layout.addWidget(next_button,0,4,1,1,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignBottom)

        layout.addWidget(QLabel('Source:'),1,1)
        
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Source")
        layout.addWidget(self.source_input,1,2,1,3)
        

        self.additional_details_input = QTextEdit(self)
        
        self.additional_details_input.setPlaceholderText("Additional Details")
        self.additional_details_input.setAcceptRichText(True)  # Enable rich text support
        layout.addWidget(self.additional_details_input,2,1,1,4)

        layout.addWidget(QLabel('Score'),3,1)
        self.score_input = QLineEdit('1')
        self.score_input.setFixedWidth(100)
        layout.addWidget(self.score_input,3,2)


    def create_content_commands(self):

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,3,0)
        layout.setSpacing(2)

        layout.addWidget(QLabel('Content'))
        layout.addStretch(1)
        
        # LaTeX
        btn_latex = QPushButton('')
        btn_latex.setProperty('class','mini')
        btn_latex.setIcon(QIcon(':icons/TeX.svg'))
        btn_latex.setToolTip(app_context.ToolTips['Generate LaTeX'])

        menu_latex = QMenu(self)
        btn_latex.setMenu(menu_latex)
        menu_latex.addAction('New LaTeX script', lambda sender=self.content_description_input: self.___config_latex(sender))
        menu_latex.addAction('Run LaTeX', lambda sender= self.content_description_input: self.run_latex(sender))
                 
        layout.addWidget(btn_latex)

        # HTML
        btn_html = QPushButton('')
        btn_html.setProperty('class','mini')
        btn_html.setIcon(QIcon(':icons/html-code.svg'))
        btn_html.setToolTip(app_context.ToolTips['Generate HTML'])
        menu_html = QMenu(self)
        btn_html.setMenu(menu_html)
        menu_html.addAction('New HTML Script',lambda sender=self.content_description_input: self.___config_basic_html(sender))
        menu_html.addAction('Run HTML',lambda _, sender=self.content_description_input: self.run_html(sender))
        
        layout.addWidget(btn_html)
        
        # INSERT BUTTON(Upload Image and insert into current content)
        add_img_button = QPushButton('')
        add_img_button.setProperty('class','mini')
        add_img_button.setIcon(QIcon(':icons/image-plus.svg'))
        add_img_button.setToolTip(app_context.ToolTips['Insert Image'])
        add_img_button.clicked.connect(lambda _, sender= self.content_description_input, arg=app_context.SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg, options='+'))
        
        layout.addWidget(add_img_button)

        # Add Snipping tools button
        snip_button = QPushButton("")
        snip_button.setProperty('class','mini')
        snip_button.setIcon(QIcon(':icons/square-bottom-dashed-scissors.svg'))
        snip_button.setToolTip(app_context.ToolTips['Insert Image from screen'])
        snip_button.clicked.connect(lambda _, t = self.content_description_input :self.run_snipping_tool(t))
        layout.addWidget(snip_button)

        ####################################################################################################
        # INSERT MENU(Clean content and upload files as new content)
        button = QPushButton('')
        button.setProperty('class','mini')
        button.setIcon(QIcon(':icons/upload.svg'))
        button.setToolTip(app_context.ToolTips['Upload File'])

        menu = QMenu(button)
        menu.addAction('Plain text',lambda sender= self.content_description_input, arg= app_context.SupportedFileTypes.TEXT: self.upload_file(sender=sender,arg=arg))
        menu.addAction('RTF',lambda sender= self.content_description_input,arg= app_context.SupportedFileTypes.RTF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Image',lambda sender= self.content_description_input, arg=app_context.SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg))
        menu.addAction('PDF(Editable)',lambda sender= self.content_description_input,arg= app_context.SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='Editable'))
        menu.addAction('PDF(Readonly)',lambda sender= self.content_description_input,arg=app_context.SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='ReadOnly'))
        menu.addAction('Word(docx)',lambda sender= self.content_description_input,arg= app_context.SupportedFileTypes.DOCX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('LaTeX',lambda sender= self.content_description_input,arg= app_context.SupportedFileTypes.LaTeX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Html',lambda sender= self.content_description_input,arg=app_context.SupportedFileTypes.HTML: self.upload_file(sender=sender,arg=arg))
        
        button.setMenu(menu)
        
        layout.addWidget(button)
        ####################################################################################################
  
        from_db_btn = QPushButton("")
        from_db_btn.setProperty('class','mini')
        from_db_btn.setIcon(QIcon(':icons/database-search.svg'))
        from_db_btn.setToolTip(app_context.ToolTips['Find in database'])

        # Create a QMenu
        menu = QMenu(self)
        # Create a QWidgetAction to hold custom widgets
        widget_action = QWidgetAction(self)

        # Create a widget to hold the QLineEdit and QPushButton
        widget = QWidget()

        # Set the widget to the QWidgetAction
        widget_action.setDefaultWidget(widget)

        # Add the QWidgetAction to the menu
        menu.addAction(widget_action)

        menu_layout = QHBoxLayout(widget)        
        # Add a QLineEdit
        line_edit = QLineEdit('')
        line_edit.setPlaceholderText("Id of edu resource ...")
        menu_layout.addWidget(line_edit)

        # Add Find Id QPushButton
        inner_button = QPushButton('')
        inner_button.setIcon(QIcon(':icons/search.svg'))
        inner_button.setProperty('class','mini')
        inner_button.clicked.connect(lambda _, sender= line_edit: self.load_from_database(sender))
        menu_layout.addWidget(inner_button)

        # Set the menu to the QPushButton
        from_db_btn.setMenu(menu)

        layout.addWidget(from_db_btn)
        ######################################################################################################


        btn = QPushButton('')
        btn.setProperty('class','mini')
        btn.setIcon(QIcon(':icons/text.svg'))
        btn.setToolTip(app_context.ToolTips['New Content'])
        btn.clicked.connect(self.clear_content)
        layout.addWidget(btn)

        # separator
        layout.addWidget(QLabel('|'))

        btn_mark = QPushButton('')
        btn_mark.setProperty('class','mini')
        btn_mark.setToolTip(app_context.ToolTips['Set bookmark'])
        # Marking an Edu-Item is done in order to revise before distribution.
        # For variety of reasons, it may be necessary to make changes to it
        # or it may be necessary to temporarily prevent its distribution.
        # Keyword [MARKED] in the text emphasizes this point. User can insert
        # some notes after this keyword, The text that has this keyword should
        # not be distributed before it is removed.
        # Notice: application of this mark is in the 'EduResourceViewer' form. 
        btn_mark.clicked.connect(lambda :(
                                    self.additional_details_input.moveCursor(QTextCursor.MoveOperation.Start),
                                    self.additional_details_input.insertPlainText('[MARKED]\n' ),
                                    self.additional_details_input.moveCursor(QTextCursor.MoveOperation.Up),
                                    self.additional_details_input.setFocus(Qt.FocusReason.MouseFocusReason)
                                        ))
        
        btn_mark.setIcon(QIcon(':icons/bookmark.svg'))
        layout.addWidget(btn_mark)


        widget = QWidget()
        widget.setFixedWidth(app_context.EDU_ITEM_PIXELS + 35)
        widget.setLayout(layout)

        return widget
        
    def create_answer_commands(self):

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,3,0)
        layout.setSpacing(2)
        layout.addWidget(QLabel('Answer'))
        layout.addStretch(1)
        # LaTeX
        btn_latex = QPushButton('')
        btn_latex.setProperty('class','mini')
        btn_latex.setIcon(QIcon(':icons/TeX.svg'))
        btn_latex.setToolTip(app_context.ToolTips['Generate LaTeX'])
        menu_latex = QMenu(self)
        btn_latex.setMenu(menu_latex)
        menu_latex.addAction('New LaTeX script', lambda sender=self.answer_input: self.___config_latex(sender))
        menu_latex.addAction('Run LaTeX', lambda sender= self.answer_input: self.run_latex(sender))
                 
        layout.addWidget(btn_latex)

        # HTML
        btn_html = QPushButton('')
        btn_html.setProperty('class','mini')
        btn_html.setIcon(QIcon(':icons/html-code.svg'))
        btn_html.setToolTip(app_context.ToolTips['Generate HTML'])
        menu_html = QMenu(self)
        btn_html.setMenu(menu_html)
        menu_html.addAction('New HTML Script',lambda sender=self.answer_input: self.___config_basic_html(sender))
        menu_html.addAction('Run HTML',lambda _, sender=self.answer_input: self.run_html(sender))
        
        layout.addWidget(btn_html)
        
        # INSERT BUTTON(Upload Image and insert into current content)
        button = QPushButton('')
        button.setProperty('class','mini')
        button.setIcon(QIcon(':icons/image-plus.svg'))
        button.setToolTip(app_context.ToolTips['Insert Image'])
        button.clicked.connect(lambda _, sender= self.answer_input, arg=app_context.SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg, options='+'))
        
        layout.addWidget(button)

        # Add Snipping tools button
        snip_button = QPushButton("")
        snip_button.setProperty('class','mini')
        snip_button.setIcon(QIcon(':icons/square-bottom-dashed-scissors.svg'))
        snip_button.setToolTip(app_context.ToolTips['Insert Image from screen'])
        snip_button.clicked.connect(lambda _, t = self.answer_input:self.run_snipping_tool(t))

        layout.addWidget(snip_button)

        # INSERT MENU(Clean content and upload files as new content)
        button = QPushButton('')
        button.setProperty('class','mini')
        button.setToolTip(app_context.ToolTips['Upload File'])
        button.setIcon(QIcon(':icons/upload.svg'))
        menu = QMenu(button)
        menu.addAction('Plain text',lambda sender= self.answer_input, arg= app_context.SupportedFileTypes.TEXT: self.upload_file(sender=sender,arg=arg))
        menu.addAction('RTF',lambda sender= self.answer_input,arg= app_context.SupportedFileTypes.RTF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Image',lambda sender= self.answer_input, arg=app_context.SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg))
        menu.addAction('PDF(Editable)',lambda sender= self.answer_input,arg= app_context.SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='Editable'))
        menu.addAction('PDF(Readonly)',lambda sender= self.answer_input,arg=app_context.SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='ReadOnly'))
        menu.addAction('Word(docx)',lambda sender= self.answer_input,arg= app_context.SupportedFileTypes.DOCX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('LaTeX',lambda sender= self.answer_input,arg= app_context.SupportedFileTypes.LaTeX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Html',lambda sender= self.answer_input,arg=app_context.SupportedFileTypes.HTML: self.upload_file(sender=sender,arg=arg))
        
        button.setMenu(menu)
        
        layout.addWidget(button)
        widget = QWidget()
        widget.setLayout(layout)

        return widget    

    def ___config_basic_html(self,sender:QTextEdit):
        
        sender.document().clear()
        
        text = '<b>Add here main content.</b>'

        html_template  = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
        html_template += '<html lang="en">\n'
        html_template += '<head> <meta charset="UTF-8" name="viewport" content="width=device-width, initial-scale=1.0"></head>\n'
        html_template += f'<body style="width:{app_context.EDU_ITEM_PIXELS}px;">\n'
        html_template += '   <main>\n'
        html_template += '      ' + text + '\n'
        html_template += '   </main>\n'
        html_template += '</body>\n'
        html_template += '</html>'

        sender.document().setPlainText(html_template)
        
        #self.___highlightText(sender, text)
    

    def ___config_latex(self,sender:QTextEdit):

        #self.___document_type = MyJobAssistant.DocumentType.LaTeX

        sender.document().clear()

        text = '   Add here main content '
        documentclass = 'article'
        package = 'xepersian'
        font='Yas'

        # Generates latex template
        latex_content = ('\\documentclass{{{}}}\n'
                          '\\usepackage{{{}}}\n'
                          '\\settextfont{{{}}}\n'
                          '\\begin{{document}}\n{}\n'
                          '\\end{{document}}'
                         ).format(documentclass, package, font, text)

        sender.document().setPlainText(latex_content)
        
        self.___highlightText(sender, text)  


    def ___highlightText(self,sender:QTextEdit,search_text):
        # The text to search for
        # Get the QTextDocument from the QTextEdit
        document = sender.document()

        # Create a QTextCharFormat to define the highlighting style
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("yellow"))  # Set background color
        highlight_format.setForeground(QColor("red"))     # Set text color (optional)

        # Create a QTextCursor to manipulate the document
        cursor = sender.textCursor()

        # Move the cursor to the beginning of the document
        cursor.movePosition(QTextCursor.Start)

        # Loop to find and highlight all occurrences of the text
        while True:
            # Search for the text using QTextDocument's find method
            cursor = document.find(search_text, cursor, QTextDocument.FindFlag.FindCaseSensitively)
            if cursor.isNull():
                break  # Exit the loop if no more occurrences are found

            # Apply the highlighting format to the found text
            cursor.mergeCharFormat(highlight_format)


    def clear_content(self):

        self.id=0
        self.Id_label.setText('(New item)')
        self.source_input.clear()
        self.score_input.clear()
        self.content_description_input.document().clear()
        self.answer_input.document().clear()
        self.additional_details_input.clear()


    def upload_PDF_as_html(self, PDF_path, sender:QTextEdit):

        try:

            # Open the PDF file using PyMuPDF
            PDF_document = pymupdf.open(PDF_path)

            # Iterate through each page in the PDF
            for page in PDF_document:
                # Load the page
                html = page.get_text('html')
                #html = '<html><br><head><br><meta name="PDF" charset="utf-8"/><br></head><br>'
                #html += f'<body style="width:{MyJobAssistant.EDU_CONTENT_WIDTH*DPI}px"><br>{html}<br></body><br></html>'
                # Set the HTML content in the QTextEdit
                sender.setHtml(html)
                
                sender.insertPlainText("\n\n")  # Add a newline after each page

        except Exception() as e:
            print(f"Error processing PDF: {e}")


    def upload_file(self,sender:QTextEdit, arg:str=app_context.SupportedFileTypes.IMAGE, options=None):
        
        # Open a file dialog to upload an image or PDF.
        file_dialog = QFileDialog(self)
        filter = app_context.FileTypes[arg]

        file_dialog.setNameFilter(filter)
        
        if file_dialog.exec():
        
            file_path = file_dialog.selectedFiles()[0]

            # avilable widh for edu-content is 6.19 inches
            if arg == app_context.SupportedFileTypes.IMAGE: 

                pixmap = QPixmap(file_path)
                
                base64_image = pixmap_to_base64(pixmap)

                html_content = f'<img src="data:image/png;base64,{base64_image}" width="{app_context.EDU_ITEM_PIXELS}"/>'
                # Set the HTML content in the QTextEdit
                if options == '+': 
                    sender.insertHtml(html_content)
                else: 
                    sender.document().clear()
                    sender.setHtml(html_content)

            elif arg == app_context.SupportedFileTypes.PDF:
                sender.document().clear()
                if options == 'Editable':
                    self.upload_PDF_as_html(file_path, sender)
                else:

                    base64s = pdf_to_base64(file_path)
                    html_content = f'<img src="data:image/png;base64,{base64s[0]}" width="{app_context.EDU_ITEM_PIXELS}"/>'
                    
                    # Set the HTML content in the QTextEdit
                    sender.setHtml(html_content)


            elif arg in [app_context.SupportedFileTypes.TEXT,
                         app_context.SupportedFileTypes.RTF,
                         app_context.SupportedFileTypes.LaTeX,
                         app_context.SupportedFileTypes.PDF,
                         app_context.SupportedFileTypes.HTML]:
                sender.document().clear()
                self.read_plain_text(sender, file_path)


            #elif arg == app_context.SupportedFileTypes.DOCX:
            #    # Loses text formatting
            #    sender.document().clear()
            #    html = pypandoc.convert_file(file_path,'html',extra_args=['--embed-resources'])
            #    sender.document().setHtml(html)


    # we read Plain text, but save in HTML format as RTF data
    def read_plain_text(self,sender:QTextEdit, file_path):
        
        file_name, extension = os.path.splitext(file_path)
        
        data = ''        

        if extension == '.txt':

            with open(file_path, 'r') as file: data = file.read()
            sender.document().setHtml(data)

        elif extension in ['.tex','.html']:

            with open(file_path, 'r', encoding='utf-8') as file: data = file.read()
            sender.document().setPlainText(data)
        
        #elif extension == '.rtf':
            # Prerequisits of using pypandoc:
            # 1) Install Pandoc using windows installer
            # 2) set path to environment variable
            #   1) Press WINDOWS LOGO + R
            #   2) run sysdm.cpl
            #   3) go to  advanced tab
            #   4) click Enviorenment Variables ...
            #   5) go to system variables section
            #   6) scroll to and select 'Path' item
            #   7) click Edit\ click New and add 'C:\Program Files\pandoc-3.6.3\'
            #   8) save changes
            # 2) install pypandoc using pip install pypandoc
            # import pypandoc

            #html = pypandoc.convert_file(file_path, "html")
        
            #sender.document().setHtml(html)
    

    def run_html(self, sender:QTextEdit):

        html = sender.document().toPlainText()

        sender.document().clear()

        sender.document().setHtml(html)
    

    def run_latex(self,sender:QTextEdit):

        html = helpers.run_latex(sender.toPlainText(), compile='xepersian', output_PDF_name= 'edu-resource.PDF')
        # Set the HTML content in the QTextEdit
        sender.clear()
        sender.insertHtml(html)
        
        
    def run_snipping_tool(self,target:QTextEdit):

        active = QApplication.activeWindow()
        active.hide()
        snipping_window = SnippingWindow(self)
        snipping_window.screen_captured.connect(lambda data:
            (
            target.insertHtml(f'<img src="data:image/png;base64,{pixmap_to_base64(data)}" width="{app_context.EDU_ITEM_PIXELS}"/>'),
            active.show()
            ))

        snipping_window.screen_capture_canceled.connect(active.show)

        snipping_window.showFullScreen()  # Ensure full coverage
        snipping_window.activateWindow()
        snipping_window.raise_()

    def remove_record(self):

        b = QMessageBox.warning(self,'WARNING',f'Current record with id "{self.id}" will be removed.\n' + 
                            'After removing is not retrived. Are you sure?',
                            QMessageBox.StandardButton.Yes,QMessageBox.StandardButton.Cancel)
        
        if b == QMessageBox.StandardButton.Cancel: return

        query  = f"DELETE FROM educational_resources WHERE id={self.id};" 
        
        try:

            self.db_cursor.execute(query)
            msg = f'The record {self.id} removed from database.'
            self.clear_content()

        except Exception as e:
            msg = f'Database error: {e}.'
        
        PopupNotifier.Notify(self,"Message", msg, 'bottom-right', delay=3000, background_color='#353030',border_color="#2E7D32")

    def load_record(self, direction:str=' >'):
        
        try:
            order = 'ORDER BY Id DESC' if direction == '<' else ' ORDER BY Id ASC'
            where =  f'WHERE Id {direction} {self.id} {order} LIMIT 1;' if not direction == '' else f'WHERE Id>0 {order} LIMIT 1;'

            # Fetch the data from the database
            query  = "SELECT Id, source_, score_, content_description_, additional_details_, answer_ FROM educational_resources " + where
            
            row = app_context.database.fetchone(query)
            
            msg = f"No content found in the database for Id {direction} {self.id}."

            if row:

                self.clear_content()

                self.id = int(row[0])
                self.source_input.setText(row[1])
                self.score_input.setText(str(row[2]))
                if not helpers.is_rtf(row[3]):
                
                    # this used to HTML and LaTeX source files(pure LaTeX or HTML data)
                    self.content_description_input.document().setPlainText(row[3])

                else:                     
                
                    # This is used to RTF or txt to display in the QTextEdit properly
                    self.content_description_input.document().setHtml(row[3])
                
                self.additional_details_input.setText(row[4])

                if helpers.is_rtf(row[4]):
                    self.answer_input.document().setHtml(row[5])
                else:
                    self.answer_input.document().setPlainText(row[5])

                msg = "Content loaded from database."
                
                self.Id_label.setText('Content editing | ' + str(self.id))

                self.content_description_input.minimumSizeHint()
            
        except Exception() as e:
            
            msg = f"Database error: {e}."
            print(msg)

        PopupNotifier.Notify(self,"Message", msg, 'bottom-right')

    def load_from_database(self,sender:QLineEdit):
        
        id  = sender.text()
        id  = 0 if id == '' else int(id)
        
        if id == int(self.id) :return
        
        self.id = id
        self.load_record('=')

    # We save the all data as text, but to manage advanced datatypes of text like rich texts with image, 
    # table or formulas we need advanced control on our data, becuase of this to simple managment, we save:
    # Plaintext and RTF as HTML format, Also we write LaTeX and HTML code in the editor directly, these type
    # of text are saved directly and without any conversion. to resore PlainText and RTF, will useing setHtml()
    # method of QEditText widget, and  for Html and LaTeX types will use setPlainText() method.
    # deference between RTF and HTML format in our contents is: we use HTML format with managing HTML tags, and
    # the text without HTML tags, but containing text formating is RTF. also the RTF text without formated
    # content, is mean PlainText.
    def save_to_database(self):
        
        # Edu-Item source book
        source = self.source_input.text()
        # score to evaluate
        score = self.score_input.text()

        score = float(score) if score !='' and score.replace('.','').isnumeric() else '1'
        
        # Get the entire content of QTextEdit
        content = self.content_description_input.document().toPlainText()

        if helpers.is_rtf(content): content = self.content_description_input.toHtml()

        answer = self.answer_input.document().toPlainText()

        if helpers.is_rtf(answer): answer = self.answer_input.document().toHtml()

        details = self.additional_details_input.toPlainText()
        
        try:

            query ="INSERT INTO educational_resources "\
                   "(source_, score_, content_description_, answer_, additional_details_)"\
                   "VALUES (%s, %s, %s, %s, %s) RETURNING id;"
                
            variables = (source, score, content, answer, details)

            msg = 'inserted'
               
            if self.id>0:
                query = "UPDATE educational_resources SET source_ = %s, score_= %s, content_description_= %s,"\
                        "answer_= %s, additional_details_= %s WHERE Id= %s RETURNING id;"

                variables = (source, score, content, answer, details, self.id)    # Save the HTML content to the database
                                
                msg = 'updated'
            
            self.db_cursor.execute(query, variables)
                
            self.id = self.db_cursor.fetchone()[0]
            
            self.Id_label.setText(f'{str(self.id)} | Content recently {msg}.')

            msg = f'Data {msg} successfully.'

        except Exception() as e:

            msg = f'Database error: {e}.'

        PopupNotifier.Notify(self,"Message", msg)
