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
import re
#import pypandoc
from PySide6.QtCore import Signal, QPoint

from PySide6.QtGui import (QFont, QIcon, QPixmap, Qt,QStandardItemModel, QStandardItem)

from PySide6.QtWidgets import ( QFileDialog, QFontComboBox, QFrame, QGridLayout, QScrollArea, QSizePolicy, QTabWidget, QVBoxLayout, 
                               QWidget, QLabel,QApplication,QDialog, QListView, QMessageBox,
                               QPushButton, QHBoxLayout, QLineEdit,QAbstractItemView,
                               QPlainTextEdit, QComboBox, QAbstractScrollArea,QMenu,QWidgetAction,)

from PySideAbdhUI.Notify import PopupNotifier
import dateutil
from ui.widgets.masonry_view import Card, MasonryView
from PySideAbdhUI.Documents.document_editor import RichTextEditor
from PySideAbdhUI.Widgets import SearchBox, Separator

from core.app_context import app_context
from utils.assessment_helper import (replace_placeholders, unpack_block, unwrap_page_divs,
                                     Edu_Template_Files, assessment_row_template, NEW_CONTENT_PLACEHOLDER)

###################################################################


class EduResourcesView(QWidget):
    
    def __init__(self,parent=None, target_students=[dict]):

        super().__init__(parent)

        self.initalized = False
        self.templates_created = False
        self._answer_loaded = False
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
        
        self.main_layout.addWidget(header_widget) 
        
        self.setup_tabwidgets()
        
        self.tabs.setCurrentIndex(0)

        self.initalized = True

        self.load_data()
    

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

        self.template_cmb.setCurrentIndex(0)
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

        self.doc_view = RichTextEditor()
        layout.addWidget(self.doc_view)
        
        container = QWidget()
        self.config_layout = QVBoxLayout(container)
        self.config_layout.setContentsMargins(5,0,5,0)
        self.template_cmb = QComboBox()
        self.template_cmb.setPlaceholderText('-- Select a template --')
        self.template_cmb.addItems(['Classroom quiz','Formal exam'])
            
        self.config_layout.addWidget(self.template_cmb)

        self.template_cmb.currentIndexChanged.connect(self.on_template_param_changed)

        content_scroll = QScrollArea()
        content_scroll.setFixedWidth(250)
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_scroll.setWidget(container)

        layout.addWidget(content_scroll)

        # Config layout creation
                
        self.org_info_input = QPlainTextEdit('')
        self.org_info_input.setFixedHeight(100)
        self.org_info_input.document().setDefaultTextOption(Qt.AlignmentFlag.AlignCenter)
        self.org_info_input.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.config_layout.addWidget(self.org_info_input)

        self.teacher_input = QLineEdit('')
        self.config_layout.addWidget(self.teacher_input)

        self.title_input = QLineEdit('')
        self.config_layout.addWidget(self.title_input)

        self.field_input = QLineEdit('')
        self.config_layout.addWidget(self.field_input)

        self.academic_year_input = QLineEdit('')
        self.config_layout.addWidget(self.academic_year_input)

        self.term_input = QLineEdit('')
        self.config_layout.addWidget(self.term_input)

        self.date_input = QLineEdit('')
        self.config_layout.addWidget(self.date_input)

        self.time_input = QLineEdit('')
        self.config_layout.addWidget(self.time_input)    
        self.duration_input = QLineEdit('')
        self.config_layout.addWidget(self.duration_input)

        btn = QPushButton('  Reload')
        btn.setIcon(QIcon(":icons/refresh-ccw"))
        btn.clicked.connect(self.on_template_param_changed)
        

        self.config_layout.addWidget(btn)
        self.config_layout.addStretch()
    
    def applyFont(self, font):
        self.doc_view.applyGlobalValue('font-family',font)
        self.font_family = font
       
    def applyDirection(self, dir):
        self.doc_view.applyGlobalValue('dir',dir,is_property=False)
        self.page_direction = dir
        
    def create_corner_commands(self):
        
        w = QWidget()
        w.setVisible(False)
        w.setFixedHeight(38)
        hlayout = QHBoxLayout(w)
        hlayout.setContentsMargins(0,0,0,10)
        hlayout.setSpacing(2)

        self.lang_cmb = QComboBox()
        self.lang_cmb.setPlaceholderText('-- Select a language --')
        self.lang_cmb.addItems(['فارسی','English'])
        self.lang_cmb.setToolTip("Language for the assessment writing")
        self.lang_cmb.setCurrentIndex(0)
        
        hlayout.addWidget(self.lang_cmb)


        fontCombo = QFontComboBox()
        fontCombo.setFixedWidth(100)
        fontCombo.setFontFilters(QFontComboBox.FontFilter.AllFonts)
        fontCombo.setCurrentFont(QFont("Arial",12))  # default font
        fontCombo.setToolTip('System installed fonts')
        fontCombo.currentFontChanged.connect(lambda f:self.applyFont(f.family()))
        hlayout.addWidget(fontCombo)
        

        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('Left to Right direction')
        btn.clicked.connect(lambda: self.applyDirection('ltr'))
        btn.setIcon(QIcon(":icons/pilcrow-right.svg"))
        
        hlayout.addWidget(btn)

        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('Right to Left direction')
        btn.clicked.connect(lambda: self.applyDirection('rtl'))
        btn.setIcon(QIcon(":icons/pilcrow-left.svg"))
        
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
        btn.setToolTip('Refresh the page to apply config changes')
        btn.setIcon(QIcon(":icons/refresh-ccw"))
        btn.clicked.connect(self.on_template_param_changed)
            
        hlayout.addWidget(btn)

 
        btn = QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('send assessment to the students and store in database.')
        btn.setIcon(QIcon(":/icons/send.svg"))
        hlayout.addWidget(btn)
        btn.clicked.connect( self.create_distribution_options)
        
        btn= QPushButton('')
        btn.setProperty('class','mini')
        btn.setToolTip('save current assessment on the disk and publish. this method does not store the assessment in the database')
        btn.clicked.connect(lambda: self.doc_view.LoadFileDialog(caption="Save File", dialog_type='save'))
        btn.setIcon(QIcon(":icons/save.svg"))
        
        hlayout.addWidget(btn)

        self.tabs.setCornerWidget(w,Qt.Corner.TopRightCorner)
    
    def _toggle_corner_widgets(self, index):

        self.tabs.cornerWidget(Qt.Corner.TopRightCorner).setVisible(index == 1)

        if index == 1: self.on_template_param_changed()

    def get_deadline(self): 

        start = self.date_input.text().strip() + ' ' + self.time_input.text().strip()

        dur = self.duration_input.text().strip()
        try:
            return dateutil.parser.parse(start) + timedelta(minutes=int(dur))
        
        except Exception as e:
            PopupNotifier.Notify(self,'',f'{e}')
        
    def create_distribution_options(self):
        
        # Create the dialog window.
        dialog = QDialog(self)
        # Set dialog caption.
        dialog.setWindowTitle("DISTRIBUTE")

        dist_options_layout = QVBoxLayout(dialog) 
        
        date_start = self.date_input.text().strip()
        time_start = self.time_input.text().strip()
        duration   = self.duration_input.text().strip()
        
        deadline_ = self.get_deadline()
        dist_options_layout.addWidget(QLabel(f'Title: {self.title_input.text().strip()}'))
        dist_options_layout.addWidget(Separator())
        dist_options_layout.addWidget(QLabel(f'Start: {date_start} {time_start}'))
        dist_options_layout.addWidget(QLabel(f'Duration:{duration}'))
        dist_options_layout.addWidget(QLabel(f'End:{deadline_}'))
        dist_options_layout.addWidget(Separator())
        dist_options_layout.addWidget(QLabel('Send to:'))
        
        stu_list = QListView(self)
        stu_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        
        model = QStandardItemModel()

        for item in self.target_students:
            new_item = QStandardItem(f'{item['Name']}\n{item['Id']}')
            model.appendRow(new_item)

        stu_list.setModel(model)
        
        dist_options_layout.addWidget(stu_list, Qt.AlignmentFlag.AlignTop)

        btn4 = QPushButton('   Send')
        btn4.setIcon(QIcon(":/icons/send.svg"))
        btn4.setEnabled(model.rowCount()>0)
        btn4.clicked.connect(self.distribute)

        dist_options_layout.addWidget(btn4)
        dialog.exec()

    def distribute(self):
        '''Distributes selected edu-items to the students'''
        
        # When students has not been specified, we try to publish an assessment as html file.
        if len(self.target_students) == 0:
            PopupNotifier.Notify(self,"", "No student specified yet.")
            return 
        
        if not self.current_selection: 
            PopupNotifier.Notify(self,'SEND','No Edu-Item selected.')
            return

        try:
            stu_cnt = len(self.target_students)
            sel  = len(self.current_selection)
            msg  = f'Number of {sel} edu-item{'s' if sel>1 else ''} will be assigned to {stu_cnt} student{'s' if stu_cnt>1 else ''}\n'
            msg += 'are you sure?'

            if QMessageBox.StandardButton.Cancel == QMessageBox.question(self,'',msg, 
                                                                         QMessageBox.StandardButton.Yes, 
                                                                         QMessageBox.StandardButton.Cancel): 
                return
            
            # Get current UTC time
            utc_time = self.date_input.text().strip()

            future_time = self.get_deadline()
            total_score  =0.0
            config = str({"Template": self.config['template'],
                          "Language": "Persian" if self.lang_cmb.currentIndex() == 0 else 'English',
                          "Font-family":self.font_family,
                          "Page direction": self.page_direction,
                          "Teacher": self.teacher_input.text(),
                          "Org-Info":self.org_info_input.toPlainText(),
                          "Title": self.title_input.text(), 
                          "Field": self.field_input.text(), 
                          "Academic Year":self.academic_year_input.text(), 
                          "Term":self.term_input.text(),
                          "Time":self.time_input.text(),
                          "Duration":self.duration_input.text(),
                        })
            
            config = config.replace("'","\"")

            for stu in self.target_students: 
                qb_IDs = ''
                # List of Edu-Items: last index was included sub totlal values
                for item in self.current_selection: 
                    qb_IDs += str(item['Id']) +'-'
                    total_score += float(item["score"])


                cmd = 'INSERT INTO quests(student_id, qb_ids_, assign_date_, deadline_, total_score_, configs_, reply_date_, scores_, responses_, feedback_) '
                    
                cmd += 'VALUES(%s, %s, %s,%s, %s, %s, %s, %s, %s, %s)'
        
                values = (stu['Id'], qb_IDs[:-1], str(utc_time), str(future_time),total_score, config, None, None, None, None)

                app_context.database.execute(cmd,values)
                
            msg  = f'Number of {sel} edu-item{'s' if sel>1 else ''} was assigned to {stu_cnt} student{'s' if stu_cnt>1 else ''} successfully'
                
            PopupNotifier.Notify(self,'',msg)
            
        except Exception as e: PopupNotifier.Notify(self,'',f'Database error: {e}.')

    def on_template_param_changed(self):

        if self.lang_cmb.currentIndex()<0: return

        # index 0: فارسی, index 1: English
        self.page_language =  'Persian' if self.lang_cmb.currentIndex() == 0 else 'English'

        if self.template_cmb.currentIndex()<0: return

        index = self.template_cmb.currentIndex()

        # index: "01-Quiz", "02-Formal-Exam"
        # Index of template selction combobox        
        config_filepath = os.path.join(app_context.resource_path,f'templates\\{Edu_Template_Files[index]}-config.json')
        
        app_context.template_config.set_path(config_filepath)

        config = app_context.template_config.read()

        config = config[self.page_language]
        # Values: "01-Quiz", "02-Formal-Exam"
        config["template"] = Edu_Template_Files[index]

        self.teacher_input.setPlaceholderText(config['Teacher'])
        self.date_input.setPlaceholderText(f"{config['Date']}: --/--/--")
        self.time_input.setPlaceholderText(f"{config['Time']}: --:--")
        self.title_input.setPlaceholderText(config['Title'])
        self.duration_input.setPlaceholderText(f'{config['Duration']} --- {config['Time Unit']}')

        if index == 1:
            self.org_info_input.setPlaceholderText(config['Organization Info']) # Formal              
            self.field_input.setPlaceholderText(config['Field'])          # Formal
            self.academic_year_input.setPlaceholderText(config['Academic Year'])         # Formal
            self.term_input.setPlaceholderText(config['Term'])
      
        # Classroom quiz has been selected, hide formal exam fields
        self.teacher_input.setVisible(index == 1)
        self.org_info_input.setVisible(index == 1)
        self.field_input.setVisible(index == 1)
        self.term_input.setVisible(index == 1)
        self.academic_year_input.setVisible(index==1)
        
        # Store configs to use  in the table generation process
        self.config = config

        #if(index == 1):
        # Generates full question table
        main_table, styles = self._generate_html_content()
        # dir = "rtl" is default, user can change it.
        main_table = f'<div class="page" contenteditable="false" dir="rtl">{main_table}</div>'
        self.doc_view.clearContent()
            
        self.doc_view.copy_content(content= main_table, custom_styles= styles,editable= False)

    
    # the selected_content will be removed
    def _generate_html_content(self) -> str:

        # Generate HTML content with template placeholders replaced
        # Read template file 01-Quiz-template.html or 02-Formal-Exam-Template.html
        template_file = os.path.join(app_context.resource_path, f'templates\\{self.config['template']}-Template.html')
        
        with open(template_file, encoding="utf-8",mode='r') as f: html = f.read()
        
        styles = []
        total_score = 0.0
        row = 0
        self.current_selection = []

        for card in self.masonry_view.cards:
            widget:LearningItemWidget = card.widget
            data = widget.data
            
            if widget.is_selected:

                self.current_selection.append(data)
                
                total_score += data['score']
                new_style, new_content = unpack_block(data["content"])
                # Removes open/close of style tag.
                new_style = new_style.replace("<style>","")
                new_style = new_style.replace("</style>","")
                # Join all styles
                styles.append(new_style)
                # remove all div with class="page" apen/close part
                # and return pure content
                new_content = unwrap_page_divs(new_content)
                # data cleaning
                new_content = new_content.replace("\n","")
                
                # Generate new row for the table, this table is contains list of questions
                # format matching data: row index,text_align,content,point
                # this format is selected on template-changed event
                new_row = assessment_row_template.format(row + 1, new_content, data['score'])
                new_row = new_row + NEW_CONTENT_PLACEHOLDER
                # Inject this row to the html body
                html = html.replace(NEW_CONTENT_PLACEHOLDER, new_row, count=1)
                row += 1
        
        data = {'Student':"",
                'Student Id':"",
                'Teacher': self.teacher_input.text(),
                'Title':self.title_input.text(),
                'Date':self.date_input.text(),
                'Time':self.time_input.text(),
                'Duration':self.duration_input.text(),
                'Total Score':str(total_score),
                'Template':self.config['template'],
                'Org-Info':self.org_info_input.toPlainText(),
                'Academic Year':self.academic_year_input.text().strip(),
                'Term':self.term_input.text(),
                'Field':self.field_input.text().strip()}
        
        html = replace_placeholders(html,self.config,  data)

        return html, "\n".join(styles)

    def _create_data_dict(self, Id, source:str, content:str,answer:str, metadata:str,score:float):
        
        return {"Id":Id,
                "source":source,
                "content":content,
                "answer":answer,
                "metadata":metadata,
                "score":score}

    def _on_answer_requested(self,sender:LearningItemWidget):

        r = self.rect()
        p = r.topLeft()
        py = 10 # titlebar height/2
        px = (r.width())/4
        point = self.mapToGlobal(p + QPoint(px,py))
        
        if sender.info_panel:
           sender.info_panel.exec(point)
           return

        Id = sender.data['Id']

        try:
            
            data = app_context.database.fetchone(f'SELECT answer_, metadata_ FROM educational_resources WHERE Id = {Id};')
            
            if data[0] == '' or not data[0]:
                PopupNotifier.Notify(self,'','No answer provided yet!')
                return
            
            sender.data['answer'] = data[0]
            sender.data['metadata'] = data[1]

            info_panel = QVBoxLayout()
            header_info = QLabel(f"{sender.data["Id"]} | {sender.data["source"]} | {sender.data["score"]}")

            header_info.setToolTip("Id | source | score")

            info_panel.addWidget(header_info, alignment=Qt.AlignmentFlag.AlignLeft)
               
            ans_view = RichTextEditor(default_size="Edu-Item")
            ans_view.setFixedWidth(app_context.A4_PIXELS + 50)
            ans_view.setFixedHeight(280)
            styles, content = unpack_block(sender.data['answer'])
            
            ans_view.copy_content(content, styles)
            
            info_panel.addWidget(ans_view)
            info_panel.addSpacing(5)
            
            details_input = QPlainTextEdit()
            details_input.setPlaceholderText("add here comment or analytical points")
            details_input.setMaximumHeight(80)
            details_input.setPlainText(sender.data["metadata"])
            
            info_panel.addWidget(details_input)
            
            footer_widget = QWidget()
            footer_layout = QHBoxLayout(footer_widget)
            
            footer_layout.addStretch(1)

            btn_menu_close = QPushButton('Close')
            footer_layout.addWidget(btn_menu_close)

            update_details_btn = QPushButton('Update')
            update_details_btn.setToolTip("Only update comment or analytical points")
            
            footer_layout.addWidget(update_details_btn,alignment=Qt.AlignmentFlag.AlignRight)

            info_panel.addWidget(footer_widget)

            info_widget = QWidget()
            info_widget.setLayout(info_panel)

            # Create a QMenu: this menu must be bind to 'More Info button on the header of Edu-Item'
            info_panel_menu = QMenu(sender.titlebar)
            # Create a QWidgetAction to hold custom widgets
            widget_action = QWidgetAction(sender.titlebar)
            # Set the widget to the QWidgetAction
            widget_action.setDefaultWidget(info_widget)
            # Add the QWidgetAction to the menu
            info_panel_menu.addAction(widget_action)
            
            info_panel_menu.setFixedHeight(500)

            btn_menu_close.clicked.connect(info_panel_menu.close)

            sender.info_panel = info_panel_menu

            sender.info_panel.exec(point)

        except Exception as e:
            print('Error:',e)

    
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
                viewer = RichTextEditor(default_size="Edu-Item")
                
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

    def _on_viewer_loaded(self, ok: bool,card:Card, sender:RichTextEditor):
        
        if ok:
            sender.toggle_scroll_visibility(False)
        
            szF = sender.getComputedSizeAsync()

            sender.setFixedHeight(szF.height())
            
            card.setFixedSize(int(szF.width())+5, int(szF.height()+42))

            self.loaded_count+=1

            if self.loaded_count == self.data_count: self.masonry_view.update_view()


class LearningItemWidget(QWidget):
    # emit Id of the learnig Item(Like Id of the question record in the database)
    on_answer_requested = Signal(QWidget) 
    
    def __init__(self, parent=None, data:dict={}):

        super().__init__(parent)

        self.info_panel:QMenu= None
        self.titlebar_created = False

        self.data = data
    
        if data == {}:
            self.data = {"Id":0, "source":"", "content":"", "answer":"", "metadata":"", "score":0.0}
        
        self.data["user-selected"] = False
            
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
            ans_mnu_btn.clicked.connect(lambda:self.on_answer_requested.emit(self))

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
    

    def _update_metadata(self,Id, value):

        app_context.database.execute(f"UPDATE educational_resources SET metadata_ = '{value}' WHERE Id = {Id};")
        self.data["metadata"] = value
        PopupNotifier.Notify(self, "", "Metadata updated.")
       
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
