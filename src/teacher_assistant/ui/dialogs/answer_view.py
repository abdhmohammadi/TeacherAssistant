
import base64
import re
from PySide6.QtCore import QMarginsF, Qt, QThread, Signal,QObject
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

from PySide6.QtGui import ( QIcon, QPageLayout, QPageSize)

from PySide6.QtWidgets import ( QDialog, QFileDialog, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, 
                               QMessageBox, QLabel,QStackedWidget, QTextEdit, QWidget,
                               QPushButton,QVBoxLayout, QTabWidget)

from PySideAbdhUI.Documents.document_viewer import DocumentViewer
from PySideAbdhUI.Notify import PopupNotifier
from processing.text import text_processing
from core.app_context import app_context
from utils.editor_helper import unwrap_page_divs, unpack_block

from dateutil.parser import parse

def is_valid_timestamp(s: str) -> bool:
    try:
        parse(s)
        return True
    except (ValueError, OverflowError):
        return False
    
class AnswerView(QDialog):
    
    def __init__(self, data, parent=None):
        super().__init__(parent)
        # data dictionary keys:
        #
        #   student': To display on the output report
        #     qb_ids: To fetch quiz content from question bank
        #    quiz-id: To fetch and update answer data in the quests table
        # asign-date: To display on the output report
        # reply-date: To display on output report and modify. 
        #
        self.data = data
        self.need_update = False
        self.setWindowTitle("")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        self.setFixedHeight(650)
        #central = QWidget()
        #central.setProperty('class', 'window-background-layer')
        #self.setCentralWidget(central)
        layout = QVBoxLayout(self)

        # ---- Loading overlay (stacked on top of content) ----
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)

        # Page 0: the actual tabbed content
        self.tab_widget = QWidget()
        self.setup_tabs()
        self.content_stack.addWidget(self.tab_widget)

        # Page 1: a simple loading indicator
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_label = QLabel("Loading... Please wait.")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(loading_label)
        self.content_stack.addWidget(loading_widget)
        self.content_stack.setCurrentIndex(1)   # show loading first

        # ---- Start the background worker ----
        self.start_worker()

    def set_need_to_update(self): self.need_update = True

    def setup_tabs(self):

        # Create the tab structure (Quiz + optional Answers).
        layout = QVBoxLayout(self.tab_widget)
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(app_context.A4_PIXELS + 100)
        layout.addWidget(self.tabs)

        # Quiz tab
        self.preview_source = DocumentViewer()
        self.tabs.addTab(self.preview_source, "Quiz")
        
        # Answer tab
        answer_widget = QWidget()
        self.answer_layout = QVBoxLayout(answer_widget)

        self.answer_table = QListWidget()
        self.answer_layout.addWidget(self.answer_table)
    
        self.tabs.addTab(answer_widget, "Answers")

        action_widget = QWidget()
        action_widget.setFixedHeight(40)
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0,0,0,5)
        action_layout.addStretch(1)

        action_layout.addWidget(QLabel('Reply date:'))
        self.reply_date_edit = QLineEdit(self.data['reply-date'])
        self.reply_date_edit.textEdited.connect(self.set_need_to_update)
        action_layout.addWidget(self.reply_date_edit)

        add_btn = QPushButton('New answer')
        add_btn.clicked.connect(self._on_add_new_answer)
        action_layout.addWidget(add_btn)

        save_btn = QPushButton('Save')
        save_btn.clicked.connect(self._on_save_answer)
        action_layout.addWidget(save_btn)

        #self.generate_button = QPushButton("Generate PDF")
        #self.generate_button.clicked.connect(self.generate_pdf)
        #self.generate_button.setEnabled(False)

        #action_layout.addWidget(self.generate_button)

        close_btn = QPushButton('Close')
        
        close_btn.clicked.connect(self.__accept)
        
        action_layout.addWidget(close_btn)
        
        self.tabs.setCornerWidget(action_widget,Qt.Corner.TopRightCorner)

    def __accept(self):
        
        if not self.need_update:
            return super().accept()
        else:
            b = QMessageBox.warning(self,'','There is unsaved data. do you want to discard changes?', 
                                    QMessageBox.StandardButton.Discard |
                                    QMessageBox.StandardButton.No)
            
            if b == QMessageBox.StandardButton.Discard:
                return super().reject()
            
    def _on_add_new_answer(self):
        
        html_content = self.open_file()
        data = {'answer': html_content, 'score':'0.0'}

        self.create_answer_item(data)

        self.set_need_to_update()

        self.answer_table.scrollToBottom()

    def start_worker(self):
        """Create the worker and connect its signals."""
        self.worker = HtmlGeneratorWorker(self.data)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_data_received)
        self.worker.error.connect(self.on_worker_error)

        # Cleanup
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)

        self.thread.start()

    def on_thread_finished(self):
        del self.thread
        PopupNotifier.Notify(self, message='Operation done!')

    def on_data_received(self, quiz, answer_blocks:list):
           
        # Save HTML for later PDF generation
        #self.quiz_html = quiz_html
        html, total_score = quiz
        # Replace dimension placeholders
        dimensions = {
            #  is palceholder,     is actual value
            '-- 2.43 inches --': f'{2.43*app_context.DPI}px',
            '-- 2.42 Inches --': f'{2.42*app_context.DPI}px',
            '-- 0.54 Inches --': f'{0.54*app_context.DPI}px',
            '-- 6.19 Inches --': f'{app_context.EDU_ITEM_PIXELS}px',
        }
        
        # Adjust the table size:
        for placeholder, value in dimensions.items(): html = html.replace(placeholder, value)

        # Replace content placeholders
        replacements = {
            '-- In the name of God --': "",#self.config[language]['InTheNameOfGod'], # In the formal exam template
            '-- Stu-Name --':self.data["student"],#self.stu_info_input.text(), # In the both templates
            '-- Stu-Id --': "",#self.stu_id_input.text(), # In the formal exam template
            '-- Organisation Info --': "",#self.org_info_input.toPlainText().replace('\n','<br>'),
            '-- Academic-Year-Term --': "",#self.term_input.toPlainText().replace('\n','<br>'),
            '-- Date --': self.data["asign-date"],#self.date_input.text(), # In the both templates
            '-- Teacher-Name --': "",#self.teacher_input.text(),
            '-- Clock --': "",#self.clock_input.text(),
            '-- Book-Grade --':"",# self.book_grade_input.text(), # In the both templates
            '-- Field --': "",#self.field_input.text(),
            '-- Time-Pages --': "",#self.time_input.text(),
            '-- Index --': "ردیف",#self.config[language]['Row'],# In the both templates
            '-- Edu-Content --': "سوالات",#self.config[language]['Header'],
            '-- Point --': "نمره",#self.config[language]['Score'], # In the both templates
            '-- Author: Abdh --': "",#self.author_input.text(),
            '-- SUM --': str(total_score),#str(total_score),
            '-- FOOTER SUM --': "",#self.config[language]['Footer sum'],
        }
        
        for placeholder, value in replacements.items(): html = html.replace(placeholder, value)
        
        # dir = "rtl" is default, user can change it.
        main_table = f'<div class="page" contenteditable="false" dir="rtl">{html}</div>'
        self.preview_source.clearContent()
           
        self.preview_source.copy_content(content=main_table, custom_styles="",editable= False)

        ################# ANSWER SECTION ########################################################     
        # If there are answers, create the answers tab and load them
        #if len(answer_blocks)>0:

        # Last index of answer blocks contains feedback data.
        for i, item in enumerate(answer_blocks[:-1]): self.create_answer_item(item)

        self.answer_layout.addWidget(QLabel('Feedback:'))
        self.feedback_text = QTextEdit()
        self.feedback_text.setMaximumHeight(100)
        self.feedback_text.setText(answer_blocks[len(answer_blocks)-1]['feedback'])
        self.feedback_text.textChanged.connect(self.set_need_to_update)
        self.answer_layout.addWidget(self.feedback_text)
        
        self.answer_layout.setStretch(0,3)
        self.answer_layout.setStretch(2,1)
        
        # Switch from loading screen to the actual content
        self.content_stack.setCurrentIndex(0)
        #self.generate_button.setEnabled(True)

    def create_answer_item(self,data):
        # Last index of answer blocks contains feedback data.
            list_item = QListWidgetItem() 
            item_widget = QWidget()
            hlayout = QHBoxLayout(item_widget)
            answer_textEdit = QTextEdit()
            answer_textEdit.setFixedWidth(app_context.A4_PIXELS)
            answer_textEdit.setHtml(data['answer'])
            answer_textEdit.textChanged.connect(self.set_need_to_update)
            hlayout.addWidget(answer_textEdit)
            
            vlayout =QVBoxLayout()
            score_edit = QLineEdit(data['score'])
            score_edit.textChanged.connect(self.set_need_to_update)
            score_edit.setMaximumWidth(36)
            score_edit.setStyleSheet('font-size:10pt; text-align:center; padding:2px')

            b1 = QPushButton('')
            b1.setIcon(QIcon(':icons/combine.svg'))
            b1.setToolTip('Replace current answer with new answer')
            b1.setProperty('class', 'mini')
            b1.clicked.connect(lambda _, textEdit = answer_textEdit: self._on_replace_answer(textEdit))
            
            b2 = QPushButton('')
            b2.setIcon(QIcon(':icons/trash-2.svg'))
            b2.setToolTip('remove current answer')
            b2.setProperty('class', 'mini')
            b2.clicked.connect(lambda _, list_item_ = list_item: self._on_delete_answer(list_item_))
            
            vlayout.addWidget(score_edit)
            vlayout.addWidget(b1)
            vlayout.addWidget(b2)
            
            hlayout.addLayout(vlayout)

            hlayout.setStretch(0,90)
            hlayout.setStretch(1,10)

            # Store references directly on the widget
            item_widget.answer_edit = answer_textEdit
            item_widget.score_edit = score_edit

            list_item.setSizeHint(item_widget.sizeHint())
            
            self.answer_table.addItem(list_item)
            self.answer_table.setItemWidget(list_item,item_widget)
        
    
    def _on_delete_answer(self, item_widget:QListWidgetItem):
        # removes an answer item from UI, this need to update by save button
        button = QMessageBox.warning(self, 'Rimove Item', 'We are about to remove the selected item,\n are you sure?',
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        
        if button == QMessageBox.StandardButton.Cancel: return
        
        row = self.answer_table.row(item_widget)

        self.answer_table.takeItem(row)

        self.set_need_to_update()


    def open_file(self):

        filter = 'Images (*.png *.jpg *.jpeg *.bmp *.gif);;HTML (*.html *.htm);;PDF (*.pdf)'
        filepath, x = QFileDialog.getOpenFileName(self, "Find student's answer", "", filter)
        print('bockmark')
        if not filepath: return
        # file extension
        ext = filepath.split('.')[-1]

        if '*.png *.jpg *.jpeg *.bmp *.gif'.find(ext)>-1:
            with open(filepath, 'rb') as f: b64 = base64.b64encode(f.read()).decode()

            html_content = f'<img src="data:image/png;base64,{b64}" width="{app_context.A4_PIXELS}"/>'

        elif '*.html *.htm'.find(ext)>-1:
            with open(filepath, "r", encoding="utf-8") as f: html_content = f.read()

        return html_content
    
    def _on_replace_answer(self, textEdit:QTextEdit):
        
        html_content = self.open_file()

        textEdit.setHtml(html_content)  

        self.need_update = True

    def on_worker_error(self, error_msg):
        """Show error and close the window if loading fails."""
        QMessageBox.critical(self, "Error", f"Failed to load HTML:\n{error_msg}")
        self.close()
    
    def _on_save_answer(self):

        id =  self.data['quiz-id']
        print(id,self.need_update)
        if id and self.need_update:
            
            score_text = []
            answer_tags = ''
            # process list items to access content data
            for row in range(self.answer_table.count()):

                item = self.answer_table.item(row)
                
                widget = self.answer_table.itemWidget(item)
                
                if widget and hasattr(widget, 'answer_edit') and hasattr(widget, 'score_edit'):
                    # returns inner html of a HTML document,
                    # this is desired answer content
                    answer_tag = text_processing.get_html_body_content(widget.answer_edit.toHtml())
                    
                    answer_tags += f'<div>{answer_tag}</div>\n'

                    score_text.append(widget.score_edit.text().strip())

            
            cmd = 'UPDATE quests SET reply_date_=%s, feedback_=%s, scores_=%s, responses_=%s WHERE id= %s;'
            
            reply_date = self.reply_date_edit.text().strip()
            if not is_valid_timestamp(reply_date):
                PopupNotifier.Notify(self,'',f'{reply_date} is not valid date-time format')
                return

            app_context.database.execute(cmd, (reply_date ,
                                              self.feedback_text.toPlainText().strip(),
                                              "-".join(score_text), answer_tags, self.data['quiz-id']))
            
            PopupNotifier.Notify(self, 'Save Answer','Answer updated.')
    
    def generate_pdf(self):
        
        # Build a combined HTML document from quiz and answer HTML,
        # keeping scripts only in the quiz part, and save as a multi‑page PDF.

        # 1. Remove any <script> blocks from the answer HTML only.
        #    This prevents duplicate declarations and execution‑order issues.
        script_re = re.compile(r'<script\b[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)

        quiz_body = self.quiz_html                    # keep quiz exactly as‑is
        answer_body = script_re.sub('', self.answer_html) if self.answer_html else ''

        # 2. Build the combined HTML – no script manipulation for the quiz.
        combined_html = (
            '<html><head>'
            '<meta charset="utf-8">'
            '<style>@media print { .page-break { page-break-after: always; } }</style>'
            '</head><body>'
            f'<div>{quiz_body}</div>'
        )
        if self.answer_html:
            combined_html += '<div class="page-break"></div>'
            combined_html += f'<div>{answer_body}</div>'

        combined_html += '</body></html>'

        # 3. Create a temporary page for PDF generation
        page = QWebEnginePage()

        def print_to_pdf(finished):
            if not finished:
                QMessageBox.warning(self, "Error", "Failed to load HTML content for PDF.")
                return

            margins = QMarginsF(24, 5, 24, 5)  # left, top, right, bottom in mm
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                margins
            )

            file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)"
            )
            if not file_name:
                return

            page.printToPdf(file_name, layout)

            # Optional notification
            PopupNotifier.Notify(self, 'PDF', f'PDF saved successfully.\n{file_name}')

        # 4. Load the combined HTML and connect the callback
        page.loadFinished.connect(print_to_pdf)
        page.setHtml(combined_html)

class HtmlGeneratorWorker(QObject):
    
    finished = Signal(tuple, list)       # quiz_html, answer_html
    error = Signal(str)               # error message

    def __init__(self, data):
        """
        data        : dict with 'student', 'qb_ids', 'quiz-id', 'asign-date', etc.
        db_config   : dict with PostgreSQL connection parameters 
                      (host, port, dbname, user, password)
        app_context : read-only object with DPI, paths, template config, etc.
        """
        super().__init__()
        self.data = data
        #self.db_config = db_config
        #app_context = app_context

    def run(self):
        #conn = None
        try:
            # 1. Open a dedicated database connection for this thread
            #conn = psycopg2.connect(**self.db_config)
            #cursor =  conn.cursor()
            #cursor = app_context.database.connection.cursor()
            # 2. Generate both HTML pieces
            quiz = self._generate_quiz_html()
            answer_blocks = self._extract_answers()
            
            # 3. Emit success (both strings)
            self.finished.emit(quiz, answer_blocks)

        except Exception as e:
            self.error.emit(str(e))

    def _generate_quiz_html(self):
        
        """Generate quiz HTML using the given database cursor."""
        # List of questions from bank in string format  separated by '-'
        qb_ids:str = self.data['qb_ids']
        
        qb_ids = qb_ids[:-1].replace('-',',')

        #if not isinstance(qb_ids, (list, tuple)):
        #    qb_ids = [qb_ids]

        #placeholders = ','.join(['%s'] * len(qb_ids))
        cmd = f'SELECT content_, score_ FROM educational_resources WHERE id IN ({qb_ids});'

        #cursor.execute(cmd, qb_ids)
        records = app_context.database.fetchall(cmd)

        if not records: return ''

        # Load template
        template_path = app_context.resource_path + '\\templates\\01-Quiz-Template.html'
        
        with open(template_path, encoding='utf-8') as f: html = f.read()

        # Common table rows: question contents
        new_row_tmp =  '        <tr>\n'
        new_row_tmp += f'            <td style="text-align: center; vertical-align:top;width:-- 0.54 Inches --;">{{}}</td>\n'
        new_row_tmp += f'            <td style="border-left:none;border-right:none; width:{app_context.EDU_ITEM_PIXELS};">{{}}</td>\n'
        new_row_tmp += f'            <td style="text-align: center; vertical-align:top;width:-- 0.54 Inches --;">{{}}</td>\n'
        new_row_tmp +=  '        </tr>\n'
        
        #language = app_context.Language
        # Replace content placeholders
        new_content_template = '<!-- NEW CONTENT -->'
        styles = ""
        total_score = 0.0
        row = 0
        # Question blocks ffrom database
        for row, item in enumerate(records):
            total_score += item[1]
            # unpack question blocks
            new_style, new_content = unpack_block(item[0])

            # Removes open/close of style tag.
            new_style = new_style.replace("<style>","")
            new_style = new_style.replace("</style>","")
            # Join all styles
            styles = f"{styles}\n{new_style}"
            # remove all div with class="page" apen/close part
            # and return pure content
            new_content = unwrap_page_divs(new_content)
            # data cleaning
            new_content = new_content.replace("\n","")
            
            # Generate new row for the table, this table is contains list of questions
            # format matching data: row index, content, point
            # this format is selected on template_changed event
            new_row = new_row_tmp.format(row + 1, new_content, item[1])
            new_row = new_row + new_content_template
            # Inject this row to the html body
            html = html.replace(new_content_template, new_row, count=1)
            
            row += 1
            
        # Inject styles to the <head> ...</head>
        html = html.replace('</head>',f'\n{styles}\n</head>')

        return (html, total_score)

    def _extract_answers(self):
        """Generate answer HTML using the given database cursor."""

        quiz_id = self.data['quiz-id']
        
        cmd = f'SELECT responses_, scores_, feedback_ FROM quests WHERE id = {quiz_id};'
        
        record = app_context.database.fetchone(cmd)
        #cursor.execute(cmd)
        #record = cursor.fetchone()
        if not record: return ''
  
        scores = str(record[1]).split('-')
 
        # Pattern explanation:
        # <div\b   – literal "<div" followed by a word boundary (ensures it's a tag, not part of a word)
        # [^>]*    – any characters except ">" (attributes, spaces, quotes)
        # >        – closing bracket of the opening tag
        # .*?      – any characters (non‑greedy), including newlines (re.DOTALL makes '.' match '\n')
        # </div>   – literal closing tag
        pattern = r'<div\b[^>]*>.*?</div>'

        # re.DOTALL allows the dot to match newline characters as well
        div_blocks = re.findall(pattern, str(record[0]), re.DOTALL)
        result = []
        
        for i,block in enumerate(div_blocks):

            result.append({'answer': block, 'score':scores[i]})

        result.append({'feedback':record[2] if record[2] else ''})

        return result


    def _generate_answer_html(self, cursor):
        """Generate answer HTML using the given database cursor."""

        template_path = app_context.resource_path + '\\templates\\01-Quiz-Template.html'
        
        with open(template_path, encoding='utf-8') as f: html = f.read()

        style = 'border-left:none;border-top:none;border-right:none'
        new_row_tmp = (
            '        <tr>\n'
            f'            <td style="{style}; vertical-align:top;">{{0}})</td>\n'
            f'            <td style="{style}; width:{app_context.EDU_ITEM_PIXELS}; text-align:{{1}}">{{2}}</td>\n'
            f'            <td style="{style}; vertical-align:top">{{3}}</td>\n'
            '        </tr>\n'
        )

        feedback_tmp = (
            '        <tr>\n'
            f'           <td style="{style}; vertical-align:top;"></td>\n'
            f'           <td style="{style};color:darkgray; width:{app_context.EDU_ITEM_PIXELS}; text-align:{{0}}">{{1}}<br>{{2}}</td>\n'
            f'           <td style="{style}; vertical-align:top;"></td>\n'
            '        </tr>\n'
        )

        language = app_context.Language
        config = app_context.template_config.read()
        text_align = config[language]['Text align']
        total_score = 0.0
        rows = []

        quiz_id = self.data['quiz-id']
        #if not isinstance(quiz_ids, (list, tuple)):
        #    quiz_ids = [quiz_ids]

        #placeholders = ','.join(['%s'] * len(quiz_ids))
        cmd = f'SELECT responses_, scores_, feedback_ FROM quests WHERE id = {quiz_id};'
        
        cursor.execute(cmd)
        record = cursor.fetchone()

        if not record: return ''

        # Pattern explanation:
        # <div\b   – literal "<div" followed by a word boundary (ensures it's a tag, not part of a word)
        # [^>]*    – any characters except ">" (attributes, spaces, quotes)
        # >        – closing bracket of the opening tag
        # .*?      – any characters (non‑greedy), including newlines (re.DOTALL makes '.' match '\n')
        # </div>   – literal closing tag
        pattern = r'<div\b[^>]*>.*?</div>'

        # re.DOTALL allows the dot to match newline characters as well
        div_blocks = re.findall(pattern, str(record[0]), re.DOTALL)

        #scores = (str(record[1])[:-1]).split('-')

        rows.append(new_row_tmp.format('', text_align, record[0], ''))
        
        if record[2]:
            label = 'Feedback:'
            rows.append(feedback_tmp.format(text_align, label, record[2]))

        html = html.replace('<!-- NEW CONTENT -->', '\n'.join(rows), 1)
        html = self._apply_common_replacements(html, config, language, total_score, mode='answer')
        
        return html

    def _apply_common_replacements(self, html, config, language, total_score, mode):
        """Apply dimension, style, and content placeholders (same as before)."""
        ac = app_context
        dimensions = {
            '-- 2.43 inches --': f'{2.43 * ac.DPI}px',
            '-- 2.42 Inches --': f'{2.42 * ac.DPI}px',
            '-- 0.54 Inches --': f'{0.54 * ac.DPI}px',
            '-- 6.19 Inches --': f'{ac.EDU_ITEM_PIXELS}px',
        }
        for old, new in dimensions.items():
            html = html.replace(old, new)

        html = html.replace('-- font-family --', config[language]['Font family'])
        html = html.replace('-- direction --', config[language]['Direction'])
        html = html.replace('-- Text Alignment --', config[language]['Text align'])

        replacements = {
            '-- Stu-Name --': self.data['student'],
            '-- Date --': str(self.data.get('asign-date') or self.data.get('reply-date', '')),
            '-- Book-Grade --': '' if mode == 'quiz' else 'Answer sheet',
            '-- SUM --': str(total_score),
        }
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)

        return html
    
