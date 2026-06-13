import re
from PySide6.QtCore import QSize
from PySide6.QtGui import (QFont, QFontDatabase, Qt, QIcon, QTextCursor)

from PySide6.QtWidgets import (QComboBox, QFileDialog, QFontComboBox, QTabWidget, QTextEdit, 
                               QVBoxLayout, QWidget, QLabel,QApplication, QMessageBox,
                               QPushButton, QHBoxLayout, QLineEdit, QMenu)

                
from PySideAbdhUI.Notify import PopupNotifier
from PySideAbdhUI.Widgets import SearchBox
from PySideAbdhUI.Documents.document_editor import RichTextEditor
from processing.Imaging.Tools import pixmap_to_base64
from processing.Imaging.SnippingTool import SnippingWindow
from utils.editor_helper import extract_editor_parts

from core.app_context import app_context

class EducationalResourceEditor(QWidget):

    # Managed with QGridLayout
    # Grid divided into 5x6 (rows x columns)
    
    def __init__(self):

        super().__init__()
        
        self.id = 0
        main_layout = QVBoxLayout(self)
        self.setContentsMargins(10,0,10,10)
        main_layout.addLayout(self.create_header_panel())

        
        self.doc_editor = RichTextEditor()
        self.answer_input = RichTextEditor()
        
        

        widget = self.create_content_commands()
        
        main_layout.addWidget(widget)

        self.setup_tabwidgets(main_layout)

        self.metadata_input = QTextEdit(self)
        
        self.metadata_input.setPlaceholderText("Additional Details")
        self.metadata_input.setMaximumHeight(150)
        self.metadata_input.setAcceptRichText(True)  # Enable rich text support
        self.metadata_input.setToolTip('Add description about question, analytical notes and etc.')
        main_layout.addWidget(self.metadata_input)

        footer = QHBoxLayout()
        main_layout.addLayout(footer)
        
        footer.addWidget(QLabel('Score:'))
        self.score_input = QLineEdit('1')
        self.score_input.setFixedWidth(50)
        self.score_input.setToolTip('The maximum score for current question.')
        footer.addWidget(self.score_input)

        footer.addStretch(1)

        btn = QPushButton('  DELETE')
        btn.setIcon(QIcon(':icons/trash-2.svg'))
        btn.setToolTip('Removes the current record form database.')
        btn.clicked.connect(self.remove_record)
        footer.addWidget(btn)
        
        save_button = QPushButton('  SAVE')
        save_button.setIcon(QIcon(':icons/database.svg'))
        save_button.setToolTip('Saves the current record in the database.')
        save_button.clicked.connect(self.save_to_database)
        footer.addWidget(save_button)

        
    def setup_tabwidgets(self, layout:QVBoxLayout):

        # -- Create tab widget --
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # -- Tab 1 --
        # 10 + 10 margins of tow edges and 15 pixel for scroll bar = 35 pixels
        #self.doc_editor.setFixedWidth(app_context.EDU_ITEM_PIXELS + 35)
        # 10 + 10 margins of tow edges and 15 pixel for scroll bar = 35 pixels
        #self.answer_input.setFixedWidth(app_context.EDU_ITEM_PIXELS + 35)  
        self.tabs.addTab(self.doc_editor, "Question")
        
        # -- Tab 2 --        
        self.tabs.addTab(self.answer_input, "Answer")

        self.tabs.setCurrentIndex(0)
        w = QWidget()
        
        clayout = QHBoxLayout(w)
        clayout.setContentsMargins(0,0,0,10)
        
        clayout.addWidget(QLabel('Source:'))
        self.source_input = QLineEdit()
        self.source_input.setFixedSize(QSize(400, 32))
        self.source_input.setPlaceholderText("Source")
        self.source_input.setToolTip('Specifies the source textbook or concept for current question.')
        clayout.addWidget(self.source_input)
        search_input = SearchBox()
        search_input.setToolTip('Find Id in the database ...')
        search_input.setPlaceholderText('Find Id ...')
        search_input.textEdited.connect(lambda _, sender= search_input: self.load_from_database(sender))
        clayout.addWidget(search_input)
        

        self.tabs.setCornerWidget(w,Qt.Corner.TopRightCorner)


    def create_header_panel(self):
        
        layout = QHBoxLayout()
        
        page_title = QLabel('RESOURCE EDITOR')
        page_title.setProperty('class','heading2')
        layout.addWidget(page_title)
        layout.addStretch(1)

        #layout.setColumnStretch(3,1)
        back_button = QPushButton() 
        # Back Navigation
        back_button.setText('')
        back_button.setIcon(QIcon(':icons/chevron-left.svg'))
        back_button.setProperty('class','grouped_mini')
        back_button.setToolTip(app_context.ToolTips['Back'])
        back_button.clicked.connect(lambda _, direction='<':self.load_record(direction))

        layout.addWidget(back_button)#,0,4,1,1,Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignBottom)
        
        self.Id_label = QLabel()
        self.Id_label.setProperty('class','caption')
        layout.addWidget(self.Id_label)#, 0,2,1,2,Qt.AlignmentFlag.AlignBottom)
        
        next_button = QPushButton()

        next_button.setText('')
        next_button.setIcon(QIcon(':icons/chevron-right.svg'))
        next_button.setProperty('class','grouped_mini')
        next_button.setToolTip(app_context.ToolTips['Next'])
        next_button.clicked.connect(lambda _ , direction='>':self.load_record(direction))
        
        layout.addWidget(next_button)
        
        return layout


    def insertMathDialog(self): self.tabs.currentWidget().insertMathDialog()
    def insertImageFile(self): self.tabs.currentWidget().insertImage()
    def insertTableDialog(self): self.tabs.currentWidget().insertTableDialog()
    def applyTextStyle(self, command=''): self.tabs.currentWidget().applyTextStyle(command)
    def chooseTextColor(self): self.tabs.currentWidget().chooseTextColor()
    def chooseBackgroundColor(self): self.tabs.currentWidget().chooseBackgroundColor()
    def setAlignment(self, command='left'): self.tabs.currentWidget().setAlignment(command)
    def setParagraphDirection(self, rtl=False): self.tabs.currentWidget().setParagraphDirection(rtl)
    def setFontFamily(self,fontFamily): self.tabs.currentWidget().setFontFamily(fontFamily)
    def setFontSize(self,size:int=12): self.tabs.currentWidget().setFontSize(size)
    def setPageSize(self,page_size_name): self.tabs.currentWidget().setPageSize(page_size_name)
    def showMarginDialog(self): self.tabs.currentWidget().showMarginDialog()
    
    def saveFile(self, file_type): self.tabs.currentWidget().saveFile(file_type)
    def exportAsImage(self): self.tabs.currentWidget().extractAsImages()
    def OpenFileDialog(self): self.tabs.currentWidget().LoadFileDialog('Open File','', dialog_type='open')
    def SaveFileDialog(self): self.tabs.currentWidget().LoadFileDialog('Save File','', dialog_type='save')

    def loadTextFile(self, auto_render=False): self.tabs.currentWidget().loadTextFile(auto_render)
    def loadHtmlFile(self): self.tabs.currentWidget().loadHtmlFile()
    def openDocx (self): self.tabs.currentWidget().loadDocxFile()
    def openPdf(self): self.tabs.currentWidget().loadPdfFile()
    
    def zoom(self,zm='in'):
        if zm == 'in':
            self.tabs.currentWidget().zoomIn()
        elif zm== 'out':
            self.tabs.currentWidget().zoomOut()
        elif zm== 'fit':
            self.tabs.currentWidget().fitPage()
        
    def zoom_percent(self,arg:str):
        
        if not arg.strip('%').isdigit(): return

        self.tabs.currentWidget().setZoomPercent(int(arg.strip('%')))

    def create_content_commands(self):

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,3,0)
        layout.setSpacing(2)

        # INSERT MENU(Clean content and upload files as new content)
        button = QPushButton('')
        button.setProperty('class','mini')
        button.setIcon(QIcon(':icons/file-text.svg'))
        button.setToolTip('Working with files')

        menu = QMenu(button)

        menu.addAction('New', self.clear_content,'CTRL+N')
        menu.addAction('Open Package', self.on_open_package)
        menu.addAction('Open File', self.OpenFileDialog)
        menu.addSeparator()
        #menu.addAction('PDF(Editable)',self.loadPDF)      # Planed
        #menu.addAction('LaTeX',lambda: self.loadLaTeX)    # Planed
        
        menu.addAction('Save Package', self.on_save_package)
        menu.addAction("Save File", self.SaveFileDialog)
        menu.addAction("Extract as Images", self.exportAsImage)
        
        button.setMenu(menu)
        
        layout.addWidget(button)

        btn_math = QPushButton('')
        btn_math.setProperty('class','mini')
        btn_math.setIcon(QIcon(':icons/sigma.svg'))
        btn_math.setToolTip('Insert math formula')
        btn_math.clicked.connect(self.insertMathDialog)

        layout.addWidget(btn_math)

        btn_table = QPushButton('')
        btn_table.setProperty('class','mini')
        btn_table.setIcon(QIcon(':icons/sheet.svg'))
        btn_table.setToolTip('Insert table')
        btn_table.clicked.connect(self.insertTableDialog)

        layout.addWidget(btn_table)

        btn_Text = QPushButton('')
        btn_Text.setProperty('class','mini')
        btn_Text.setIcon(QIcon(':icons/pencil.svg'))
        btn_Text.setToolTip('Text font styles')

        layout.addWidget(btn_Text)

        menu_text = QMenu(self)

        btn_Text.setMenu(menu_text)
        for name, slot in [
            ("Bold", lambda : self.applyTextStyle('Bold')), 
            ("Italic", lambda: self.applyTextStyle('Italic')),# or editor.setItalic(italic: bool)
            ("Underline", lambda: self.applyTextStyle('Underline')),
            ("Strike", lambda: self.applyTextStyle('Strike')),
            ('Text Color', self.chooseTextColor),
            ('Highlight',self.chooseBackgroundColor)
        ]:
            menu_text.addAction(name, slot)

        menu_text.addSeparator()

        lalign_btn = QPushButton("")
        lalign_btn.setProperty('class','mini')
        lalign_btn.setToolTip('Left alignment')
        lalign_btn.setIcon(QIcon(':icons/left-to-right.svg'))
        lalign_btn.clicked.connect(lambda: self.setAlignment('left'))
        layout.addWidget(lalign_btn)

        calign_btn = QPushButton("")
        calign_btn.setProperty('class','mini')
        calign_btn.setToolTip('Center alignment')
        calign_btn.setIcon(QIcon(':icons/center-align.svg'))
        calign_btn.clicked.connect(lambda: self.setAlignment('center'))
        layout.addWidget(calign_btn)

        ralign_btn = QPushButton("")
        ralign_btn.setProperty('class','mini')
        ralign_btn.setToolTip('Right alignment')
        ralign_btn.setIcon(QIcon(':icons/right-to-left.svg'))
        ralign_btn.clicked.connect(lambda: self.setAlignment('right'))
        layout.addWidget(ralign_btn)

        justify_btn = QPushButton("")
        justify_btn.setProperty('class','mini')
        justify_btn.setToolTip('Justify')
        justify_btn.setIcon(QIcon(':icons/justify.svg'))
        justify_btn.clicked.connect(lambda: self.setAlignment('justify'))
        layout.addWidget(justify_btn)

        ltr_btn = QPushButton('')
        ltr_btn.setProperty('class','mini')
        ltr_btn.setToolTip('Left to Right direction')
        ltr_btn.setIcon(QIcon(':icons/pilcrow-right.svg'))
        ltr_btn.clicked.connect(lambda: self.setParagraphDirection(False))
        layout.addWidget(ltr_btn)
        
        rtl_btn = QPushButton('')
        rtl_btn.setProperty('class','mini')
        rtl_btn.setToolTip('Right to Left direction')
        rtl_btn.setIcon(QIcon(':icons/pilcrow-left.svg'))
        rtl_btn.clicked.connect(lambda: self.setParagraphDirection(True))
        layout.addWidget(rtl_btn)

        # LaTeX
        #btn_latex = QPushButton('')
        #btn_latex.setProperty('class','mini')
        #btn_latex.setIcon(QIcon(':icons/TeX.svg'))
        #btn_latex.setToolTip(app_context.ToolTips['Generate LaTeX'])

        #menu_latex = QMenu(self)
        #btn_latex.setMenu(menu_latex)
        #menu_latex.addAction('New LaTeX script', lambda sender=self.doc_editor: self.___config_latex(sender))
        #menu_latex.addAction('Run LaTeX', lambda sender= self.doc_editor: self.run_latex(sender))
                 
        #layout.addWidget(btn_latex)

        # HTML
        #btn_html = QPushButton('')
        #btn_html.setProperty('class','mini')
        #btn_html.setIcon(QIcon(':icons/html-code.svg'))
        #btn_html.setToolTip(app_context.ToolTips['Generate HTML'])
        #menu_html = QMenu(self)
        #btn_html.setMenu(menu_html)
        #menu_html.addAction('New HTML Script',lambda sender=self.doc_editor: self.___config_basic_html(sender))
        #menu_html.addAction('Run HTML',lambda _, sender=self.doc_editor: self.run_html(sender))
        
        #btn_html.setDisabled(True)
        #layout.addWidget(btn_html)
        
        # INSERT BUTTON(Upload Image and insert into current content)
        add_img_button = QPushButton('')
        add_img_button.setProperty('class','mini')
        add_img_button.setIcon(QIcon(':icons/image-plus.svg'))
        add_img_button.setToolTip(app_context.ToolTips['Insert Image'])
        add_img_button.clicked.connect(self.insertImageFile) 
        layout.addWidget(add_img_button)

        # Add Snipping tools button
        snip_button = QPushButton("")
        snip_button.setProperty('class','mini')
        snip_button.setIcon(QIcon(':icons/square-bottom-dashed-scissors.svg'))
        snip_button.setToolTip(app_context.ToolTips['Insert Image from screen'])
        #snip_button.clicked.connect(lambda _, t = self.doc_editor :self.run_snipping_tool(t))
        layout.addWidget(snip_button)

        btn = QPushButton('')
        btn.setProperty('class','mini')
        btn.setIcon(QIcon(':icons/square-dashed.svg'))
        btn.setToolTip('Paper margins')
        btn.clicked.connect(self.showMarginDialog)
        layout.addWidget(btn)

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
                                    self.metadata_input.moveCursor(QTextCursor.MoveOperation.Start),
                                    self.metadata_input.insertPlainText('[MARKED]\n' ),
                                    self.metadata_input.moveCursor(QTextCursor.MoveOperation.Up),
                                    self.metadata_input.setFocus(Qt.FocusReason.MouseFocusReason)
                                        ))
        
        btn_mark.setIcon(QIcon(':icons/bookmark.svg'))
        layout.addWidget(btn_mark)

        btn = QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('Zoom in, zoom out and fit page')
        btn.setIcon(QIcon(':icons/zoom-in.svg'))
        btn.clicked.connect(self.showMarginDialog)

        menu = QMenu(btn)
        btn.setMenu(menu)

        menu.addAction('Zoom In',lambda: self.zoom('in'))
        menu.addAction('Zoom Out',lambda: self.zoom('out'))
        menu.addAction('Fit page',lambda: self.zoom('fit'))

        layout.addWidget(btn)
        
        zoom_edit = QLineEdit('100%')
        zoom_edit.setFixedWidth(50)
        zoom_edit.setToolTip('Zoom')
        zoom_edit.textEdited.connect(self.zoom_percent)
        
        layout.addWidget(zoom_edit)

        font_size_edit = QLineEdit('12')
        font_size_edit.setFixedWidth(34)
        font_size_edit.setToolTip('Font size')
        font_size_edit.textChanged.connect(self.setFontSize)
        layout.addWidget(font_size_edit)

        fontCombo = QFontComboBox()
        fontCombo.setFixedWidth(100)
        fontCombo.setFontFilters(QFontComboBox.FontFilter.AllFonts)
        fontCombo.setWritingSystem(QFontDatabase.WritingSystem.Any)  # or QFontDatabase.Any
        fontCombo.setCurrentFont(QFont("Arial",12))  # default font
        fontCombo.setToolTip('System installed fonts')
        fontCombo.currentFontChanged.connect(lambda f: self.setFontFamily(f.family()))
        layout.addWidget(fontCombo)
        
        pageCombo = QComboBox()
        pageCombo.addItems(["A4", "Letter", "B5", "Edu-Item"])
        pageCombo.setCurrentText('A4')
        pageCombo.setFixedWidth(80)
        pageCombo.setToolTip('Paper size')
        pageCombo.currentTextChanged.connect(self.setPageSize)
        layout.addWidget(pageCombo)
        
        layout.addStretch(1)
        
        widget = QWidget()
        #widget.setFixedWidth(app_context.EDU_ITEM_PIXELS + 35)
        widget.setLayout(layout)

        return widget
    
    def on_save_package(self):
        
        full_html =  self.doc_editor.getFullHtmlAsync()
        styles , content = extract_editor_parts(full_html)

        block = f'<BLOCK>\n{styles}\n{content}</BLOCK>'

        filepath, _ = QFileDialog.getSaveFileName(None, 'Save Package', '','Text(*.txt)')

        with open(filepath, mode='w',encoding='utf-8') as f: f.write(block)

    def on_open_package(self):
        
        if self.notify_unsaved_content(): return
        
        filepath, _ = QFileDialog.getOpenFileName(None, 'Open package','','Text(*.txt)')
        
        if not filepath: return
        
        with open(filepath, mode='r',encoding='utf-8') as f:  block = f.read()
        
        block = block.replace('<BLOCK>','')
        block = block.replace('</BLOCK>','')

        # Extract all style blocks from imported HTML.
        styles = re.findall( r"<style[^>]*>.*?</style>", block, flags=re.I | re.S)
        styles = ''.join(styles)
        # Remove style blocks from body.
        # They will be reinserted later after synchronization.
        content = re.sub(r"<style[^>]*>.*?</style>", "", block, flags=re.I | re.S)

        self.doc_editor.copy_content(content, styles)
 
    def notify_unsaved_content(self):
        
        if self.doc_editor.isModified():
            PopupNotifier.Notify(self, 'Warning','unsaved data detected. to ignore click "DISCARD" and retry!',
                                 ok_slot= self.doc_editor.setClean)
            return True
        return False
    
    def clear_content(self):

        if self.notify_unsaved_content(): return
        
        self.id = 0
        self.Id_label.setText('(New item)')
        self.source_input.clear()
        self.score_input.setText('0.0')
        self.doc_editor.clearContent()
        self.answer_input.clearContent()
        self.metadata_input.clear()

     
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

            app_context.database.execute(query)
            msg = f'The record {self.id} removed from database.'
            self.clear_content()

        except Exception as e:
            msg = f'Database error: {e}.'
        
        PopupNotifier.Notify(self,"Message", msg)

    def load_record(self, direction:str=' >'):
        
        """ Fetch the one record based on <b>direction</b>.<br>
            if <b>direction</b> is <b>></b> is fetched next to current record,<br>
            if <b>direction</b> is <b><</b> is fetched previou to current record,<br>
            and if <b>direction</b> is <b>EMPTY STRING,</b> is fetched first record bigger than zero Id.<br>
        """
        if self.tabs.currentWidget().isModified():
            PopupNotifier.Notify(self, 'Warning','unsaved data detected. to ignore click "DISCARD"',
                                 ok_slot= self.doc_editor.setClean)
            return
        try:
            order = 'ORDER BY Id DESC' if direction == '<' else ' ORDER BY Id ASC'
            where =  f'WHERE Id {direction} {self.id} {order} LIMIT 1;' if not direction == '' else f'WHERE Id>0 {order} LIMIT 1;'

            # Fetch the data from the database
            query  = f"SELECT Id, source_, score_, content_, answer_, metadata_ FROM educational_resources {where}"
            
            row = app_context.database.fetchone(query)
            if row:            
                self.clear_content()

                self.id = int(row[0])
                self.source_input.setText(row[1])
                self.score_input.setText(str(row[2]))
                # row[3] is a block of question/learning material
                block = row[3]
                block = block.replace('<BLOCK>','')
                block = block.replace('</BLOCK>','')

                # Extract all style blocks from imported HTML.
                styles = re.findall( r"<style[^>]*>.*?</style>", block, flags=re.I | re.S)
                styles = ''.join(styles)

                # Remove style blocks from body.
                # They will be reinserted later after synchronization.
                block = re.sub(r"<style[^>]*>.*?</style>", "", block, flags=re.I | re.S)

                block = block.replace("<CONTENT>","")
                block = block.replace("</CONTENT>","")
                
                self.doc_editor.copy_content(block, styles)

                self.answer_input.setText(row[4])
                self.metadata_input.setText(row[5])
                
                self.Id_label.setText('Content editing | ' + str(self.id))

            #self.doc_editor.minimumSizeHint()
            
        except Exception() as e:
            PopupNotifier.Notify(self,"Message", f"Error: {e}.")

    def load_from_database(self,sender:QLineEdit):
        
        # Id of the record in the database
        id  = sender.text() 
        id  = 0 if id == '' else int(id)
        
        if self.id and id == int(self.id) :return
        
        self.id = id
        self.load_record('=')
    ###################################################################################################
    ##############  WARNING: this comment is not valid, it has to updated | 2026-05-27 ################
    ###################################################################################################
     # We save the all data as text, but to manage advanced datatypes of text like rich texts with image, 
    # table or formulas we need advanced control on our data, becuase of this to simple managment, we save:
    # Plaintext and RTF as HTML format, Also we write LaTeX and HTML code in the editor directly, these type
    # of text are saved directly and without any conversion. to resore PlainText and RTF, will useing setHtml()
    # method of QEditText widget, and  for Html and LaTeX types will use setPlainText() method.
    # deference between RTF and HTML format in our contents is: we use HTML format with managing HTML tags, and
    # the text without HTML tags, but containing text formating is RTF. also the RTF text without formated
    # content, is mean PlainText.
    ####################################################################################################
    def save_to_database(self):
        
        # Edu-Item source book
        source = self.source_input.text()
        # score to evaluate
        score = self.score_input.text()

        score = float(score) if score !='' and score.replace('.','').isnumeric() else '1'
        
        # Get the entire content of QTextEdit
        source_html = self.doc_editor.getFullHtmlAsync()
        styles , content = extract_editor_parts(source_html)

        # remove id if exist and return <style> ... </style>
        styles =  re.sub(r'[^>]*<style[^>]*>', "<style>", styles, flags=re.I | re.S)
        # clean if styles are empty.
        if styles.replace('\n','').replace(' ','') == '<style></style>' : styles = "<style></style>"
        
        content = f'<BLOCK>\n{styles}\n<CONTENT>\n{content}\n</CONTENT>\n</BLOCK>'

        answer = self.answer_input.getHtmlContentSync()

        details = self.metadata_input.toPlainText()
        
        try:

            query ="INSERT INTO educational_resources "\
                   "(source_, score_, content_, answer_, metadata_)"\
                   "VALUES (%s, %s, %s, %s, %s) RETURNING id;"
                
            variables = (source, score, content, answer, details)

            msg = 'inserted'
               
            if self.id and self.id>0:
                query = "UPDATE educational_resources SET source_ = %s, score_= %s, content_= %s,"\
                        "answer_= %s, metadata_= %s WHERE Id= %s RETURNING id;"

                variables = (source, score, content, answer, details, self.id)
                                
                msg = 'updated'
                
            # execute the query and return id
            self.id = app_context.database.execute_and_return(query, variables)[0]
            
            self.Id_label.setText(f'{str(self.id)} | Content recently {msg}.')

            msg = f'Data {msg} successfully.'

        except Exception() as e:

            msg = f'Database error: {e}.'

        PopupNotifier.Notify(self,"Message", msg)
