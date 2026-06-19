
import base64
import re
import dateutil

from PySide6.QtCore import Qt, QThread, Signal,QObject

from PySide6.QtGui import QIcon

from PySide6.QtWidgets import ( QDialog, QFileDialog, QHBoxLayout, QLineEdit, QListWidget,
                               QMessageBox, QLabel, QTextEdit, QWidget, QListWidgetItem, 
                               QPushButton,QVBoxLayout, QTabWidget)

from PySideAbdhUI.Documents.document_editor import RichTextEditor   
from PySideAbdhUI.Notify import PopupNotifier
from processing.text import text_processing
from core.app_context import app_context
from utils.assessment_helper import (replace_placeholders, unwrap_page_divs, unpack_block,
                                     assessment_row_template, NEW_CONTENT_PLACEHOLDER)

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
        #    student: To display on the output report\
        #         Id: To dispaly on the formal assessments
        #     qb_ids: To fetch quiz content from question bank
        #    quiz-id: To fetch and update answer data in the quests table
        # assign-date: To display on the output report
        # reply-date: To display on output report and modify. 
        self.data = data
        self.need_update = False
        self.data_received = False
        self.setWindowTitle("")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        self.setFixedHeight(650)
        layout = QVBoxLayout(self)

        self.tab_widget = QWidget()
        self.setup_tabs()
        layout.addWidget(self.tab_widget)

        self.start_worker()

    def set_need_to_update(self): self.need_update = True

    def on_page_loaded(self,ok:bool):
        if ok:
            dir = self.data['configs']['Page direction']
            font = self.data['configs']['Font-family']
            self.preview_source.applyGlobalValue('dir', dir,is_property=False)
            self.preview_source.applyGlobalValue('font-family',font)

    def setup_tabs(self):

        # Create the tab structure (Quiz + optional Answers).
        layout = QVBoxLayout(self.tab_widget)
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(app_context.A4_PIXELS + 100)
        layout.addWidget(self.tabs)

        # Quiz tab
        self.preview_source = RichTextEditor()
        self.preview_source.loadFinished.connect(self.on_page_loaded)
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

        if not self.data_received: PopupNotifier.Notify(self,"","No data received!")

        else: PopupNotifier.Notify(self, message='Operation done!')

    def on_data_received(self, quiz, answer_blocks:list):
           
        # Save HTML for later PDF generation
        #self.quiz_html = quiz_html
        html, styles = quiz

        self.data_received = html != ''
        
        if not self.data_received: return
        
        # dir = "rtl" is default, user can change it.
        main_table = f'<div class="page" contenteditable="false">{html}</div>'
        
        self.preview_source.clearContent()
           
        self.preview_source.copy_content(content=main_table, custom_styles=styles,editable= False)

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
                PopupNotifier.Notify(self,'',f'"{reply_date}" is not valid date-time format')
                return

            app_context.database.execute(cmd, (reply_date , self.feedback_text.toPlainText().strip(),
                                              "-".join(score_text), answer_tags, self.data['quiz-id']))
            
            PopupNotifier.Notify(self, 'Save Answer','Answer updated.')
    
class HtmlGeneratorWorker(QObject):
    
    finished = Signal(tuple, list)       # quiz_html, answer_html
    error = Signal(str)               # error message

    def __init__(self, data):
        """
        data        : dict with 'student', 'qb_ids', 'quiz-id', 'assign-date', etc.
        db_config   : dict with PostgreSQL connection parameters 
                      (host, port, dbname, user, password)
        app_context : read-only object with DPI, paths, template config, etc.
        """
        super().__init__()
        self.data = data

    def run(self):
        #conn = None
        try:
            # Generate both HTML pieces
            quiz = self._generate_quiz_html()
            answer_blocks = self._extract_answers()
            
            # 3. Emit success (both strings)
            self.finished.emit(quiz, answer_blocks)

        except Exception as e:
            self.error.emit(str(e))

    def _generate_quiz_html(self):
        # List of questions from bank in string format  separated by '-'
        qb_ids:str = self.data['qb_ids']
        
        qb_ids = qb_ids.replace('-',',')

        cmd = f'SELECT content_, score_ FROM educational_resources WHERE id IN ({qb_ids});'

        #cursor.execute(cmd, qb_ids)
        records = app_context.database.fetchall(cmd)

        if not records: return ('','')

        config_filepath = app_context.resource_path + f'\\templates\\{self.data['configs']['Template']}-config.json'
        
        app_context.template_config.set_path(config_filepath)

        config = app_context.template_config.read()
        config = config[self.data['configs']['Language']]
        
        # Load template
        template_path = app_context.resource_path + f'\\templates\\{self.data['configs']['Template']}-Template.html'
        
        with open(template_path, encoding='utf-8') as f: html = f.read()

        #language = app_context.Language
        styles = []
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
            # Join all styles
            styles.append(new_style)
            # remove all div with class="page" apen/close part
            # and return pure content
            new_content = unwrap_page_divs(new_content)
            # data cleaning
            new_content = new_content.replace("\n","")
            
            # Generate new row for the table, this table is contains list of questions
            # format matching data: row index, content, point
            # this format is selected on template_changed event
            new_row = assessment_row_template.format(row + 1, new_content, item[1])
            new_row = new_row + NEW_CONTENT_PLACEHOLDER
            # Inject this row to the html body
            html = html.replace(NEW_CONTENT_PLACEHOLDER, new_row, count=1)
            
            row += 1

        date_ = dateutil.parser.parse(str(self.data['assign-date']))
        date_str = date_.strftime("%Y-%m-%d")

        data = {'Student':self.data['student'],
                'Teacher': self.data['configs']['Teacher'],
                'Title':self.data['configs']['Title'],
                'Date':date_str,
                'Time':self.data['configs']['Time'],
                'Duration':self.data['configs']['Duration'],
                'Total Score':str(total_score),
                'Template':self.data['configs']['Template']}
        
        if str(self.data['configs']['Template']).lower().find('formal')>-1:
            data['Student Id']= self.data['Id']
            data['Org-Info']= self.data['configs']['Org-Info']
            data['Academic Year'] = self.data['configs']['Academic Year']
            data['Term'] = self.data['configs']['Term']
            data['Field'] = self.data['configs']['Field']

        html = replace_placeholders(html, config, data)
    
        return (html, "\n".join(styles))


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

