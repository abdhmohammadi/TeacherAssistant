"""
# EduationalResourceViewer.py
# ###################################################################################################
#                             EDUCATION RESOURCE VIEWER                                             #
# ################################################################################################### 
# In this content we manage educational resources and make them ready to use. All datatypes must be #
# adjust size and qulity and other properties. the defualt paper size to publish is A4, thus width  #
# of all learning units that created in 'EduationalResourceViewer.py' is set to width of A4 210mm   #
# or 8.27 inches. To paublish/export the contents, User must be choose at least one item, there are #
# many template to publish, each template has specified settings to publish. All of templates is    #
# avilable in \resources\templates directory.                                                       #
# The main layout of the view is a 3x2 grid. Column 1 contains filter options and edu items list,   #
# and column 2 has provided for nessecery command, template settings and other actions.             # 
#####################################################################################################
"""
import os

from datetime import datetime, timedelta
import random
import re
#import pypandoc
from PySide6.QtCore import QTimer, Signal, QPoint

from PySide6.QtGui import (QIcon, QPixmap, Qt,QStandardItemModel, QStandardItem)

from PySide6.QtWidgets import ( QFileDialog, QFrame, QGridLayout, QScrollArea, QSizePolicy, QTabWidget, QVBoxLayout, QWidget, QLabel,QApplication,QDialog, QListView, QMessageBox,
                               QPushButton, QHBoxLayout, QLineEdit,QAbstractItemView,
                               QPlainTextEdit, QComboBox, QAbstractScrollArea,QMenu,QWidgetAction,)
from PySide6.QtWebEngineCore import QWebEngineScript
from PySideAbdhUI.Notify import PopupNotifier
#from PySideAbdhUI.CardGridView import CardGridView
from utils.editor_helper import unwrap_page_divs, custom_script
from ui.widgets.masonry_view import Card, MasonryView
from PySideAbdhUI.Documents.document_viewer import DocumentViewer
from PySideAbdhUI.Widgets import SearchBox

from ui.dialogs.answer_view import AnswerView

from core.app_context import app_context

###################################################################
# File names of Edu-Content templates
Edu_Template_Files = ['01-Quiz','02-Formal-Exam']

class EduResourcesView(QWidget):
    
    def __init__(self,parent=None, target_students=[dict]):

        super().__init__(parent)

        self.initalized = False
        self.templates_created = False
        self.selected_card:LearningItemWidget = None

        self.target_students = target_students
        # Defualt dispaly configs
        self.disply_columns = 2
        self.page_size = 50
        self.initUI()
    

    def initUI(self):

        if self.initalized : return

        self.setContentsMargins(10,0,10,10)
    
        self.main_layout = QVBoxLayout(self)
        
        header_widget = QWidget()
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(0,0,0,0)
        header.setSpacing(2)
        page_title = QLabel('RESOURCE COLLECTION')
        page_title.setProperty('class','heading2')
        header.addWidget(page_title,1)

        self.source_input = SearchBox(expanded_width=400)
        self.source_input.setPlaceholderText("Filter data using 'Source' ...")
        self.source_input.textEdited.connect(lambda text:self.load_data(filter=text) )
        header.addWidget(self.source_input,1)

        btn3 = QPushButton('distribute')
        header.addWidget(btn3)

        btn3.setMenu(self.create_distribution_options())
                
        self.main_layout.addWidget(header_widget) 
        
        self.setup_tabwidgets()

        self.initalized = True

        self.load_data()
    

    def _toggle_corner_widgets(self, index):

        self.tabs.cornerWidget(Qt.Corner.TopRightCorner).setVisible(index == 1)

        if(index == 1):
            # Generates full question table
            main_table  = self._generate_html_content() 
            main_table = f'<div class="page" contenteditable="false">{main_table}</div>'
            self.doc_view.clearContent()
            
            self.doc_view.copy_content(content=main_table,custom_styles="",editable= False)
            
            #script = QWebEngineScript(name="custom-script",sourceCode=custom_script)
            #self.doc_view.page().scripts().insert(script)


    def setup_tabwidgets(self):

        # -- Create tab widget --
        self.tabs = QTabWidget()
        # Add tabs to second row
        self.main_layout.addWidget(self.tabs)

        # -- Tab 1: Labels with random colored texts --
        tab1 = QWidget()
        self.setup_tab1(tab1)

        self.tabs.addTab(tab1, "COLLECTION")
        
        # -- Tab 2: Ring progress & controls --
        tab2 = QWidget()
        self.setup_tab2(tab2)
        self.tabs.addTab(tab2, "Assessment Preview")       

        self.create_corner_commands()

        self.tabs.setCurrentIndex(0)

        self.tabs.currentChanged.connect(lambda index:self._toggle_corner_widgets(index))

    # ---------- Tab 1: Ring progress ----------
    def setup_tab1(self, parent):

        layout = QVBoxLayout(parent)
        self.masonry_view = MasonryView()
        layout.addWidget(self.masonry_view)

    # ---------- Tab 2: Random colored labels ----------
    def setup_tab2(self, parent: QWidget):
        
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(5,5,5,5)
        self.doc_view = DocumentViewer()
        layout.addWidget(self.doc_view)

        container = self.create_output_template_selector()
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_scroll.setWidget(container)

        layout.addWidget(content_scroll)

        layout.setStretch(0,4)
        layout.setStretch(1,1)

    def create_corner_commands(self):
        w = QWidget()
        w.setVisible(False)
        w.setFixedHeight(38)
        hlayout = QHBoxLayout(w)
        hlayout.setContentsMargins(0,0,0,10)
        hlayout.setSpacing(2)

        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('publish')
        btn.clicked.connect(lambda: self.doc_view.LoadFileDialog(caption="Save File", dialog_type='save'))
        btn.setIcon(QIcon(":icons/save.svg"))
        
        hlayout.addWidget(btn)

        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('Fit page')
        btn.clicked.connect(self.doc_view.fitPage)
        btn.setIcon(QIcon(":icons/square-dashed.svg"))
        
        hlayout.addWidget(btn)

        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('Zoom in')
        btn.clicked.connect(self.doc_view.zoomIn)
        btn.setIcon(QIcon(":icons/zoom-in.svg"))
        
        hlayout.addWidget(btn)

        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('Zoom out')
        btn.clicked.connect(self.doc_view.zoomOut)
        btn.setIcon(QIcon(":icons/zoom-out.svg"))
        
        hlayout.addWidget(btn)

        
        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('Clear page')
        btn.clicked.connect(self.doc_view.clearContent)
        btn.setIcon(QIcon(":icons/trash-2.svg"))
        
        hlayout.addWidget(btn)

        btn = QPushButton('')
        btn.setProperty('class','mini')
        btn.setIcon(QIcon(":icons/refresh-ccw"))
        btn.clicked.connect(lambda: self._toggle_corner_widgets(1))
            
        hlayout.addWidget(btn)
        self.tabs.setCornerWidget(w,Qt.Corner.TopRightCorner)

    def get_deadline(self): return self.deadline_input.text()
    
    def get_distribution_time(self): return self.dist_time_input.text()
    
    def create_distribution_options(self):
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

        dist_options_layout = QGridLayout(widget) 
        dist_options_layout.setSpacing(0)
        dist_options_layout.addWidget(QLabel('Send to:'),0,0)
        
        stu_list = QListView(self)
        stu_list.setFixedWidth(150)
        stu_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        
        model = QStandardItemModel()

        for item in self.target_students:
            new_item = QStandardItem(f'{item['Name']}\n{item['Id']}')
            model.appendRow(new_item)

        stu_list.setModel(model)
        
        dist_options_layout.addWidget(stu_list,1,0,3,1, Qt.AlignmentFlag.AlignTop)

        dist_options_layout.addWidget(QLabel('distribution time'),0,1,Qt.AlignmentFlag.AlignTop)

        self.dist_time_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        dist_options_layout.addWidget(self.dist_time_input,1,1,Qt.AlignmentFlag.AlignTop)

        dist_options_layout.addWidget(QLabel('deadline'),2,1,Qt.AlignmentFlag.AlignTop)
        
        self.deadline_input = QLineEdit((datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        dist_options_layout.addWidget(self.deadline_input,3,1,Qt.AlignmentFlag.AlignTop)

        dist_options_layout.setRowStretch(3,1)

        btn4 = QPushButton('distribute')
        btn4.clicked.connect(self.distribute)

        dist_options_layout.addWidget(btn4,4,0,1,2)        
        
        return menu   

    def distribute(self):
        '''Distributes selected edu-items to the students'''
        
        # When students has not been specified, we try to publish an assessment as html file.
        if len(self.target_students) == 0:
            self.create_output_template_selector()
        else:

            try:
                
                items = self.get_selected_contents()
        
                if len(items) == 0: 
                    PopupNotifier.Notify(self,'SEND','No Edu-Item selected.')
                    return
                
                stu_cnt = len(self.target_students)
                msg  = f'Number of {len(items)-1} edu-item{'s' if len(items)-1>1 else ''} will be assigned to {stu_cnt} student{'s' if stu_cnt>1 else ''}\n'
                msg += 'are you sure?'

                if QMessageBox.StandardButton.Cancel == QMessageBox.question(self,'',msg,QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Cancel): return
                # Get current UTC time
                utc_time = self.get_distribution_time()

                future_time = self.get_deadline()
                
                for stu in self.target_students: 
                    qb_IDs = ''
                    # List of Edu-Items: last index was included sub totlal values
                    for item in items[:len(items)-1]: 
                        qb_IDs += str(item['Id']) +'-'

                    total_score =  items[len(items)-1]['total_score']
                    
                    cmd = 'INSERT INTO quests(student_id, qb_ids_, assign_date_, deadline_, total_score_, reply_date_, scores_, responses_, feedback_) '
                    
                    cmd += 'VALUES(%s, %s, %s,%s, %s, %s, %s, %s, %s)'
        
                    values = (stu['Id'], qb_IDs[:-1], str(utc_time), str(future_time),total_score, None, None, None, None)

                    app_context.database.execute(cmd,values)
                
                msg  = f'Number of {len(items)-1} edu-item{'s' if len(items)-1>1 else ''} was assigned to {stu_cnt} student{'s' if stu_cnt>1 else ''} successfully'
                
                PopupNotifier.Notify(self,'',msg)
            
            except Exception as e: PopupNotifier.Notify(self,'',f'Database error: {e}.')

    def create_output_template_selector(self):

        if not self.templates_created:
            w = QWidget()
            self.config_layout = QVBoxLayout(w)
            self.config_layout.setContentsMargins(5,0,5,0)
            template_selector_combo = QComboBox()
            template_selector_combo.setPlaceholderText('-- Select a template --')
            template_selector_combo.addItems(['Classroom quiz','Formal exam'])
            template_selector_combo.currentIndexChanged.connect(lambda _, sender= template_selector_combo: self.template_changed(sender))
            
            self.config_layout.addWidget(template_selector_combo)

            template_selector_combo.setCurrentIndex(0)

            return w
    
    def template_changed(self,sender:QComboBox):
        
        index = sender.currentIndex()

        if index < 0 : return

        self.edu_template_file = ''

        if not self.templates_created: 

            self.stu_info_input = QLineEdit('')
            self.stu_info_input.setPlaceholderText('Student name')
            self.config_layout.addWidget(self.stu_info_input)
            
            self.stu_id_input = QLineEdit('')
            self.stu_id_input.setPlaceholderText('Student Id')
            self.config_layout.addWidget(self.stu_id_input)
            
            self.teacher_input = QLineEdit('')
            self.teacher_input.setPlaceholderText('Teacher name')
            self.config_layout.addWidget(self.teacher_input)

            self.author_input = QLineEdit('')
            self.author_input.setPlaceholderText('Author')
            self.config_layout.addWidget(self.author_input)

            self.org_info_input = QPlainTextEdit('')
            self.org_info_input.setPlaceholderText('Oragnisation info')
            self.org_info_input.document().setDefaultTextOption(Qt.AlignmentFlag.AlignCenter)
            self.org_info_input.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
            self.config_layout.addWidget(self.org_info_input)

            self.book_grade_input = QLineEdit('')
            self.book_grade_input.setPlaceholderText('Book and Grade info')
            self.config_layout.addWidget(self.book_grade_input)

        
            self.field_input = QLineEdit('')
            self.field_input.setPlaceholderText('Field Study')
            self.config_layout.addWidget(self.field_input)

            self.term_input = QPlainTextEdit()
            self.term_input.document().setHtml('')
            self.term_input.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
            self.term_input.setPlaceholderText('Term')
            self.config_layout.addWidget(self.term_input)

            self.date_input = QLineEdit('')
            self.date_input.setPlaceholderText('Exam date')
            self.config_layout.addWidget(self.date_input)

            tm_layout = QHBoxLayout()
            self.clock_input = QLineEdit('')
            self.clock_input.setPlaceholderText('Clock: --:-- ')

            tm_layout.addWidget(self.clock_input)
        
            self.time_input = QLineEdit('')
            self.time_input.setPlaceholderText('Time: --')

            tm_layout.addWidget(self.time_input)
            self.config_layout.addLayout(tm_layout)

            btn = QPushButton('     Reload')
            btn.setIcon(QIcon(":icons/refresh-ccw"))
            btn.clicked.connect(lambda: self._toggle_corner_widgets(1))
            
            self.config_layout.addWidget(btn)
            self.config_layout.addStretch()

            self.templates_created = True


        
        if self.templates_created:

            self.stu_info_input.setVisible(False)
            self.stu_id_input.setVisible(False)
            self.teacher_input.setVisible(False)
            self.author_input.setVisible(False)
            self.org_info_input.setVisible(False)
            self.book_grade_input.setVisible(False)
            self.field_input.setVisible(False)
            self.term_input.setVisible(False)
            self.date_input.setVisible(False)
            self.clock_input.setVisible(False)
            self.time_input.setVisible(False)
            
        
        new_row_tmp = ''

        language = app_context.Language
        
        self.edu_template_file = Edu_Template_Files[index]

        config_filepath = app_context.resource_path + f'\\templates\\{self.edu_template_file}-config.json'
        
        app_context.template_config.set_path(config_filepath)
        config = app_context.template_config.read()

        
        # Common configs
        self.stu_info_input.setPlaceholderText(config[language]['Student name'])
        self.stu_info_input.setText(config[language]['Student name'])
        self.book_grade_input.setPlaceholderText(config[language]['Book'])
        self.book_grade_input.setText(config[language]['Book'] +' math')
        self.date_input.setPlaceholderText(config[language]['Date'])
        self.date_input.setText(config[language]['Date'] + ' ' + datetime.now().strftime("%Y-%m-%d"))
            
        self.stu_info_input.setVisible(True)
        self.book_grade_input.setVisible(True)
        self.date_input.setVisible(True)

        # Special configs
        if index == 0: # Classroom quiz has been selected

            self.stu_id_input.setVisible(False)
            self.teacher_input.setVisible(False)
            self.author_input.setVisible(False)
            self.org_info_input.setVisible(False)
            self.field_input.setVisible(False)
            self.term_input.setVisible(False)
            self.clock_input.setVisible(False)
            self.time_input.setVisible(False)
        
        # row index,text_align,content,point
        elif index == 1: # Formal template hass been selected
                
                self.stu_id_input.setVisible(True)
                self.teacher_input.setVisible(True)
                self.author_input.setVisible(True)
                self.org_info_input.setVisible(True)
                self.field_input.setVisible(True)
                self.term_input.setVisible(True)
                self.clock_input.setVisible(True)
                self.time_input.setVisible(True)
                

                self.stu_id_input.setPlaceholderText(config[language]['Student Id'])
                self.stu_id_input.setText(config[language]['Student Id'])
                self.teacher_input.setPlaceholderText(config[language]['Teacher name'])
                self.teacher_input.setText(config[language]['Teacher name'])
                self.author_input.setPlaceholderText(config[language]['Author'])
                self.author_input.setText(config[language]['Author'])
                self.org_info_input.setPlaceholderText(config[language]['Organization info'])
                self.org_info_input.setPlainText(config[language]['Organization info'])               
                self.org_info_input.setFixedHeight(100)
                self.field_input.setPlaceholderText(config[language]['Field Study'])
                self.field_input.setText(config[language]['Field Study'])
                self.term_input.setPlaceholderText(config[language]['Academic year'])
                self.term_input.setPlainText(config[language]['Academic year'])
                self.term_input.setFixedHeight(60)
                self.clock_input.setPlaceholderText(config[language]['Clock'])
                self.clock_input.setText(config[language]['Clock'])
                self.time_input.setPlaceholderText(config[language]['Time'])
                self.time_input.setText(config[language]['Time'])

        # Common table rows: question contents
        new_row_tmp =  '        <tr>\n'
        new_row_tmp += f'            <td style="text-align: center; vertical-align:top;width:-- 0.54 Inches --;">{{}}</td>\n'
        new_row_tmp += f'            <td style="border-left:none;border-right:none; width:{app_context.EDU_ITEM_PIXELS};">{{}}</td>\n'
        new_row_tmp += f'            <td style="text-align: center; vertical-align:top;width:-- 0.54 Inches --;">{{}}</td>\n'
        new_row_tmp +=  '        </tr>\n'

        self.content_row_template = new_row_tmp

        self.config = config


    def remove_card(self):
        """Remove the selected card"""
        selected_card = self.card_grid.get_selected_card()
        if selected_card:
            # Find the card ID
            for card_id, card in self.card_grid.cards.items():
                if card.widget == selected_card:
                    self.card_grid.remove_card(card_id)
                    break
    

    def clear_cards(self):
        """Clear all cards"""
        self.card_grid.clear()
        self.next_card_id = 1
    
    def on_card_selected(self,widget:LearningItemWidget):

        if self.selected_card: self.selected_card.hide_titlebar()
        # Handle card selection:
        # The selected widget is type of EduItemWidget, this Item has a DataModel
        # and the DataModel has a Id Property
        widget.show_titlebar()
        self.selected_card = widget
    

    def on_card_removed(self, widget: QWidget):
        """Handle card removal"""
        pass
        

    def generate_edu_contents(self):
        # Validate template selection and existence
        if not self.___validate_template__(): return

        # Get selected items and validate
        selected_content = self.get_selected_contents()

        if not selected_content:
            PopupNotifier.Notify(self, 'Info', 'No item selected')
            return

        # Generate HTML content
        html = self._generate_html_content()

        # Show PDF preview window
        self.___show_pdf_preview__(html)


    def ___validate_template__(self) -> bool:
        # Validate template file selection and existence
        if self.edu_template_file == '':
            PopupNotifier.Notify(self, 'Error', 'The output template has not selected.')
            return False
        
        template_file = app_context.resource_path + f'\\templates\\{self.edu_template_file}-Template.html'
        
        if not os.path.exists(template_file):
            PopupNotifier.Notify(self, 'Error', f'The template file not found in the specified path --> {template_file}')
            return False
            
        #self.edu_template_file = template_file
        return True
    

    def get_selected_contents(self):
        """
            Returns list fo dict of {row, Id, content, score}...{total_score}
        """
        # Get selected cards and their content
        selected_content = []
        # Sum of scores of all questions
        total_points = 0
        
        for card in self.masonry_view.cards:

            widget:LearningItemWidget = card.widget
            data = widget.data

            if widget.is_selected:
                
                selected_content.append(data)
                total_points += data['score']
        
        if selected_content: # Sum of scores of all questions
            selected_content.append({'total_score': total_points})
            
        return selected_content

    # the selected_content will be removed
    def _generate_html_content(self) -> str:

        # Generate HTML content with template placeholders replaced
        # Read template file 01-Quiz-template.html or 02-Formal-Exam-Template.html
        template_file = app_context.resource_path + f'\\templates\\{self.edu_template_file}-Template.html'
        with open(template_file, encoding="utf-8",mode='r') as f: html = f.read()
        
        language = app_context.Language
        
        # Replace content placeholders
        new_content_template = '<!-- NEW CONTENT -->'
        styles = ""
        total_score = 0.0
        row = 0
        for card in self.masonry_view.cards:
            widget:LearningItemWidget = card.widget
            data = widget.data
            
            if widget.is_selected:

                total_score += data['score']
                new_style, new_content = unpack_block(data["content"])
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
                # format matching data: row index,text_align,content,point
                # this format is selected on template_changed event
                new_row = self.content_row_template.format(row + 1, new_content, data['score'])
                new_row = new_row + new_content_template
                # Inject this row to the html body
                html = html.replace(new_content_template, new_row, count=1)
                row += 1
        
        # Inject styles to the <head> ...</head>
        html = html.replace('</head>',f'\n{styles}\n</head>')
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

        # Replace style placeholders
        #html = html.replace('-- font-family --', self.config[language]['Font family'])
        html = html.replace('-- direction --', 'rtl')#self.config[language]['Direction'])
        #html = html.replace('-- Text Alignment --', text_align)

        # Replace content placeholders
        replacements = {
            '-- In the name of God --': self.config[language]['InTheNameOfGod'], # In the formal exam template
            '-- Stu-Name --': self.stu_info_input.text(), # In the both templates
            '-- Stu-Id --': self.stu_id_input.text(), # In the formal exam template
            '-- Organisation Info --': self.org_info_input.toPlainText().replace('\n','<br>'),
            '-- Academic-Year-Term --': self.term_input.toPlainText().replace('\n','<br>'),
            '-- Date --': self.date_input.text(), # In the both templates
            '-- Teacher-Name --': self.teacher_input.text(),
            '-- Clock --': self.clock_input.text(),
            '-- Book-Grade --': self.book_grade_input.text(), # In the both templates
            '-- Field --': self.field_input.text(),
            '-- Time-Pages --': self.time_input.text(),
            '-- ROW --':"ردیف",
            '-- SCORE --':"نمره",
            '-- Index --': self.config[language]['Row'],# In the both templates
            '-- Edu-Content --': self.config[language]['Header'],
            '-- Point --': self.config[language]['Score'], # In the both templates
            '-- Author: Abdh --': self.author_input.text(),
            '-- SUM --': str(total_score),
            '-- FOOTER SUM --': self.config[language]['Footer sum'],
        }
        
        for placeholder, value in replacements.items(): html = html.replace(placeholder, value)

        return html


    def ___show_pdf_preview__(self, html):

        self.dialog.move(10, 25)
    
        view = DocumentViewer()
        view.loadHtml(html)
        
        dlg = QDialog(parent=self.dialog)

        layout = QVBoxLayout(dlg)
        hl = QHBoxLayout()
        
        hl.addStretch(1)

        def save_pdf():
            filepath, _ = QFileDialog.getSaveFileName(self, '', '','PDF(*.pdf)')
            
            if not filepath: return

            view.savePdf(filepath)
            dlg.close()
            self.dialog.close()
            
        btn_save = QPushButton("Save")
        
        btn_save.clicked.connect(save_pdf)

        hl.addWidget(btn_save)

        btn_close = QPushButton("close")
        btn_close.clicked.connect(dlg.reject)

        hl.addWidget(btn_close)
        layout.addLayout(hl)
        layout.addWidget(view)
        
        dlg.setFixedWidth(app_context.A4_PIXELS+50)
        dlg.setFixedHeight(750)
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.move(self.dialog.geometry().topRight().x() + 10, 10)
        
        button = dlg.exec()
        if button == 1:
            # save
            save_pdf()


        self.dialog.setModal(True)
 

    def load_answer(self, Id):

        try:
            
            data = app_context.database.fetchone(f'SELECT answer_, metadata_ FROM educational_resources WHERE Id = {Id};')
            
            self.answer = data[0]
            self.details = data[1]

        except Exception as e: raise(e)

        return data
 

    def _create_data_dict(self, Id, source:str, content:str,answer:str, metadata:str,score:float):
        
        return {"Id":Id,
                "source":source,
                "content":content,
                "answer":answer,
                "metadata":metadata,
                "score":score}

    def _on_answer_requested(self,sender:LearningItemWidget):
        
        data = self.load_answer(sender.data["Id"])

        sender.data["answer"] = data[0]
        sender.data["metadata"] = data[1]
        sender.show_answer()
        
    def load_data(self, filter: str = ''):
        
        self.masonry_view.clear()
        self.current_page = 0
        self.has_more = True
        self.current_filter = filter
        
        # Use server-side cursor for streaming + low memory
        search = f"%{self.current_filter}%".strip()
        # Build safe parameterized query
        base_query  = "SELECT Id, source_, content_, score_, metadata_ FROM educational_resources"
        where_parts = f"(source_ ILIKE '%{search}' OR content_ ILIKE '%{search}' "
        where_parts = f"{where_parts} OR metadata_ ILIKE '%{search}' OR TEXT(Id) ILIKE '%{search}')"
                          
        where_clause = "WHERE " + where_parts if where_parts else ""

        order_by = "ORDER BY score_ DESC NULLS LAST, Id DESC"

        full_query = f"{base_query} {where_clause} {order_by}"

        rows = app_context.database.fetchall(full_query)
        
        if rows:
            self.data_count = len(rows)
            self.loaded_count = 0

            # Add each HTML item to the list widget
            for record in rows:
                data_dict = self._create_data_dict(record[0], record[1], record[2],'', record[4], record[3] )
                # Create a custom widget for the item
                viewer = DocumentViewer(default_size="Edu-Item")
                
                viewer.setFixedWidth(app_context.A4_PIXELS)
                viewer.setPageMargins(5,10,5,10)

                # self._view_model.content is a block of question/learning material
                block = record[2]
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

                viewer.copy_content(block, styles)

                w = LearningItemWidget(data=data_dict)

                w.initUI(viewer)
                w.on_answer_requested.connect(lambda arg: self._on_answer_requested(arg))
                card = Card(w)
                viewer.loadFinished.connect(lambda ok,c=card, sender=viewer: self._on_viewer_loaded(ok,c, sender))
                self.masonry_view.add_card(card)

    def _on_viewer_loaded(self, ok: bool,card:Card, sender:DocumentViewer):
        
        if ok:
            sender.toggle_scroll_visibility(False)
        
            szF = sender.getComputedSizeAsync()

            sender.setFixedHeight(szF.height())
            
            card.setFixedSize(int(szF.width())+5, int(szF.height()+42))

            self.loaded_count+=1

            if self.loaded_count == self.data_count: self.masonry_view.update_view()

class LearningItemWidget(QWidget):
    
    on_answer_requested  = Signal(QWidget) # emit Id of the learnig Item(Like Id of the question record in the database)
    on_answer_received = Signal(str)
    
    def __init__(self, parent=None, data:dict={}):

        super().__init__(parent)
        
        self.titlebar_created = False
        self.info_panel_created = False
        self.data = data
        self.data["user-selected"] = False
        if data == {}:
            self.data = {"Id":0,
                         "source":"",
                         "content":"",
                         "answer":"",
                         "metadata":"",
                         "score":0.0,
                         "user-selected":False
                        }
            
    def initUI(self, data_presenter_widget:QWidget):
        
        # Create a layout for the item with no margins or spacing
        self.main_layout = QGridLayout(self)

        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(0)
        # packground layer for visual porposes               
        self.background_layer = QWidget()
        self.background_layer.setProperty('class', 'EduItem')
        self.background_layer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout.addWidget(self.background_layer,0,0,2,1)

        self.titlebar = self.create_titlebar()

        self.main_layout.addWidget(self.titlebar,0,0,1,1)

        # Create a QLabel for the HTML content
        self.data_presenter = data_presenter_widget
        
        # Add the content label to the layout
        self.main_layout.addWidget(self.data_presenter,1,0,1,1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

    def create_titlebar(self):
        
        if not self.titlebar_created:

            cmd_widget = QWidget()

            cmd_widget.setFixedHeight(34)
            
            commands = QHBoxLayout(cmd_widget)
            commands.setContentsMargins(5,0,5,0)
            commands.setSpacing(2)
            # Add checkbox to select edu-item
            checkbox = QPushButton('')
            checkbox.setCheckable(True)
            checkbox.setToolTip('Check to select the item.')
            #checkbox.setVisible(False) 
            checkbox.setProperty('class','checkLike')
            checkbox.clicked.connect(lambda _, sender= checkbox: self._on_toggle_selection(sender))
            commands.addWidget(checkbox)

            self.mark_label = QLabel()

            self.mark_label.setPixmap(QPixmap(':icons/bookmark-filled-blue.svg'))
            # First item of the titlebar
            commands.addWidget(self.mark_label)
            self.mark_label.setVisible(self.is_marked)
            self.mark_label.setProperty('class','caption')
            self.mark_label.setToolTip(app_context.ToolTips['Marked Item'])

            # Display Id: <id> | <score> | <Source>
            header_info = QLabel(self.data['source'] + (' | ' if self.data['source'] !='' else '') 
                                                     + str(self.data['score']) + ' | ' + str(self.data['Id']))
            
            header_info.setToolTip('Id | score | source' if self.data['source'] != '' else 'Id | score')

            header_info.setProperty('class','caption')

            commands.addWidget(header_info)
            
            commands.addStretch(1)
            
            ans_mnu_btn = QPushButton('')
            ans_mnu_btn.setIcon(QIcon(':icons/book-text.svg'))
            #ans_mnu_btn.setVisible(False)
            ans_mnu_btn.setToolTip('Show information about Edu-item')
            ans_mnu_btn.setProperty('class','grouped_mini')
            ans_mnu_btn.clicked.connect(self.___on_answer_requested)
            #lambda _, sender = cmd_widget: self.load_answer(sender))

            commands.addWidget(ans_mnu_btn)
            
            btn2 = QPushButton('')            
            btn2.setIcon(QIcon(':icons/bookmark.svg'))
            #btn2.setVisible(False)
            btn2.setToolTip(app_context.ToolTips['Set bookmark'])
            btn2.setProperty('class','grouped_mini')
            menu = self.create_bookmark_menu()
            btn2.setMenu(menu)
            
            commands.addWidget(btn2)

            self.titlebar_created = True

        return cmd_widget
    

    def ___on_answer_requested(self):
        
        if not self.answer_loaded: self.on_answer_requested.emit(self)

    def _update_metadata(self,Id, value):

        app_context.database.execute(f"UPDATE educational_resources SET metadata_ = '{value}' WHERE Id = {Id};")
        self.data["metadata"] = value
        PopupNotifier.Notify(self, "", "Metadata updated.")
    
    def show_answer(self):

        if not self.info_panel_created:

            info_panel = QGridLayout()
            header_info = QLabel(f"{self.data["score"]} | {self.data["Id"]} | {self.data["source"]}")

            header_info.setToolTip("score | Id | source")

            info_panel.addWidget(header_info,0,0,1,1,Qt.AlignmentFlag.AlignLeft)
               
            ans_label = QLabel()
            ans_label.setWordWrap(True)        
            #ans_label.setTextFormat(Qt.TextFormat.RichText)
            help_note = "No answer provided yet!\nAdd answer in the Editor then you will see here your added answer. " \
            f"In the Editor, find this item by Id= {self.data["Id"]}. go to \"Answer\" tab, and write the answer."
            
            ans_label.setText(self.data["answer"] if self.data["answer"] != '' else help_note)
            
            #ans_label.setProperty('class','EduItem')
            info_panel.addWidget(ans_label,1,0,1,1,Qt.AlignmentFlag.AlignTop)

            details_input = QPlainTextEdit()
            details_input.setPlaceholderText("add here comment or analytical points")
            details_input.setMaximumHeight(100)
            details_input.setPlainText(self.data["metadata"])
            # Bind UI elements to ViewModel properties
            #self._view_model.bind_property("details", self._view_model.details, details_input)
           
            info_panel.addWidget(details_input,2,0,1,1,Qt.AlignmentFlag.AlignTop)
            
            footer_widget = QWidget()
            footer_layout = QHBoxLayout(footer_widget)
            footer_layout.setSpacing(2)
            
            footer_layout.addStretch(1)

            update_details_btn = QPushButton('update metadata')
            update_details_btn.setToolTip("Only update metadata")
            update_details_btn.clicked.connect(lambda: self._update_metadata(self.data["Id"], details_input.toPlainText()))
            footer_layout.addWidget(update_details_btn,alignment=Qt.AlignmentFlag.AlignRight)

            info_panel.addWidget(footer_widget,3,0,1,1)

            info_widget = QWidget()
            info_widget.setLayout(info_panel)

            # Create a QMenu: this menu must be bind to 'More Info button on the header of Edu-Item'
            menu = QMenu(self.titlebar)
            # Create a QWidgetAction to hold custom widgets
            widget_action = QWidgetAction(self.titlebar)
            # Set the widget to the QWidgetAction
            widget_action.setDefaultWidget(info_widget)
            # Add the QWidgetAction to the menu
            menu.addAction(widget_action)
            
            menu.sizeHint()

            self.info_panel_created = True

            self.info_panel_menu = menu

        r = self.rect()
        p = r.topLeft()
        py = 18 # titlebar height/2
        px = (r.width())/4
        point = self.mapToGlobal(p + QPoint(px,py))

        self.info_panel_menu.exec(point)
        
    def create_bookmark_menu(self):
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

        menu_layout = QVBoxLayout(widget)        
        menu_layout.addWidget(QLabel('Bookmark note'))
        # Add a QLineEdit
        line_edit = QLineEdit('')
        line_edit.setPlaceholderText("Add note ...")
        menu_layout.addWidget(line_edit)

        # Add Find Id QPushButton
        inner_button = QPushButton('Set bookmark')
        
        inner_button.clicked.connect(lambda _, sender= line_edit:self.set_bookmark(sender))

        menu_layout.addWidget(inner_button,stretch=0, alignment=Qt.AlignmentFlag.AlignRight)

        # Set the menu to the QPushButton
        return menu

    def set_bookmark(self, sender:QLineEdit):
        
        if not self.is_marked:
            
            self.data['metadata'] = '[MARKED]' + sender.text() + '\n' + self.data['metadata']
            
            status, msg = True, "The code need to implement"#self._view_model.update_value('metadata_',self._view_model.details)
            
            if status: 
                self.titlebar.layout().itemAt(0).widget().setVisible(True)
                #msg = 'The item was marked now, to reomve bookmark delete keyword [MARKED] from "details" and save.'

            PopupNotifier.Notify(self, 'Update bookmark', msg)
    
    @property
    def answer_loaded(self): return self.data["answer"] != ""
    
    @property
    def is_marked(self): return '[MARKED]' in self.data['metadata']
    
    @property
    def is_selected(self): return self.data["user-selected"]
        
    def _on_toggle_selection(self, sender:QPushButton):
        
        #self.selected = not self.selected
        self.data["user-selected"] = sender.isChecked()

        sender.setIcon(QIcon(':icons/check.svg') if self.is_selected else QIcon())

        self.background_layer.setProperty("class", "EduItem-Selected" if self.is_selected else "EduItem")

        self.background_layer.style().unpolish(self.background_layer)
        self.background_layer.style().polish(self.background_layer)
        self.background_layer.update()



 ################ html helpers ###########################

def unpack_block(block:str)->tuple[str, str]:
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
    return styles, block
