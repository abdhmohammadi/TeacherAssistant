
from datetime import datetime
from PySideAbdhUI.Notify import PopupNotifier
from PySide6.QtGui import (Qt, QTextOption, QIcon, QAction, QPixmap, QImage)

from PySide6.QtWidgets import (QListWidget, QListWidgetItem,
                               QTextEdit, QDialogButtonBox,
                               QGridLayout, QWidget, QLabel,QApplication,QDialog, QMessageBox,
                               QPushButton, QHBoxLayout, QVBoxLayout,
                               QPlainTextEdit, QMenu)
from PySideAbdhUI.Widgets import StackedWidget, Separator

from processing.Imaging.Tools import bytea_to_pixmap
from processing.text.text_processing import local_culture_digits
from utils import analysis
from processing.text import text_processing
from ui.widgets.widgets import EduItemStudentWidget, ObservedBehaviourWidget
from ui.pages.edu_resource_view import EduResourcesView
from core.app_context import app_context

class StudentActivityTrackingPage(QWidget):
    
    def __init__(self,student):
        super().__init__()
        self.student = student
    
        self.initUI()
    # QVLayout in root,
    # Top row of root is hosted of 'QGridLayout' and shows identical info, and activity analysis charts
    # Second is the container of 'StackedWidget' to dispaly behavioral data and activities in tow pages
    def initUI(self):

        each_row = 40
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        # returns QGrid 5x2
        header_layout = self.init_StudentInfoUI()
        
        layout.addLayout(header_layout)

        # A container for notes and behavioral text
        self.behav_list = QListWidget()
        # A contaner for educational items and learning conents
        self.quests_list = QListWidget()
        
        self.load_behav_data()

        scaled_score, scores, items_status = self.load_quests_data()
        
        self.create_charts(header_layout, scaled_score, scores,items_status, each_row)
        
        # header : 5x5
        stacked_widget = StackedWidget()
        stacked_widget.setContentsMargins(5,0,5,0)
        stacked_widget.add_page(self.behav_list)
        stacked_widget.add_page(self.quests_list)
        
        btn  = QPushButton('')
        btn.setIcon(QIcon(':icons/chevron-left.svg'))
        btn.setToolTip('Observed behaviours')
        btn.setProperty('class', 'grouped_mini')
        btn.clicked.connect(stacked_widget.go_back)
        header_layout.addWidget(btn, 5,0,alignment=Qt.AlignmentFlag.AlignLeft)

        btn  = QPushButton('')
        btn.setIcon(QIcon(':icons/chevron-right.svg'))
        btn.setProperty('class', 'grouped_mini')
        btn.setToolTip('Activities')
        btn.clicked.connect(stacked_widget.go_next)
        header_layout.addWidget(btn,5,0,alignment=Qt.AlignmentFlag.AlignRight)

        activities_lbl = QLabel('Activity and behaviours')
        activities_lbl.setProperty('class','title')
        header_layout.addWidget(activities_lbl,5,1,1,2)

        commands = QHBoxLayout()
        commands.setContentsMargins(0,0,20,0)
        btn = QPushButton('')
        btn.setIcon(QIcon(':icons/printer.svg'))
        btn.setToolTip('Export data')
        btn.setProperty('class','grouped_mini')
        menu = QMenu(btn)
        btn.setMenu(menu)

        action1 = QAction(text= 'Activities',parent=menu)
        action1.setEnabled(False)
        #action1.triggered.connect(lambda _, data=record: self.open_behaviour_list_page(data))
        menu.addAction(action1)

        action2 = QAction(text= 'Behavioral observations',parent=menu)
        #action1.triggered.connect(lambda _, data=record: self.open_behaviour_list_page(data))
        menu.addAction(action2)
        action2.setEnabled(False)
        #btn.clicked.connect(lambda: self.add_behaviour_note(data=None))
        commands.addWidget(btn)

        btn = QPushButton('')
        btn.setIcon(QIcon(':icons/pencil-line.svg'))
        btn.setToolTip('Add new behaviour note')
        btn.setProperty('class','grouped_mini')
        btn.clicked.connect(lambda: self.add_behaviour_note(data=None))

        commands.addWidget(btn)

        btn = QPushButton('')
        btn.setIcon(QIcon(':icons/drafting-compass.svg'))
        btn.setToolTip('New Edu-Item')
        btn.setProperty('class','grouped_mini')
        btn.clicked.connect(lambda _, stu={'Id':self.student[0],'Name':f'{self.student[1]}  {self.student[2]}'}:
                                      self.assign_edu_to_student(stu))
        
        #header_layout.addWidget(btn,5,6)
        commands.addWidget(btn)
        header_layout.addLayout(commands,5,3,1,3,alignment=Qt.AlignmentFlag.AlignRight)

        header_layout.addWidget(Separator(stroke=2, color='#3D3D3D'),5, 0, 1, header_layout.columnCount(),alignment=Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(stacked_widget)

    # Initalizes the given grid layout with 5 rows and 2 columns
    # the rows and columns is used to set personal data fields
    def init_StudentInfoUI(self):

        layout = QGridLayout()
        layout.setSpacing(2)
        # Third Column: Photo and Buttons
        photo_label = QLabel()
        photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_label.setText("No Photo Uploaded")
        # Set photo box dimensions to the formal size (35mm x 45mm ≈ 138x177 pixels at 96 DPI)
        photo_label.setFixedSize( 128 , 140)
        photo_label.setStyleSheet("border: 1px solid #888888; border-radius: 8px; padding:4px; margin:0px 10px 0px 10px")
        
        pixmap = bytea_to_pixmap(self.student[5])
        # Scale the photo to fill the entire photo box (ignore aspect ratio)
        scaled_pixmap = pixmap.scaled(photo_label.size(), 
                                              Qt.AspectRatioMode.IgnoreAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
        photo_label.setPixmap(scaled_pixmap)
        photo_label.setText("")
        
        layout.addWidget(photo_label, 0, 0, 4, 1)  # Span across 5 rows and 1 column
        layout.setAlignment(photo_label,Qt.AlignmentFlag.AlignTop)

        student_id = QLabel(local_culture_digits(self.student[0],language=app_context.Language))
        layout.addWidget(student_id,4,0, alignment=Qt.AlignmentFlag.AlignTop| Qt.AlignmentFlag.AlignHCenter)

        # Name of the student
        name = QLabel(f'{self.student[1]} {self.student[2]}')
        name.setProperty('class','subtitle')
        layout.addWidget(name, 0, 1,alignment=Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        # Phone number 
        phone_label = QLabel(local_culture_digits(self.student[3],language=app_context.Language))
        layout.addWidget(phone_label, 1,1,alignment=Qt.AlignmentFlag.AlignLeft)

        # Parent/Guardian Name
        parent_name_input = QLabel(self.student[8])
        layout.addWidget(parent_name_input, 2, 1,alignment=Qt.AlignmentFlag.AlignLeft)
        # Parent/Guardian Phone
        parent_phone_label = QLabel(local_culture_digits(self.student[9],language=app_context.Language))

        layout.addWidget(parent_phone_label, 3, 1,alignment= Qt.AlignmentFlag.AlignLeft)
        
        return layout
    
    def create_charts(self, header_layout:QGridLayout,scaled_score:float, scores:list, items_status:tuple[int,int,int,int], row_height):
        # When we fetch the data from the database, that is ordered DESC
        # so to generate time-series of data, we need reverse the order. 
        #
        # The scaled_score is a list of earned points that is scaled between [0,1]
        scores.reverse()
        # x_values just is 1, 2, 3, ...
        x_values = list(range(1, 1 + len(scores)))
        bytes_ = analysis.create_line_chart_image(x_values, scores)
        image = QImage.fromData(bytes_)

        chart = QLabel()
        chart.setToolTip('Changes in scores obtained so far.')
        chart.setFixedSize(283, 170)
        chart.setPixmap(QPixmap.fromImage(image))
        chart.setScaledContents(True)
        header_layout.addWidget(chart,0,2,5,1,alignment= Qt.AlignmentFlag.AlignCenter)
        header_layout.setColumnStretch(2,1)

        # Create donut 1
        scaled_score = round(scaled_score,2)
        bytes_ = analysis.create_donut_image(scaled_score, 20)
        image = QImage.fromData(bytes_)

        chart = QLabel()
        chart.setToolTip('Cumulative score: Cumulative score: The sum of all scores obtained so far, converted to a 20-point scale.')
        chart.setFixedSize(140, 140)
        chart.setContentsMargins(0,0,0,0)
        chart.setPixmap(QPixmap.fromImage(image))
        chart.setScaledContents(True)
        header_layout.addWidget(chart,0,3,4,1,alignment= Qt.AlignmentFlag.AlignCenter)
        header_layout.setColumnStretch(3,1)

        lbl = QLabel('Cumulative')
        header_layout.addWidget(lbl,4,3,alignment= Qt.AlignmentFlag.AlignCenter)
        # create donut 2
        avg = round(sum(scores)/len(scores)*20,2) if len(scores)>0 else 0
        bytes_ = analysis.create_donut_image(avg, 20)
        image = QImage.fromData(bytes_)

        chart = QLabel()
        chart.setToolTip('Average score: The average of the scores obtained so far, converted to a 20-point scale.')
        chart.setFixedSize(140,140)
        chart.setContentsMargins(0,0,0,0)
        chart.setPixmap(QPixmap.fromImage(image))
        chart.setScaledContents(True)
        header_layout.addWidget(chart,0,4,4,1,alignment= Qt.AlignmentFlag.AlignCenter)
        header_layout.setColumnStretch(4,1)
        lbl = QLabel('Average')
        header_layout.addWidget(lbl,4,4,alignment= Qt.AlignmentFlag.AlignCenter)
        
        bytes_ = analysis.create_pie_chart(values= items_status,
                                           labels=[f'Replied({items_status[0]})', f'Waiting({items_status[1]})',
                                                   f'Delayed({items_status[2]})', f'Lost({items_status[3]})'],ncol=2)
        image = QImage.fromData(bytes_)

        chart = QLabel()
        chart.setToolTip(app_context.ToolTips['Activity status'])
        chart.setFixedSize(145, 140)
        chart.setContentsMargins(0,0,0,0)
        chart.setPixmap(QPixmap.fromImage(image))
        chart.setScaledContents(True)
        header_layout.addWidget(chart,0,5,5,1,alignment= Qt.AlignmentFlag.AlignHCenter| Qt.AlignmentFlag.AlignTop)
        header_layout.setColumnStretch(5,1)
        lbl = QLabel('Activity status')
        
        header_layout.addWidget(lbl,4,5, alignment= Qt.AlignmentFlag.AlignCenter)

    def assign_edu_to_student(self,stu:dict):
        
        window = QApplication.activeWindow()
        window.add_page(EduResourcesView(window,[stu]))
        
    def edit_behaviour_note(self,record_id, behaviour_widget:QPlainTextEdit, analysis_widget:QPlainTextEdit):
        
        new_behaviour = behaviour_widget.toPlainText()
        new_analysis  = analysis_widget.toPlainText()

        if new_analysis or new_behaviour:
            try:
                query  = 'UPDATE observed_behaviours SET observed_behaviour_=%s, analysis_=%s WHERE Id=%s;'
                
                #cursor = TeacherAssistant.db_connection.cursor()

                app_context.database.execute(query, (new_behaviour,new_analysis,record_id))
                msg = 'Content updated.'
            
            except Exception as e:
                msg = f'Database error: {e}.'

        PopupNotifier.Notify(self,"Message",msg)   
        
    # Target: Adding new note to database about the current pereson
    # Opens a QDailog and takes behaviour note and teacher's analysis
    def add_behaviour_note(self,data=None):

        #editor_type = 'UPDATE' if data else 'INSERT'
        dialog = QDialog(parent=self)
        
        dialog.setWindowTitle('ADD BEHAVIOUR')
        dialog.setMinimumWidth(800)
        dialog.setMaximumWidth(800)
        dialog.setMaximumHeight(400)
        
        row_box = QVBoxLayout()
        row_box.addWidget(QLabel('OBSERVED BEHAVIOUR:'))
        # Adds the behaviour note to edit or accept new note
        behaviuor_input = QTextEdit(data[3] if data else '')
        row_box.addWidget(behaviuor_input)

        row_box.addWidget(QLabel('TEACHER ANALYSIS:'))
        analysis_input = QTextEdit(data[4] if data else '')
        row_box.addWidget(analysis_input)
        
        # Create a QDialogButtonBox with OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.button(QDialogButtonBox.Ok).setText("Save")
        button_box.button(QDialogButtonBox.Cancel).setText("Reject")
        # Connect the buttons to the dialog's accept and reject slots
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        # Add the button box to the layout
        row_box.addWidget(button_box)
        
        dialog.setLayout(row_box)
        dialog.exec()

        if dialog.accepted:

            behaviuor = behaviuor_input.toPlainText()
            analysis  = analysis_input.toPlainText()

            if behaviuor or analysis:
                # save data
                query  = 'INSERT INTO observed_behaviours(date_time_, student_id, observed_behaviour_, analysis_)'
                query += 'VALUES (%s, %s, %s,%s) RETURNING Id;'
                now = datetime.now()
                #cursor = TeacherAssistant.db_connection.cursor()
                id = app_context.database.fetchone(query, (now, self.student[0], behaviuor, analysis))

                widget =  self.___create_observed_note_widget(0, id, now, behaviuor, analysis)

                list_item = QListWidgetItem()
                list_item.setSizeHint(widget.sizeHint())
                self.behav_list.insertItem(0, list_item)
                self.behav_list.setItemWidget(list_item, widget) 

                msg ='New behaviour note saved for ' + self.student[1] + ' ' + self.student[2]

                PopupNotifier.Notify(self,"Message",msg, delay=3000)
    

    def load_behav_data(self):
        
        try:
            self.behav_list.clear()

            cmd  = "SELECT Id, date_time_, observed_behaviour_, analysis_ " 
            cmd += "FROM observed_behaviours WHERE student_id =\'" +self.student[0]+"\' "
            cmd += "ORDER BY date_time_ DESC;"
            
            records = app_context.database.fetchall(cmd)
            
            for row, record in enumerate(records):

                widget = self.___create_observed_note_widget(row, record[0], record[1], record[2], record[3])
                
                list_item = QListWidgetItem()
                #widget.adjustSize()
                list_item.setSizeHint(widget.sizeHint())
                self.behav_list.addItem(list_item)
                self.behav_list.setItemWidget(list_item, widget) 
                
                
        except Exception as e: print(f"Error: {e}")

    def load_quests_data(self):
        
            self.quests_list.clear()
            cmd  = 'SELECT quests.id, quests.max_point_, quests.earned_point_, quests.assign_date_, '
            cmd += 'quests.deadline_, quests.answer_, quests.reply_date_, quests.feedback_ , '
            cmd += 'educational_resources.content_description_ '
            cmd += 'FROM quests LEFT JOIN educational_resources '
            cmd += 'ON quests.qb_id = educational_resources.id WHERE quests.student_id = %s '
            cmd += 'ORDER BY quests.assign_date_ DESC;'

            records= app_context.database.fetchall(cmd,(self.student[0],))
            # Id: record[0], max-score: record[1], earned-score: record[2]
            # assigned-date: record[3], deadline: record[4], answer: record[5] -> long html text
            # reply-date: record[6], feedback: record[7], main-content: record[8] -> long html text
            #all_quests = len(records)
            earned_score = 0.0
            total_score = 0.0 
            
            replied = 0
            delayed = 0
            lost = 0
            has_time = 0

            score_progress = []
            today = datetime.now()

            for row, record in enumerate(records):
                # Sum of earned scores for all activities
                earned_score += float(record[2])
                total_score  += float(record[1])

                deadline: datetime = record[4]
                status = ''
                # If still has not replied
                if record[6] == None:
                    # currently has time to reply
                    if today <= deadline: 
                        has_time += 1
                        status = 'Waiting'
                    else: 
                        # the time passed and student has not replied
                        # at this status the score is considered, and is assigned to zero
                        lost += 1
                        status = 'Lost'
                        # zero score: record[2] is zero
                        score_progress.append(record[2]/record[1])
                else:  
                    # The answer has replied    
                    reply:datetime = record[6]
                    # The activity has been replied befer deadline ended
                    if reply <= deadline: 
                        replied +=1
                        status = 'Replied'
                    # The activity has been replied after deadline ended(delayed)
                    else: 
                        delayed += 1
                        status = 'Delayed'
                    # stores the score for the progress chart
                    score_progress.append(record[2]/record[1])
                
                answer  = text_processing.get_html_body_content(record[5])
                feedback = text_processing.get_html_body_content(record[7])

                item = EduItemStudentWidget(record[0], record[8], answer, feedback, record[1],
                                                    record[2], record[3], record[4], record[6], status)
                
                item.data_updated.connect(lambda _, message :PopupNotifier.Notify(self,'', message))

                # User need to confirm delete of item
                # this signal emited after ContentRemoved signal in the hosted model 
                item.delete_executed.connect(lambda _, message:(
                                             self.quests_list.takeItem(row), 
                                             PopupNotifier.Notify(self,'', message)))

                list_item = QListWidgetItem()
        
                list_item.setSizeHint(item.sizeHint())
        
                self.quests_list.addItem(list_item)
                self.quests_list.setItemWidget(list_item, item)

            if len(records) == 0:
                total_score = 1
                score_progress =[0]

            return earned_score/total_score*20, score_progress, (replied, has_time, delayed, lost)

        
    def ___create_observed_note_widget(self, row, Id, date, observed, analysis):
        
                widget = QWidget()
                layout = QGridLayout(widget)

                observed_label = QLabel(str(Id)+ ' | Observed behaviour | ' + str(date.strftime("%Y-%m-%d %H:%M:%S"))+'')
                observed_label.setProperty('class','caption')
                
                layout.addWidget(observed_label,0,0)

                behaviour_plain_text = QPlainTextEdit()
                behaviour_plain_text.setPlainText(observed)
                behaviour_plain_text.setReadOnly(True)  # Disable editing if not needed
                behaviour_plain_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
                behaviour_plain_text.setFixedHeight(100)
                
                layout.addWidget(behaviour_plain_text,1,0,1,2)
                
                analysis_label = QLabel('Teacher analysis:')
                analysis_label.setProperty('class','caption')
                #analysis_label.hide()
                
                layout.addWidget(analysis_label,2,0)

                analysis_plain_text = QPlainTextEdit()
                analysis_plain_text.setPlainText(analysis)
                #analysis_plain_text.hide()
                analysis_plain_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
                analysis_plain_text.setFixedHeight(100)
                
                layout.addWidget(analysis_plain_text,3,0,1,2)
                
                btn = QPushButton('')            
                btn.setIcon(QIcon(':icons/menu.svg'))
                btn.setProperty('class','grouped_mini')
                menu = QMenu(btn)
                
                btn.setMenu(menu)
                
                """action0 = QAction(text='Enabel feedback',parent=menu)
                action0.triggered.connect(lambda:(
                                analysis_label.setVisible( not analysis_label.isVisible()),
                                analysis_plain_text.setVisible(not analysis_plain_text.isVisible()),
                                widget.setFixedSize(layout.sizeHint())
                            ))
                menu.addAction(action0)
                """
                action1 = QAction(text='Update',parent=menu)
                action1.triggered.connect(lambda _, Id= Id,
                                                    behaviour_widget= behaviour_plain_text, 
                                                    analysis_widget= analysis_plain_text:
                                                self.edit_behaviour_note(Id, behaviour_widget, analysis_widget))
                menu.addAction(action1)

                action2 = QAction(text='Remove',parent =menu)
                action2.triggered.connect(lambda _,index = row, Id=Id: self.delete_behaviour_note(record_Id=Id,record_index=index))
                
                menu.addAction(action2)
                layout.addWidget(btn,0,1,1,1,Qt.AlignmentFlag.AlignRight)
                
                return widget
    
    def toggle_analysis_inputs(self, widget:QWidget):
            widget.adjustSize()
        
    def delete_behaviour_note(self, record_Id, record_index):
        
        try:# drop data
            button = QMessageBox.warning(self,'DELETE RECORD','ARE YOU SURE TO DELETE THE RECORD ?',QMessageBox.StandardButton.Ok,QMessageBox.StandardButton.Cancel)
            if not button == QMessageBox.StandardButton.Ok : return

            query  = 'DELETE FROM observed_behaviours WHERE student_Id=%s AND Id =%s;'
            
            app_context.database.execute(query, (self.student[0],record_Id))
            
            self.behav_list.takeItem(record_index) # Remove from list 
            msg = 'The note with Id ' + str(record_Id) + ' removed from database.'   
                    
        except Exception as e:
            msg = f'Database Error: {e}'
    
        PopupNotifier.Notify(self,"Message",msg, 'bottom-right', delay=3000, background_color='#353030',border_color="#2E7D32")
        
    # conected to top-right Button
    def open_behaviour_note_editor(self,data):

        self.dialog = QDialog(parent=self)
        self.dialog.setWindowTitle('OBSERVED BEHAVIOUR EDITOR')
        self.dialog.setMinimumWidth(800)
        self.dialog.setMaximumWidth(800)
        self.dialog.setMaximumHeight(500)
        student_info_form = ObservedBehaviourWidget(profile_data=data,parent=self.dialog)
        
        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(student_info_form)
    
        # Set the layout for the dialog
        self.dialog.setLayout(layout)
        self.dialog.exec()

