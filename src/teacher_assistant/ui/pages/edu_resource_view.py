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
#import pypandoc
from PySide6.QtCore import QThreadPool, Slot, QPoint

from PySide6.QtGui import (Qt,QStandardItemModel, QStandardItem)

from PySide6.QtWidgets import ( QGridLayout, QWidget, QLabel,QApplication,QDialog, QListView, QMessageBox,
                               QPushButton, QHBoxLayout, QLineEdit,QAbstractItemView,
                               QPlainTextEdit, QComboBox, QAbstractScrollArea,QMenu,QWidgetAction,)

from PySideAbdhUI.Notify import PopupNotifier
from PySideAbdhUI.CardGridView import CardGridView

from processing.utils.pdf import PdfGeneratorApp
from data.loaders import DataLoaderWorker
from ui.widgets.widgets import EduItemWidget
from core.app_context import app_context

###################################################################
# File names of Edu-Content templates
Edu_Template_Files = ['01-Quiz','02-Formal-Exam']

class EduResourcesView(QWidget):
    
    def __init__(self,parent=None, target_students=[dict]):

        super().__init__(parent)

        self.initalized = False

        self.selected_card:EduItemWidget = None

        self.target_students = target_students
        # Defualt dispaly configs
        self.disply_columns = 2
        self.page_size = 50
        self.initUI()
    
    def initUI(self):

        if self.initalized : return

        self.setContentsMargins(10,0,10,10)

        # Initialize the UI. (QGridLayout 3x2)
        # Column 1 contains filter options and edu items list,
        # and column 2 has provided for nessecery command, template settings and other actions.
        main_layout = QGridLayout(self)
        
        header_widget = QWidget()
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(0,0,0,0)
        header.setSpacing(2)
        page_title = QLabel('RESOURCE COLLECTION')
        page_title.setProperty('class','heading2')
        header.addWidget(page_title,1)

        #header.addStretch(1)
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Filter data using 'Source' ...")
        self.source_input.textChanged.connect(lambda text:self.load_data(filter=text) )
        header.addWidget(self.source_input,1)

        btn3 = QPushButton('distribute')
        header.addWidget(btn3)

        btn3.setMenu(self.create_distribution_options())
        # Create card grid view
        #self.card_grid = CardGridView(self.disply_columns)
        self.card_grid = CardGridView(self.disply_columns, parent=self)
        # Connect the signal to your loader
        # @@@@ self.card_grid.load_more_requested.connect(self.load_next_page)
        
        # Connect signals
        self.card_grid.card_selected.connect(self.on_card_selected)
        self.card_grid.card_removed.connect(self.on_card_removed)
        
        # Filter and it's commands
        main_layout.addWidget(header_widget, 0, 0) # Cell [0,0]
        # QListViewWidget for Edu-content
        main_layout.addWidget(self.card_grid,1,0)# Cell [1,0]
        main_layout.setRowStretch(1,1)
        
        self.templates_created = False

        self.initalized = True

        self.load_data()
        
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
        if len(self.target_students) == 0:
            self.show_template_selector_dlg()
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

                    # List of Edu-Items
                    for item in items[:len(items)-1]: # last index was included sub totlal values
                        cmd = 'INSERT INTO quests(qb_id, student_id, max_point_, earned_point_, assign_date_, deadline_, answer_, reply_date_, feedback_) '
                        cmd += 'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)'
        
                        values = (item['Id'], stu['Id'], item['score'], 0, str(utc_time), str(future_time), None, None, None)

                        app_context.database.execute(cmd,values)
                
                msg  = f'Number of {len(items)-1} edu-item{'s' if len(items)-1>1 else ''} was assigned to {stu_cnt} student{'s' if stu_cnt>1 else ''} successfully'
                
                PopupNotifier.Notify(self,'',msg)
            
            except Exception as e: PopupNotifier.Notify(self,'',f'Database error: {e}.')


    def show_template_selector_dlg(self):

        if not self.templates_created:

            self.config_layout = QGridLayout()
            self.config_layout.setContentsMargins(16,16,16,16)
            self.config_layout.addWidget(QLabel('SELECT OUTPUT TEMPLATE'),0,0)
            template_selector_combo = QComboBox()
            template_selector_combo.setPlaceholderText('-- Select a template --')
            template_selector_combo.addItems(['Classroom quiz','Formal exam'])
            template_selector_combo.currentIndexChanged.connect(lambda _, sender= template_selector_combo: self.template_changed(sender))
            
            self.config_layout.addWidget(template_selector_combo,1,0)

            self.dialog = QDialog(self)
            self.dialog.setWindowTitle('DISTRIPUTION')
            self.dialog.setFixedWidth(400)
            self.dialog.setLayout(self.config_layout)

            geo = QApplication.activeWindow().geometry()
            x = geo.left() + geo.width()//2 - self.dialog.width()/2
            self.dialog.move(x, geo.top() + 40)
            template_selector_combo.setCurrentIndex(0)

        self.dialog.exec()

    
    def template_changed(self,sender:QComboBox):
        
        index = sender.currentIndex()
        if index<0: return

        self.edu_template_file = ''

        if not self.templates_created: 

            self.stu_info_input = QLineEdit('')
            self.stu_info_input.setPlaceholderText('Student name')
            self.config_layout.addWidget(self.stu_info_input,2,0)
            
            self.stu_id_input = QLineEdit('')
            self.stu_id_input.setPlaceholderText('Student Id')
            self.config_layout.addWidget(self.stu_id_input,3,0)
            
            self.teacher_input = QLineEdit('')
            self.teacher_input.setPlaceholderText('Teacher name')
            self.config_layout.addWidget(self.teacher_input,4,0)

            self.author_input = QLineEdit('')
            self.author_input.setPlaceholderText('Author')
            self.config_layout.addWidget(self.author_input,5,0)

            self.org_info_input = QPlainTextEdit('')
            self.org_info_input.setPlaceholderText('Oragnisation info')
            self.org_info_input.document().setDefaultTextOption(Qt.AlignmentFlag.AlignCenter)
            self.org_info_input.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
            self.config_layout.addWidget(self.org_info_input,6,0)

            self.book_grade_input = QLineEdit('')
            self.book_grade_input.setPlaceholderText('Book and Grade info')
            self.config_layout.addWidget(self.book_grade_input,7,0)

        
            self.field_input = QLineEdit('')
            self.field_input.setPlaceholderText('Field Study')
            self.config_layout.addWidget(self.field_input,8,0)

            self.term_input = QPlainTextEdit()
            self.term_input.document().setHtml('')
            self.term_input.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
            self.term_input.setPlaceholderText('Term')
            self.config_layout.addWidget(self.term_input,9,0)
                        

            self.date_input = QLineEdit('')
            self.date_input.setPlaceholderText('Exam date')
            self.config_layout.addWidget(self.date_input,10,0)


            self.clock_input = QLineEdit('')
            self.clock_input.setPlaceholderText('Clock: --:-- ')
            self.config_layout.addWidget(self.clock_input,11,0)

        
            self.time_input = QLineEdit('')
            self.time_input.setPlaceholderText('Time: --')
            self.config_layout.addWidget(self.time_input,12,0)
            
            btn = QPushButton('Generate Edu-content')
            btn.clicked.connect(lambda: self.generate_edu_contents())
            self.config_layout.addWidget(btn,13,0)
           
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

        language =app_context.Language

        #config_file  = state.application_path + f'\\resources\\templates\\{Edu_Template_Files[index]}-config.json'
        #template_config.set_path(config_file)
        config = None#template_config.read()

        # Common configs
        self.stu_info_input.setPlaceholderText(config[language]['Student name'])
        self.stu_info_input.setText(config[language]['Student name'])
        self.book_grade_input.setPlaceholderText(config[language]['Book'])
        self.book_grade_input.setText(config[language]['Book'])
        self.date_input.setPlaceholderText(config[language]['Date'])
        self.date_input.setText(config[language]['Date'])
            
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


                new_row_tmp =  '        <tr>\n'
                new_row_tmp += f'            <td style="border-left:none;border-top:none;border-right:none; vertical-align:top;">{{}})</td>\n'
                new_row_tmp += f'            <td style="border-left:none;border-top:none;border-right:none; width:{app_context.EDU_ITEM_PIXELS}; text-align:{{}}">{{}}</td>\n'
                new_row_tmp += f'            <td style="border-left:none;border-top:none;border-right:none; vertical-align:top">{{}}</td>\n'
                new_row_tmp +=  '        </tr>\n'
        
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

                new_row_tmp =  '        <tr>\n'
                new_row_tmp += f'            <td>{{}}</td>\n'
                new_row_tmp += f'            <td style="width:{app_context.EDU_ITEM_PIXELS}; text-align:{{}}">{{}}</td>\n'
                new_row_tmp += f'            <td>{{}}</td>\n'
                new_row_tmp +=  '        </tr>\n'
                # row index,text_align,content,point

        self.content_row_template = new_row_tmp
        self.edu_template_file = Edu_Template_Files[index]
        self.config = config

        # Update layout and dialog size after all widgets are added
        self.config_layout.invalidate()
        self.config_layout.activate()
        self.dialog.adjustSize()

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
    
    def on_card_selected(self,widget:EduItemWidget):

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
        html = self.___generate_html_content__(selected_content)
        
        # Show PDF preview window
        self.___show_pdf_preview__(html)

    def ___validate_template__(self) -> bool:
        # Validate template file selection and existence
        if self.edu_template_file == '':
            PopupNotifier.Notify(self, 'Error', 'The output template has not selected.', background_color='RED')
            return False
        
        template_file = app_context.application_path + f'\\resources\\templates\\{self.edu_template_file}-Template.html'
        if not os.path.exists(template_file):
            PopupNotifier.Notify(self, 'Error', f'The template file not found in the specified path--> {template_file}')
            return False
            
        self.template_file = template_file
        return True
    

    def get_selected_contents(self):
        # Get selected cards and their content
        selected_content = []
        total_points = 0
        row = 0
        
        for card in self.card_grid.get_cards():
            data = card.get_data()
            if data['selected']:
                row += 1
                content = {
                    'Id':data['Id'],
                    'row': row,
                    'content': data['content'],
                    'score': float(data['score'])
                }
                selected_content.append(content)
                total_points += content['score']
        
        if selected_content:
            selected_content.append({'total_points': total_points})
            
        return selected_content

    def ___generate_html_content__(self, selected_content) -> str:
        """Generate HTML content with template placeholders replaced"""
        stream = open(self.template_file, encoding="utf-8",mode='r')
        stream.seek(0)
        html = stream.read()
        stream.close()
        language =app_context.Language
        
        # Replace content placeholders
        new_content_template = '<!-- NEW CONTENT -->'
        text_align = self.config[language]['Text align']
        
        for item in selected_content[:-1]:  # Skip last item (total_points)
            new_row = self.content_row_template.format(
                item['row'], 
                text_align,
                item['content'], 
                item['score']
            ) + new_content_template
            html = html.replace(new_content_template, new_row, count=1)

        # Replace dimension placeholders
        dimensions = {
            '-- 2.43 inches --': f'{2.43*app_context.DPI}px',
            '-- 2.42 Inches --': f'{2.42*app_context.DPI}px',
            '-- 0.54 Inches --': f'{0.54*app_context.DPI}px',
            '-- 6.19 Inches --': f'{app_context.EDU_ITEM_PIXELS}px',
        }

        for old, new in dimensions.items(): html = html.replace(old, new)

        # Replace style placeholders
        html = html.replace('-- font-family --', self.config[language]['Font family'])
        html = html.replace('-- direction --', self.config[language]['Direction'])
        html = html.replace('-- Text Alignment --', text_align)

        # Replace content placeholders
        replacements = {
            '-- In the name of God --': self.config[language]['InTheNameOfGod'],
            '-- Stu-Name --': self.stu_info_input.text(),
            '-- Stu-Id --': self.stu_id_input.text(),
            '-- Organisation Info --': self.org_info_input.toPlainText().replace('\n','<br>'),
            '-- Academic-Year-Term --': self.term_input.toPlainText().replace('\n','<br>'),
            '-- Date --': self.date_input.text(),
            '-- Teacher-Name --': self.teacher_input.text(),
            '-- Clock --': self.clock_input.text(),
            '-- Book-Grade --': self.book_grade_input.text(),
            '-- Field --': self.field_input.text(),
            '-- Time-Pages --': self.time_input.text(),
            '-- Index --': self.config[language]['Row'],
            '-- Edu-Content --': self.config[language]['Header'],
            '-- Point --': self.config[language]['Score'],
            '-- Author: Abdh --': self.author_input.text(),
            '-- SUM --': str(selected_content[-1]['total_points']),
            '-- FOOTER SUM --': self.config[language]['Footer sum']
        }
        
        for placeholder, value in replacements.items(): html = html.replace(placeholder, value)
            
        return html

    def ___show_pdf_preview__(self, html):
        """Show PDF preview window"""
        self.dialog.setModal(False)
        self.dialog.move(10, 10)
        
        window = PdfGeneratorApp(html_content=html, parent=self.dialog)
        window.setWindowModality(Qt.WindowModality.WindowModal)
        window.move(self.dialog.geometry().topRight() + QPoint(10, 0))
        window.show()
        
        self.dialog.setModal(True)

    ######################################################
    def load_data(self, filter: str = ''):
        self.card_grid.reset()  # clears grid, resets scroll
        self.current_page = 0
        self.has_more = True
        self.current_filter = filter
        
        # paginated data loading
        self.load_next_page(filter)  # load first page

    def load_next_page(self, filter_text):
        
        if not self.has_more: return
        # Use server-side cursor for streaming + low memory
        search = f"%{filter_text}%".strip()
        # Build safe parameterized query
        base_query  = "SELECT Id, content_description_, score_, source_, additional_details_ FROM educational_resources"
        where_parts = f"(source_ ILIKE '%{search}' OR content_description_ ILIKE '%{search}' "
        where_parts = f"{where_parts} OR additional_details_ ILIKE '%{search}' OR TEXT(Id) ILIKE '%{search}')"
                          
        where_clause = "WHERE " + where_parts if where_parts else ""

        order_by = "ORDER BY score_ DESC NULLS LAST, Id DESC"

        full_query = f"{base_query} {where_clause} {order_by}"

        # Start background worker
        worker = DataLoaderWorker(query=full_query, page=self.current_page, page_size=self.page_size)
            
        worker.signals.batch_ready.connect(self.on_batch_received)
        worker.signals.finished.connect(self.on_load_finished)
        worker.signals.error.connect(self.on_load_error)

        QThreadPool.globalInstance().start(worker)
        self.current_page += 1

    # To update the UI
    @Slot(list)
    def on_batch_received(self, rows):

        if rows:
            #self.card_grid.clear()
            # Add each HTML item to the list widget
            for record in rows:
                # Create a custom widget for the item
                edu_item = EduItemWidget(record, app_context.EDU_ITEM_PIXELS + 20,cursor=app_context.database)
                # Optional: card.clicked.connect(self.on_card_clicked)
                self.card_grid.add_card(record[0], edu_item)

    @Slot(int)
    def on_load_finished(self, count):
        self.card_grid.hide_loading_indicator()

        if count < self.page_size:
            self.has_more = False
            if self.card_grid.grid_layout.count() == 0:
                self.card_grid.show_empty_message("No results found.")
        else:
            self.has_more = True
            # Optional: show manual load button instead of auto-scroll
            self.card_grid.show_load_more_button()

    @Slot(str)
    def on_load_error(self, error_msg):
        self.card_grid.hide_loading_indicator()
        self.card_grid.show_empty_message(f"Error: {error_msg}")