
from datetime import datetime
#import dateutil as du
from PySideAbdhUI.Notify import PopupNotifier
from PySide6.QtGui import (Qt, QTextOption, QIcon, QAction, QPixmap, QImage)

from PySide6.QtWidgets import (QFileDialog, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QProgressBar,
                               QTextEdit, QDialogButtonBox,
                               QGridLayout, QWidget, QLabel,QApplication,QDialog, QMessageBox,
                               QPushButton, QHBoxLayout, QVBoxLayout, QPlainTextEdit, QMenu)
from PySideAbdhUI.Widgets import StackedWidget, Separator

from processing.Imaging.Tools import bytea_to_pixmap
from processing.text.text_processing import local_culture_digits
from services.edu_item_services import EduItemStudentService as edu_service
from utils import analysis
from ui.dialogs.answer_view import AnswerView
from ui.widgets.widgets import ObservedBehaviourWidget
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
        layout.addWidget(Separator()) # Row separator
        # A container for notes and behavioral text
        self.behav_list = QListWidget()
        # A contaner for educational items and learning conents
        self.quests_list = QListWidget()
        self.load_behav_data()
        # Go to the function and fix bugs(has unknown bug for the installed app)
        scaled_score, scores, items_status = self.load_quests_data()
        
        self.create_charts(header_layout, scaled_score, scores,items_status, each_row)
        
        # Header
        stacked_widget = StackedWidget()
        stacked_widget.setContentsMargins(5,0,5,0)
        stacked_widget.add_page(self.behav_list)
        stacked_widget.add_page(self.quests_list)
        
        commands = QHBoxLayout()
        commands.setContentsMargins(0,0,20,0)
        
        btn  = QPushButton('')
        btn.setIcon(QIcon(':icons/chevron-left.svg'))
        btn.setToolTip('Observed behaviours')
        btn.setProperty('class', 'grouped_mini')
        btn.clicked.connect(lambda _:(activities_lbl.setText('BEHAVIOURS'), stacked_widget.go_back()))
        commands.addWidget(btn)

        activities_lbl = QLabel('ACTIVITIES')
        activities_lbl.setProperty('class','title')
        commands.addWidget(activities_lbl)

        btn  = QPushButton('')
        btn.setIcon(QIcon(':icons/chevron-right.svg'))
        btn.setProperty('class', 'grouped_mini')
        btn.setToolTip('Activities')
        btn.clicked.connect(lambda _:(activities_lbl.setText('ACTIVITIES'), stacked_widget.go_next()))
        commands.addWidget(btn)
        
        commands.addStretch(1)

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
        
        commands.addWidget(btn)
        header_layout.addLayout(commands,5,0,1,6,alignment=Qt.AlignmentFlag.AlignRight)

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
        chart.setFixedSize(140, 135)
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
        chart.setFixedSize(140,135)
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
                
                
        except Exception as e: PopupNotifier.Notify(self,message= f"Error: {e}")

    def calc_total(self, scores:str=''):
        
            if not scores: return 0.0
        
            lst = scores.split('-')
            total = 0.0
        
            for val in lst:
                total+= float(val)
            return total
    
    def load_quests_data(self):
        
        earned_score = 0.0
        total_score  = 0.0
            
        replied = 0
        delayed = 0
        lost = 0
        has_time = 0

        score_progress = []
        today = datetime.now()

        self.quests_list.clear()
        
        cmd  = 'SELECT id, qb_ids_, total_score_, scores_, assign_date_, deadline_, reply_date_ FROM quests '
        cmd += 'WHERE student_id = %s ORDER BY assign_date_ DESC;'

        records = app_context.database.fetchall(cmd,(self.student[0],))
        #         quiz-Id: record[0],       source-ids: record[1],
        #     total-score: record[2],    earned-scores: record[3],
        #   assigned-date: record[4],         deadline: record[5],  reply-date: record[6]
        
        for row, record in enumerate(records):
            
            status = '' # Options for each quiz (Replied, Waiting, Lost) 
            # Sum of earned scores for all activities
            earned_score = self.calc_total(record[3])
            total_score  = float(record[2]) if record[2] else 1.0
            
            deadline: datetime = record[5]            
            
            # If still has not replied
            if record[6] == None:
                # currently has time to reply
                if today <= deadline: 
                    has_time += 1
                    status = 'Waiting'
                else: 
                    # the time passed and student has not replied at 
                    # this status the score is considered, and is assigned to zero
                    lost += 1
                    status = 'Lost'
                    # Earned score  divided by max score
                    score_progress.append(record[3]/record[2])
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
                score_progress.append(earned_score/total_score)
            
            item_grid = QGridLayout() # For each row
            # Column 0: Row index | quiz-id
            string = f'<div>{row + 1}<br>{record[0]}</div>'
            col0 = QLabel(string)
            col0.setToolTip('Row index\nQuiz-Id')
            col0.setTextFormat(Qt.TextFormat.RichText)

            # Column 1: The time when quiz assigned to student
            string = f'<div>Assign date : {record[4]}<br>Deadline : {record[5]}<br>Total score : {total_score}</div>'
            col1 =QLabel(string)
            col1.setTextFormat(Qt.TextFormat.RichText)           

            # Column 2
            string = f'<div>Status : {status}<br>Relpy : {record[6]}<br>Earned score : {earned_score}</div>'
            col2 =QLabel(string)
            col2.setTextFormat(Qt.TextFormat.RichText)
            
            # Column 3: the donut of the earned score
            bytes_ = analysis.create_donut_image(earned_score, total_score)
            image = QImage.fromData(bytes_)

            chart = QLabel()
            chart.setToolTip(f'Earbed score:\n{earned_score} of {total_score}')
            chart.setFixedSize(90, 85)
            chart.setContentsMargins(5,5,5,5)
            chart.setPixmap(QPixmap.fromImage(image))
            chart.setScaledContents(True)

            # Column 4: Actions    
            view_btn = QPushButton('')
            #view_btn.setVisible(False)
            view_btn.setIcon(QIcon(':icons/eye.svg'))
            view_btn.setProperty('class','grouped_mini')
            view_btn.setToolTip('Opens a window to display complete data of the quiz')
            # data 
            data = {'student': f'{self.student[1]} {self.student[2]}', # To display on the output report
                    'qb_ids':record[1],                                # To fetch quiz content from question bank
                    'quiz-id':record[0],                               # To fetch and update answer data in the quests table
                    'asign-date': str(record[4]),                      # To display on the output report
                    'reply-date': str(record[6])                       # To display on output report and modify.
                    }
            
            view_btn.clicked.connect(lambda _, d = data : self.open_activity_item(d))

            """ans_btn = QPushButton('')
            #ans_btn.setVisible(False)
            ans_btn.setIcon(QIcon(':icons/pencil.svg'))
            ans_btn.setProperty('class','grouped_mini')
            ans_btn.setToolTip('Opens a window to modify the answer of the quiz received from the student.')
            ans_btn.clicked.connect(lambda _,id= record[0]: self.__create_answer_input_dlg(quiz_id=id))"""
            # add delete button
            del_btn   = QPushButton('')
            del_btn.setIcon(QIcon(':icons/trash-2.svg'))
            del_btn.setProperty('class','grouped_mini')

            actions_ = QVBoxLayout()
            actions_.setContentsMargins(0,0,0,0)
            actions_.setSpacing(0)
            actions_.addWidget(view_btn)
            actions_.addWidget(del_btn)

            actions_container = QWidget()
            actions_container.setLayout(actions_)
            actions_container.setFixedWidth(30)
            actions_container.setVisible(False)
            
            item_grid.setColumnMinimumWidth(4,35)
            
            item_grid.addWidget(col0,  0, 0, Qt.AlignmentFlag.AlignVCenter)    
            item_grid.addWidget(col1,  0, 1) # Assign date
            item_grid.addWidget(col2,  0, 2) # Status label
            item_grid.addWidget(chart, 0, 3, Qt.AlignmentFlag.AlignCenter)
            item_grid.addWidget(actions_container, 0, 4, Qt.AlignmentFlag.AlignTop)
            item_grid.addWidget(Separator(),0,0,1,5,Qt.AlignmentFlag.AlignBottom) # Row separator

            item_grid.setColumnStretch(1,1)      # Stretch the column
            item_grid.setColumnStretch(2,1)      # Stretch the column
            item_grid.setColumnStretch(3,1)      # Stretch the column

            item_widget = QWidget()
            item_widget.setLayout(item_grid)
            list_item = QListWidgetItem()
            
            list_item.setSizeHint(item_widget.sizeHint())
            
            self.quests_list.addItem(list_item)
            self.quests_list.setItemWidget(list_item,item_widget)
        
        self.quests_list.currentItemChanged.connect(self.on_current_item_changed)
        
        if len(records) == 0:
            total_score = 1
            score_progress =[0]
        
        return earned_score/total_score*20, score_progress, (replied, has_time, delayed, lost)

    def on_current_item_changed(self, current:QListWidgetItem, previous:QListWidgetItem):

        if previous:
            widget = self.quests_list.itemWidget(previous)      
            item_grid = widget.layout()                        
                                
            container_item = item_grid.itemAtPosition(0, 4)
            if container_item:
                container = container_item.widget()      
                container.setVisible(False)         
        
        if current:
            widget = self.quests_list.itemWidget(current)      
            item_grid = widget.layout()                        
                                
            container_item = item_grid.itemAtPosition(0, 4)
            if container_item:
                container = container_item.widget()       
                container.setVisible(True)         
            
            current.setSizeHint(widget.sizeHint())

    # Opens answer viewer for activity
    def open_activity_item(self, data=None):

        # Create the window – it starts loading automatically
        self.answer_window = AnswerView(data, parent=self)
#        self.answer_window.setWindowModality(Qt.WindowModality.WindowModal)
        self.answer_window.exec()
   
    def __create_answer_input_dlg(self, quiz_id):

        dlg = QDialog(self)
        dlg.setWindowTitle("Answer Details")
        dlg.resize(920, 400)
        layout = QVBoxLayout(dlg)
        
        layout.addWidget(QLabel('ANSWER'))
        answer_input = QTextEdit()
        answer_input.setPlaceholderText('Load answer of the student here or write manully ...')
        answer_input.setAcceptRichText(True)
        layout.addWidget(answer_input)

        layout.addWidget(QLabel(r'ANALYSIS & FEEDBACK'))
        analysis_input = QTextEdit()
        analysis_input.setPlaceholderText('add analytic explanation about replied answer')
        analysis_input.setFixedHeight(100)
        
        layout.addWidget(analysis_input)

        ans_footer = QHBoxLayout()
        ans_footer.addWidget(QLabel('Score:'))
        score_input = QLineEdit()
        score_input.setPlaceholderText('0.0')
        ans_footer.addWidget(score_input)

        ans_footer.addWidget(QLabel("Replied at:"))
        date_input = QLineEdit()
        date_input.setPlaceholderText('YYYY-MM-dd HH:mm:ss')
        date_input.setMinimumWidth(200)
        ans_footer.addWidget(date_input)

        ans_footer.addStretch(1)
        
        load_answer_btn = QPushButton('Load answer')
        ans_footer.addWidget(load_answer_btn)
        menu = QMenu(load_answer_btn)
        menu.addAction('Plain text',lambda sender= answer_input, arg= app_context.SupportedFileTypes.TEXT: self.upload_file(sender=sender,arg=arg))
        menu.addAction('RTF',lambda sender= answer_input,arg= app_context.SupportedFileTypes.RTF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Image' ,lambda sender= answer_input, arg=app_context.SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg))
        menu.addAction('PDF',lambda sender= answer_input, arg=app_context.SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Html',lambda sender= answer_input,arg=app_context.SupportedFileTypes.HTML: self.upload_file(sender=sender,arg=arg))

        load_answer_btn.setMenu(menu)
        
        save_button = QPushButton('Save')

        save_button.clicked.connect(lambda _, id=quiz_id,
                                    answer= answer_input, 
                                    feedback= analysis_input, 
                                    score=score_input, date=date_input: 
                                    self.save_answer(quiz_id=id, answer_input=answer, 
                                                     feedback_input=feedback,
                                                     score_input=score, 
                                                     date_input=date))
    
        ans_footer.addWidget(save_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda _, Id=quiz_id,
                                    answer= answer_input, 
                                    feedback= analysis_input, 
                                    score=score_input, date=date_input:
                                    self.delete_answer(Id=Id, answer_input=answer, 
                                                     feedback_input=feedback,
                                                     score_input=score, 
                                                     date_input=date))
                                     
        ans_footer.addWidget(delete_button)

        close_btn = QPushButton('Close')
        close_btn.clicked.connect(dlg.reject)
        ans_footer.addWidget(close_btn)

        layout.addLayout(ans_footer)
        # load old data
        query = 'SELECT scores_, reply_date_, responses_, feedback_ FROM quests WHERE Id = %s;'
        data = app_context.database.fetchone(query,(quiz_id,))

        if data:
            answer_input.document().setHtml(data[2])
            analysis_input.document().setHtml(data[3])
            score_input.setText(str(self.calc_total(data[0])))
            date_input.setText(str(data[1]))

        dlg.exec()
        
    def delete_answer(self, Id, answer_input:QTextEdit, feedback_input:QTextEdit, score_input:QLineEdit, date_input:QLineEdit):

        button = QMessageBox.warning(self,'DELETE RECORD','ARE YOU SURE TO DELETE THE ANSWER ?', 
                                     QMessageBox.StandardButton.Ok, 
                                     QMessageBox.StandardButton.Cancel)
        
        if button == QMessageBox.StandardButton.Cancel: return

        result = edu_service.update_learning_item(self, Id=Id, answer='', feedback='', score= 0.0, reply_date=str(datetime.now()))
        
        if result[0]:
            answer_input.document().clear()
            feedback_input.document().clear()
            score_input.setText('')
            date_input.setText('')
        
        PopupNotifier.Notify(self,message=f'{result[1]}')

    def save_answer(self, quiz_id, answer_input:QTextEdit, feedback_input:QTextEdit, score_input:QLineEdit, date_input:QLineEdit):
        
        if answer_input.document().toPlainText() == '' or score_input.text() == '' or date_input.text() == '':
            PopupNotifier.Notify(self,message='Invalid data, the answer does not updated')
            return
        
        
        result = edu_service.update_learning_item(self, 
                                            Id=quiz_id,
                                            answer=answer_input.document().toHtml(),
                                            feedback= feedback_input.document().toHtml(),
                                            score= float(score_input.text()),
                                            reply_date= date_input.text())

        PopupNotifier.Notify(self,message= f'{result[1]}')
        
    def upload_file(self,sender:QTextEdit, arg:str=app_context.SupportedFileTypes.IMAGE):
        
        # Open a file dialog to upload an image or PDF.
        file_dialog = QFileDialog(self)
        filter = app_context.FileTypes[arg]

        file_dialog.setNameFilter(filter)
        
        if file_dialog.exec():
        
            file_path = file_dialog.selectedFiles()[0]

            # avilable widh for edu-content is 6.19 inches
            if arg == app_context.SupportedFileTypes.IMAGE: 

                pixmap = QPixmap(file_path)
                from processing.Imaging.Tools import pixmap_to_base64
                from processing.utils.image_tools import pdf_to_base64
                base64_image = pixmap_to_base64(pixmap)

                html_content = f'<img src="data:image/png;base64,{base64_image}" width="{app_context.A4_PIXELS}"/>'
                
                sender.document().clear()
                sender.document().setHtml(html_content)

            elif arg == app_context.SupportedFileTypes.PDF:
                sender.document().clear()
                base64s = pdf_to_base64(file_path)
                html_content = f'<img src="data:image/png;base64,{base64s[0]}" width="{app_context.A4_PIXELS}"/>'
                # Set the HTML content in the QTextEdit
                sender.setHtml(html_content)
            
            #elif arg == app_context.SupportedFileTypes.RTF:

            #    html = pypandoc.convert_file(file_path, "html")
        
            #    sender.document().setHtml(html)

            elif arg in [app_context.SupportedFileTypes.TEXT, app_context.SupportedFileTypes.HTML]:
                
                sender.document().clear()
                with open(file_path, 'r',encoding="utf-8") as file: data = file.read()
                sender.document().setHtml(data)
    

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
                
        action1 = QAction(text='Update',parent=menu)
        action1.triggered.connect(lambda _, Id= Id, behaviour_widget= behaviour_plain_text, 
                                                    analysis_widget= analysis_plain_text:
                                                    self.edit_behaviour_note(Id, behaviour_widget, analysis_widget))
        menu.addAction(action1)

        action2 = QAction(text='Remove',parent =menu)
        action2.triggered.connect(lambda _,index = row, Id=Id: self.delete_behaviour_note(record_Id=Id,record_index=index))
                
        menu.addAction(action2)
        layout.addWidget(btn,0,1,1,1,Qt.AlignmentFlag.AlignRight)
                
        return widget
    
    def toggle_analysis_inputs(self, widget:QWidget): widget.adjustSize()
        
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


