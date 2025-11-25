
import sys
import psycopg2
#import pypandoc
from psycopg2 import sql
from datetime import datetime

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (QDialog,QHBoxLayout, QVBoxLayout, QMenu, QWidgetAction, QProgressBar, QSizePolicy,
                               QFormLayout, QFrame, QWidget, QMessageBox,QTextEdit, QPlainTextEdit, QApplication,
                               QGridLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QScrollArea) 

from Imaging.Tools import pixmap_to_base64, bytea_to_pixmap

import TeacherAssistant
from TeacherAssistant import ToolTips
from TeacherAssistant.utils import text_processing
from TeacherAssistant.utils import database_tools
from TeacherAssistant.utils.image_tools import pdf_to_base64
from TeacherAssistant.view_models import EduItems as views
from TeacherAssistant.models import EduItems as models
from TeacherAssistant import SupportedFileTypes, FileTypes, state

from PySideAbdhUI.Notify import PopupNotifier
from PySideAbdhUI.Widgets import Label



class ObservedBehaviourWidget(QWidget):
    
    def __init__(self,db_cursor, profile_data=None, parent=None):
        super().__init__()
        self.db_cursor = db_cursor
        self.parent = parent
        self.data_modified = False
        self.profile_data = profile_data
        self.initUI()

    def initUI(self):
        # Set golden color palette
        # Main layout
        grid_layout = QGridLayout(self)
        grid_layout.setSpacing(2)
        # Window settings
        self.setWindowTitle("Student Information Form")

        # Remove the maximize and minimize buttons
        self.setWindowFlags(self.windowFlags() & Qt.WindowType.WindowCloseButtonHint)
        # First Column: First Name, Last Name, Student ID
        self.first_name_label = QLabel("First Name:")
        self.first_name_input = QLabel(self.profile_data[1])
        grid_layout.addWidget(self.first_name_label, 0, 0)
        grid_layout.addWidget(self.first_name_input, 0, 1)

        self.last_name_label = QLabel("Last Name:")
        self.last_name_input = QLabel(self.profile_data[2])
        grid_layout.addWidget(self.last_name_label, 1, 0)
        grid_layout.addWidget(self.last_name_input, 1, 1)

        self.student_id_label = QLabel("Student ID:")
        self.student_id_input = QLabel(self.profile_data[0])
        grid_layout.addWidget(self.student_id_label, 2, 0)
        grid_layout.addWidget(self.student_id_input, 2, 1)

        # Second Column: Date of Birth, Gender, Phone
        self.dob_label = QLabel("Date of Birth:")
        self.dob_input = QLabel('YYYY-MM-DD')
        grid_layout.addWidget(self.dob_label, 0, 2)
        grid_layout.addWidget(self.dob_input, 0, 3)

        self.gender_label = QLabel("Gender:")
        self.gender_input = QLabel()
        grid_layout.addWidget(self.gender_label, 1, 2)
        grid_layout.addWidget(self.gender_input, 1, 3)

        self.phone_label = QLabel("Phone:")
        self.phone_input = QLabel(self.profile_data[3])
        grid_layout.addWidget(self.phone_label, 2, 2)
        grid_layout.addWidget(self.phone_input, 2, 3)

        # Third Column: Photo and Buttons
        self.photo_label = QLabel()
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_label.setText("No Photo Uploaded")

        # Set photo box dimensions to the formal size (35mm x 45mm ≈ 138x177 pixels at 96 DPI)
        photo_width = 138  # Width of the photo box
        photo_height = 177  # Height of the photo box
        self.photo_label.setFixedSize(photo_width, photo_height)

        self.photo_label.setStyleSheet("""QLabel { border: 2px dashed #D4AF37; border-radius: 8px; padding:5px;}""")
        # photo data has loaded in 5 column and must be displayed on first column
        pixmap = bytea_to_pixmap(self.profile_data[5])
        # Scale the photo to fill the entire photo box (ignore aspect ratio)
        self.photo_label.setPixmap(pixmap)
        self.photo_label.setScaledContents(True)
        self.photo_label.setText("")

        grid_layout.addWidget(self.photo_label, 0, 4, 5, 1)  # Span across 3 rows and 1 column
        grid_layout.setAlignment(self.photo_label,Qt.AlignmentFlag.AlignTop)
        
        # Address (stretched across 2 columns)
        self.address_label = QLabel("Address:")
        self.address_input = QLabel()
        self.address_input.setText('bojnord')
        grid_layout.addWidget(self.address_label, 3, 0)
        grid_layout.addWidget(self.address_input, 3, 1, 1,3)  # Span across 1 row and 2 columns

        # Parent/Guardian Name
        self.parent_name_label = QLabel("Parent Name:")
        self.parent_name_input = QLabel()
        grid_layout.addWidget(self.parent_name_label, 4, 0)
        grid_layout.addWidget(self.parent_name_input, 4, 1)

        # Parent/Guardian Phone
        self.parent_phone_label = QLabel("Parent Phone:")
        self.parent_phone_input = QLabel()
        grid_layout.addWidget(self.parent_phone_label, 4, 2)
        grid_layout.addWidget(self.parent_phone_input, 4, 3)

        # Add a horizontal separator 
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #D4AF37; margin:2px 0px 0px 5px;")
        grid_layout.addWidget(line,5,0,1,5,alignment=Qt.AlignmentFlag.AlignBottom)
        # Additional Details Section
        self.observed_behaviour_label = QLabel("Observed behaviour:")
        self.observed_behaviour_input = QTextEdit()

        self.observed_behaviour_input.setPlaceholderText("Enter additional details (e.g., medical conditions, special needs)...")
        grid_layout.addWidget(self.observed_behaviour_label, 5, 0)
        grid_layout.addWidget(self.observed_behaviour_input, 6, 0, 1, 5)  # Span across 1 row and 5 columns

        # Additional Details Section
        self.teacher_analysis_label = QLabel("Teacher analysis:")
        self.teacher_analysis_input = QTextEdit()
        self.teacher_analysis_input.setPlaceholderText("Analysis by teacher")
        grid_layout.addWidget(self.teacher_analysis_label, 7, 0)
        grid_layout.addWidget(self.teacher_analysis_input, 8, 0, 1, 5)  # Span across 1 row and 5 columns

        # Buttons layout (Clear Form, Submit, Close Form)
        self.clear_form_button = QPushButton("Clear")
        self.clear_form_button.clicked.connect(self.clear_form)
        grid_layout.addWidget(self.clear_form_button, 9, 0)

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit_form)
        grid_layout.addWidget(self.submit_button, 9, 3)

        self.close_form_button = QPushButton("Close")
        self.close_form_button.clicked.connect(self.close_form)
        grid_layout.addWidget(self.close_form_button, 9, 4)
     
    def clear_form(self):
        # Clear all input fields
        self.teacher_analysis_input.clear()
        self.observed_behaviour_input.clear()
    
    def close_form(self):
        self.parent.close()  # Close the form window

    def submit_form(self):

        student_id = self.student_id_input.text()
        obeh = self.observed_behaviour_input.toPlainText()
        ta = self.teacher_analysis_input.toPlainText()
        now = datetime.now()
        
        # Insert personal information into the table
        insert_query = sql.SQL('INSERT INTO observed_behaviours(date_time_,student_id, observed_behaviour_, analysis_)'
                               + 'VALUES (%s, %s, %s,%s)')

        self.db_cursor.execute(insert_query, (now,student_id,obeh,ta))
        # Commit the transaction
        # Here you can add code to process the form data (e.g., save to database, etc.)
        QMessageBox.information(self, "Success", "Student information submitted successfully!")
        self.data_modified = True

        # Function to convert QPixmap to binary data


 
class PostgreSqlConnectionWidget(QObject):
    
    def __init__(self,host='localhost',port='5432',database='',user='postgres',password='9875123N'):
        
        super().__init__()

        self.connection = None
        self.dialog = QDialog()
        # Set the window flags properly
        self.dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint| Qt.WindowType.FramelessWindowHint)
        self.dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Optional: auto delete when closed

        layout = QVBoxLayout(self.dialog)

        # Create an inner background container
        background = QWidget(self.dialog)
        background.setProperty('class',"surface-background-layer")
        layout.addWidget(background)


        # Form layout inside the container
        self.form_layout = QFormLayout(background)
        background.setContentsMargins(15, 5, 15, 15)
        # Add form fields
        self.host_field = QLineEdit()
        self.host_field.setText(host)
        
        self.port_field = QLineEdit()
        self.port_field.setText(port)

        self.database_field = QLineEdit()
        self.database_field.setText(database)

        self.user_field = QLineEdit()
        self.user_field.setText(user)

        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setText(password)

        self.form_layout.addWidget(QLabel('<b>CONNECT TO PostgreSQL DATABASE</b>'))
        self.form_layout.addRow("Host:", self.host_field)
        self.form_layout.addRow("Port:", self.port_field)
        self.form_layout.addRow("Database:", self.database_field)
        self.form_layout.addRow("User:", self.user_field)
        self.form_layout.addRow("Password:", self.password_field)


        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_database)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close_dialog)
        
        self.commands_layout = QHBoxLayout()
        self.commands_layout.addStretch(1)
        self.commands_layout.addWidget(self.cancel_button)
        self.commands_layout.addWidget(self.connect_button)
        self.form_layout.addRow(self.commands_layout)
        self.dialog.setLayout(layout)
    
    def close_dialog(self): self.dialog.close()
    
    def create_database(self):
        
        self.host = self.host_field.text()
        self.port = self.port_field.text()
        self.database = self.database_field.text()
        self.user = self.user_field.text()
        self.password = self.password_field.text()

        connection = psycopg2.connect(host=self.host, 
                                      port=self.port, 
                                      database= 'postgres',
                                      user=self.user,
                                      password=self.password)
        
        if connection:

            status, msg = database_tools.create_database(connection, database= self.database)
            
            if not status: 
                QMessageBox.warning(self,'',msg)
                return
            
            status, connection, msg = database_tools.change_database_in_session(connection,self.database,self.password)
            
            if not status:
                QMessageBox.warning(self,'',msg)    
                return
            
            status, msg= database_tools.initialize_database(connection)
            
            if not status:
                QMessageBox.warning(self,'',msg)    
                return
            
            
            TeacherAssistant.db_connection = connection
            # Enable autocommit mode
            TeacherAssistant.db_connection.autocommit = True

            self.dialog.hide()


    def connect_to_database(self):
        
        self.host = self.host_field.text()
        self.port = self.port_field.text()
        self.database = self.database_field.text()# postgres
        self.user = self.user_field.text()
        self.password = self.password_field.text()
        
        try:
  
            connection = psycopg2.connect(host=self.host, port=self.port, database= self.database, user=self.user, password=self.password)
            
            if connection:
                if connection.status == 1: # STATUS_READY
                    TeacherAssistant.db_connection = connection
                    
                    self.dialog.close()
        
        except Exception as e:

            QMessageBox.critical(self, "Error", f"Failed to connect to database,\nError: {e}")
       
    def show_dialog(self):

        self.dialog.resize(550, 250)
        self.dialog.setMaximumSize(550,250)
        self.dialog.setMinimumWidth(550)
        
        self.dialog.exec()

        # this part is executed after the dialog is closed
        if TeacherAssistant.db_connection:
            
            TeacherAssistant.db_connection.autocommit = True

            host = '' if self.host is None else self.host
            port = '' if self.port is None else self.port
            database = '' if self.database is None else self.database
            user = '' if self.user is None else self.user
            password = '' if self.password is None else self.password
            settings_list = [('host',host),('port',port),('database',database),('user',user),('password',password)]
            # Create a dictionary with the list elements as key-value pairs under 'connection'
            connection_settings = {"connection": dict(settings_list)}
            status = True
        else:
            connection_settings = None
            status = False

        return status, connection_settings


class EduItemStudentWidget(QWidget):

    data_updated     = Signal(bool,str)
    delete_executed  = Signal(bool, str)
    
    def __init__(self, id:int =0, main_content='', answer='', feedback ='', 
                 total_score:float = 1.0, earned_score:float = 0.0, 
                 sent_date:datetime=None, deadline:datetime=None, received_date ='',status =''):
        
        super().__init__()

        self.viewModel = views.EduItemStudentViewModel(models.EduItemStudentModel(TeacherAssistant.db_connection.cursor()))

        # Init UI values
        self.viewModel.set_data(id, main_content, answer, feedback, earned_score, total_score, sent_date, deadline, received_date)
        
        self.viewModel.ContentUpdated.connect(self.data_updated)

        self.viewModel.ContentRemoved.connect(self.delete_executed)
        
        # Create a layout for the item with no margins or spacing
        main_layout = QGridLayout(self)
        
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)                 
        background_layer = QWidget()
        background_layer.setProperty('class', 'EduItem')
        background_layer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(background_layer,0,0,2,1)

        main_layout.setSpacing(5)

        header = QHBoxLayout()
        header.setContentsMargins(5,5,5,5)
        title = QLabel(f'{id} | Total Score: {total_score}')
        title.setProperty('class','caption')
        header.addWidget(title)
        
        header.addStretch(1)

        title = QLabel(f' Assign time: {sent_date} | End time: {deadline} | {status}   ')
        title.setProperty('class','caption')
        header.addWidget(title)

        main_layout.addLayout(header,0,0)

        main_content_label = Label()
        # Bind UI elements to ViewModel properties
        main_content_label.setWordWrap(True) 
        main_content_label.setTextFormat(Qt.TextFormat.RichText)
        main_content_label.setProperty('class','EduText')
        self.viewModel.bind_property("content", main_content, main_content_label)
        
        # Wrap the label in a scroll area with a limited height so content is scrollable when it overflows
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_scroll.setWidget(main_content_label)
        content_scroll.setFixedHeight(150)  # adjust height as needed

        # adding to row 1, column 0
        main_layout.addWidget(content_scroll,1,0)

        answer_input = QTextEdit()
        answer_input.setPlaceholderText('Load answer of the student here ...')
        answer_input.setAcceptRichText(True)
        self.viewModel.bind_property("response", answer, answer_input)
        
        main_layout.addWidget(answer_input,2,0)
        
        ans_footer = QHBoxLayout()
        ans_footer.addWidget(QLabel('Score:'))
        self.earn_input = QLineEdit()
        self.viewModel.bind_property("score", str(earned_score), self.earn_input)
        ans_footer.addWidget(self.earn_input)

        ans_footer.addWidget(QLabel("Replied at:"))
        self.received_date_input = QLineEdit()
        self.viewModel.bind_property("reply_date", str(received_date), self.received_date_input)
        ans_footer.addWidget(self.received_date_input)

        save_button = QPushButton("Save")

        save_button.clicked.connect(self.viewModel.save)
        
        ans_footer.addWidget(save_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda _: self.delete_request())

        ans_footer.addWidget(delete_button)
        
        try:
            if status.lower() =='waiting':
                # time range
                range = int((deadline - sent_date).total_seconds()/3600)
                # passed time
                passed = int((datetime.now() - sent_date).total_seconds()/3600)
                
                progress_bar = QProgressBar(minimum=0, maximum=range, value=passed)
                progress_bar.setTextVisible(False)

                tip =f'Time allocated to relpy: {range} hours({int(range/24)} day{'' if int(range/24)<=1 else 's'})\n'
                tip += f'Elapsed time: {passed} hours({int(passed/24)} day{'' if int(passed/24)<=1 else 's'})\n'
                tip += f'Time remaining: {range - passed} hours({round((range - passed)/24,2)} day{'' if int((range - passed)/24)<=1 else 's'})'
                progress_bar.setToolTip(tip)
                g = QGridLayout()
                g.setSpacing(0)
                g.setContentsMargins(0,0,0,8)
                lbl = QLabel(f'Time elapsed: {passed}H - Time remaining: {range- passed}H')
                lbl.setProperty('class','caption')

                g.addWidget(lbl,0,0,alignment=Qt.AlignmentFlag.AlignJustify)
                g.addWidget(progress_bar,1,0)

                ans_footer.addLayout(g,stretch=1)
                
        except Exception as e: print(f'Error:{e}')

        ans_footer.addStretch(1)
        
        load_answer_btn = QPushButton('Load answer')
        ans_footer.addWidget(load_answer_btn)
        menu = QMenu(load_answer_btn)
        menu.addAction('Plain text',lambda sender= answer_input, arg= SupportedFileTypes.TEXT: self.upload_file(sender=sender,arg=arg))
        menu.addAction('RTF',lambda sender= answer_input,arg= SupportedFileTypes.RTF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Image' ,lambda sender= answer_input, arg=SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg))
        menu.addAction('PDF',lambda sender= answer_input, arg=SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Html',lambda sender= answer_input,arg=SupportedFileTypes.HTML: self.upload_file(sender=sender,arg=arg))

        load_answer_btn.setMenu(menu)
        
        main_layout.addLayout(ans_footer,3,0)

        self.analysis_input = QTextEdit()
        self.analysis_input.setPlaceholderText('add analytic explanation about replied answer')
        self.analysis_input.setFixedHeight(100)
        self.viewModel.bind_property('feedback',feedback,self.analysis_input)
        main_layout.addWidget(self.analysis_input,4,0)
    
    
    def delete_request(self):
        
        button = QMessageBox.warning(self,'DELETE RECORD','ARE YOU SURE TO DELETE THE RECORD ?',
                                         QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.Cancel)
            
        if not button == QMessageBox.StandardButton.Ok : return

        self.viewModel.remove()


    def upload_file(self,sender:QTextEdit, arg:str=SupportedFileTypes.IMAGE):
        
        # Open a file dialog to upload an image or PDF.
        file_dialog = QFileDialog(self)
        filter = FileTypes[arg]

        file_dialog.setNameFilter(filter)
        
        if file_dialog.exec():
        
            file_path = file_dialog.selectedFiles()[0]

            # avilable widh for edu-content is 6.19 inches
            if arg == SupportedFileTypes.IMAGE: 

                pixmap = QPixmap(file_path)
                
                base64_image = pixmap_to_base64(pixmap)

                html_content = f'<img src="data:image/png;base64,{base64_image}" width="{state.A4_PIXELS}"/>'
                
                sender.document().clear()
                sender.document().setHtml(html_content)

            elif arg == SupportedFileTypes.PDF:
                sender.document().clear()
                base64s = pdf_to_base64(file_path)
                html_content = f'<img src="data:image/png;base64,{base64s[0]}" width="{state.A4_PIXELS}"/>'
                # Set the HTML content in the QTextEdit
                sender.setHtml(html_content)
            
            #elif arg == SupportedFileTypes.RTF:

            #    html = pypandoc.convert_file(file_path, "html")
        
            #    sender.document().setHtml(html)

            elif arg in [SupportedFileTypes.TEXT, SupportedFileTypes.HTML]:
                
                sender.document().clear()
                with open(file_path, 'r',encoding="utf-8") as file: data = file.read()
                sender.document().setHtml(data)
 

# A Widget for view layer(as list item)
class EduItemWidget(QWidget):
    
    bookmark_created = False
    titlebar_created = False
    info_panel_created = False

    def __init__(self, data= None, width= 400, parent=None):
        # Id: data[0], content:data[1], score: data[2]
        # source: data[3], additional_details: data[4]
        super().__init__(parent)
        
        self.svg_path = 'TeacherAssistant\\resources\\icons\\svg'
        self.setFixedWidth(width)
        
        self._view_model = views.EduItemViewModel() 
        # Init UI values
        self.set_model_data(data)
        
        self.initUI()

        self.update_view()

    def initUI(self):
        
        # Create a layout for the item with no margins or spacing
        main_layout = QGridLayout(self)

        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)                 
        background_layer = QWidget()
        background_layer.setProperty('class', 'EduItem')
        background_layer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(background_layer,0,0,2,1)

        self.titlebar = self.create_titlebar()

        main_layout.addWidget(self.titlebar,0,0,1,1)

        # Create a QLabel for the HTML content
        self.content_label = QLabel()   # HTML content in second column 
        self.content_label.setWordWrap(True)        
        self.content_label.setTextFormat(Qt.TextFormat.RichText)
        self.content_label.setProperty('class','EduText')
        self.content_label.setText(self._view_model.content)
        # Add the content label to the layout
        main_layout.addWidget(self.content_label,1,0,1,1, Qt.AlignmentFlag.AlignTop)


    def update_view(self):

        # Bind ViewModel properties to UI elements
        info = str(self._view_model.Id)
        info += '<br>Source: ' + self._view_model.source +'<br><b>Score:</b>'
        self.content_label.setText(self._view_model.content)

    def set_model_data(self,data, selected = False):

        self._view_model.Id = data[0]      # Id from database
        self._view_model.content = data[1]
        self._view_model.selected = selected
        self._view_model.score = data[2]
        self._view_model.source = data[3]
        self._view_model.details = data[4]

    def update_model(self, property:str, value): self._view_model._set_property(property, value)
        
    def is_marked(self): return '[MARKED]' in self._view_model.details
    
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
        
        if not self.is_marked():
            
            self._view_model.details = '[MARKED]' + sender.text() + '\n' + self._view_model.details
            
            status, msg = self._view_model.update_value('additional_details_',self._view_model.details)
            
            if status: 
                self.titlebar.layout().itemAt(0).widget().setVisible(True)
                msg = 'The item was marked now, to reomve bookmark delete keyword [MARKED] from "details" and save.'

            PopupNotifier.Notify(self,'Update bookmark',msg, background_color= 'GREEN' if status else 'RED')

   
    def create_titlebar(self):
        
        if not self.titlebar_created:

            cmd_widget = QWidget()

            cmd_widget.setFixedHeight(32)
            
            commands = QHBoxLayout(cmd_widget)
            commands.setContentsMargins(5,0,5,0)
            commands.setSpacing(2)
            # Add checkbox to select edu-item
            checkbox = QPushButton('')
            checkbox.setToolTip('Check this state to select the item.')
            checkbox.setVisible(False)
            checkbox.setProperty('class','checkLike')
            checkbox.clicked.connect(lambda _, sender= checkbox: self.select_item(sender))
            commands.addWidget(checkbox)

            self.mark_label = QLabel()

            self.mark_label.setPixmap(QPixmap(f'{state.application_path}\\resources\\icons\\svg\\bookmark-filled-blue.svg'))
            # First item of the titlebar
            commands.addWidget(self.mark_label)
            self.mark_label.setVisible(self.is_marked())
            self.mark_label.setProperty('class','caption')
            self.mark_label.setToolTip(ToolTips['Marked Item'])

            # Display Id: <id> | <score> | <Source>
            header_info = QLabel(self._view_model.source + (' | ' if self._view_model.source !='' else '') + str(self._view_model.score)+ ' | ' + str(self._view_model.Id))
            
            header_info.setToolTip('Id | score | source' if self._view_model.source != '' else 'Id | score')

            header_info.setProperty('class','caption')

            commands.addWidget(header_info)
            
            commands.addStretch(1)
            

            ans_mnu_btn = QPushButton('')
            ans_mnu_btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\book-text.svg'))
            ans_mnu_btn.setVisible(False)
            ans_mnu_btn.setToolTip('Show information about Edu-item')
            ans_mnu_btn.setProperty('class','grouped_mini')
            ans_mnu_btn.clicked.connect(lambda _, sender= cmd_widget: self.load_answer(sender))

            commands.addWidget(ans_mnu_btn)
            
            btn2 = QPushButton('')            
            btn2.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\bookmark.svg'))
            btn2.setVisible(False)
            btn2.setToolTip(ToolTips['Set bookmark'])
            btn2.setProperty('class','grouped_mini')
            menu = self.create_bookmark_menu()
            btn2.setMenu(menu)
            
            commands.addWidget(btn2)


            self.titlebar_created = True


        return cmd_widget


    def create_info_panel(self):
        
        if not self.info_panel_created:

            info_panel = QGridLayout()
            header_info = QLabel(str(self._view_model.Id) + ' | ' + self._view_model.source)
            #header_info.setProperty('class','EduItem')
            info_panel.addWidget(header_info,0,0,1,1,Qt.AlignmentFlag.AlignLeft)
            
                             
            ans_label = QLabel()
            ans_label.setWordWrap(True)        
            ans_label.setTextFormat(Qt.TextFormat.RichText)
            ans_label.setText(self._view_model.answer if text_processing.get_html_body_content(self._view_model.answer) != '' else 'NO ANSWER PROVIDED YET!')
            
            info_panel.addWidget(ans_label,1,0,1,1,Qt.AlignmentFlag.AlignTop)

            
            details_input = QPlainTextEdit()
            details_input.setMaximumHeight(100)
            details_input.setPlainText(self._view_model.details if self._view_model.details != '' else 'NO INFO PROVIDED YET!')
            
            details_input.textChanged.connect(lambda: setattr(self._view_model,'details',details_input.toPlainText()))
           
            info_panel.addWidget(details_input,2,0,1,1,Qt.AlignmentFlag.AlignTop)
            
            footer_widget = QWidget()
            footer_layout = QHBoxLayout(footer_widget)
            footer_layout.setSpacing(2)
            self.score_input = QLineEdit(str(self._view_model.score))
            self.score_input.textChanged.connect(lambda:setattr(self._view_model,'score',self.score_input.text()))
            self.score_input.setToolTip('Changes of the score is not applied to database. '+
                                        'to update score go to "Resource Editor".\n' +
                                        ToolTips['Score change warning'])

            footer_layout.addWidget(self.score_input)
            
            checkbox = QLabel('(To distribute only)')
            checkbox.setProperty('class','caption')
            checkbox.setToolTip(self.score_input.toolTip())
            footer_layout.addWidget(checkbox)
            footer_layout.addStretch(1)

            update_details_btn = QPushButton('update details')
            
            update_details_btn.clicked.connect(self.update_details)
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

            # Connect ViewModel to UI
            self._view_model.property_changed.connect(self.update_views)


    def update_details(self):
        status , msg =self._view_model.update_value('additional_details_', self._view_model.details)

        PopupNotifier.Notify(QApplication.activeWindow(), '', msg,background_color= 'green' if status else 'red')


    def load_answer(self,target:QWidget):
        
        self._view_model.load_answer()        
        
        if not self.info_panel_created:

            info_panel = QGridLayout()
            header_info = QLabel(str(self._view_model.Id) + ' | ' + self._view_model.source)
            info_panel.addWidget(header_info,0,0,1,1,Qt.AlignmentFlag.AlignLeft)
            
                             
            ans_label = QLabel()
            ans_label.setWordWrap(True)        
            ans_label.setTextFormat(Qt.TextFormat.RichText)
            ans_label.setText(self._view_model.answer if text_processing.get_html_body_content(self._view_model.answer) != '' else 'NO ANSWER PROVIDED YET!')
            
            ans_label.setProperty('class','EduItem')
            info_panel.addWidget(ans_label,1,0,1,1,Qt.AlignmentFlag.AlignTop)

            
            details_input = QPlainTextEdit() 
            details_input.setMaximumHeight(100)
            details_input.setPlainText(self._view_model.details if self._view_model.details != '' else 'NO INFO PROVIDED YET!')
            # Bind UI elements to ViewModel properties
            self._view_model.bind_property("details", self._view_model.details, details_input)
           
            info_panel.addWidget(details_input,2,0,1,1,Qt.AlignmentFlag.AlignTop)
            
            footer_widget = QWidget()
            footer_layout = QHBoxLayout(footer_widget)
            footer_layout.setSpacing(2)
            self.score_input = QLineEdit(str(self._view_model.score))
            self._view_model.bind_property('score',self._view_model.score, self.score_input)

            #self.score_input.textChanged.connect(lambda:setattr(self._view_model,'score',self.score_input.text()))
            self.score_input.setToolTip('Changes of the score is not applied to database. '+
                                        'to update score go to "Resource Editor".\n' +
                                        ToolTips['Score change warning'])

            footer_layout.addWidget(self.score_input)
            
            checkbox = QLabel('(To distribute only)')
            checkbox.setProperty('class','caption')
            checkbox.setToolTip(self.score_input.toolTip())
            footer_layout.addWidget(checkbox)
            footer_layout.addStretch(1)

            update_details_btn = QPushButton('update details')
            
            update_details_btn.clicked.connect(self.update_details)
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

        point = target.mapToGlobal(target.rect().bottomLeft())
         
        self.info_panel_menu.exec(point)
        

    def select_item(self,sender:QPushButton):
        self._view_model.selected = not self._view_model.selected
        sender.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\check.svg') if self._view_model.selected else QIcon())

    def get_data(self):
        
        return {'content': text_processing.get_html_body_content(self.content_label.text()),
                'Id': self._view_model.Id,
                'selected': self._view_model.selected,
                'score': self._view_model.score}
    
    def show_titlebar(self):
       # The titlebar hase 6 widgets
        # First : mark-label(visible when item marked)
        # second: info about Edu-item(source, score, id,...)- always visible
        # Third : stretch
        # Fourth: checkbox for distribution selection- visible when item focused
        # Fifth : button to open a menu-visible when item focused
        # Sixth : button for set mark(First widget is shown)- visible when item focused 
        
        self.titlebar.layout().itemAt(0).widget().setVisible(True)
        self.titlebar.layout().itemAt(1).widget().setVisible(self.is_marked())
        self.titlebar.layout().itemAt(4).widget().setVisible(True)
        self.titlebar.layout().itemAt(5).widget().setVisible(True)
        
       
    def hide_titlebar(self):
        # The titlebar hase 6 widgets
        # First : mark-label(visible when item marked)
        # second: info about Edu-item(source, score, id,...)- always visible
        # Third : stretch
        # Fourth: checkbox for distribution selection- visible when item focused
        # Fifth : button to open a menu-visible when item focused
        # Sixth : button for set mark(First widget is shown)- visible when item focused 
        
        # Mark label
        self.titlebar.layout().itemAt(1).widget().setVisible(self.is_marked())
        self.titlebar.layout().itemAt(0).widget().setVisible(self._view_model.selected)
        #
        # Second item is skeeped
        #
        # checkbox
        # menu button
        self.titlebar.layout().itemAt(4).widget().setVisible(False)
        # set mark button
        self.titlebar.layout().itemAt(5).widget().setVisible(False)

