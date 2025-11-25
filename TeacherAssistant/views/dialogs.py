#import datetime
from PySide6.QtWidgets import (QMessageBox, QVBoxLayout,QTableWidget,QFormLayout, QLineEdit, QPushButton, 
                               QListView, QHBoxLayout,QGridLayout,QCalendarWidget, QComboBox,
                               QLabel, QTextEdit, QFileDialog,QDialog,QTableWidgetItem)

from PySide6.QtCore import QItemSelection, QByteArray,Qt
from PySide6.QtGui import QPixmap, QIcon

from Imaging.Tools import bytea_to_pixmap
from TeacherAssistant import state
from TeacherAssistant.view_models import PersonalInfoViewModel as pvModel
from TeacherAssistant.utils.image_tools import convert_qpixmap_to_binary


class CalendarPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)  # Popup style
        self.calendar = QCalendarWidget(self)
        self.calendar.clicked.connect(self.on_date_selected)

        layout = QVBoxLayout(self)
        layout.addWidget(self.calendar)
        layout.setContentsMargins(0, 0, 0, 0)  # No margins

        self.selected_date = None

    def on_date_selected(self, date):
        self.selected_date = date
        self.accept()  # Close the popup

# View (UI Layer)
class PersonalInfoDialog(QDialog):

    def __init__(self,title='',parent=None):
        
        super().__init__(parent)
        
        self.setWindowTitle(title)
                
        self.initUI()

        self._view_model = pvModel.PersonalInfoViewModel() 

        self._bind_view_model()

    def show_calendar(self, parent:QPushButton):
        popup = CalendarPopup(parent)
        # Position popup below the button
        popup.move(parent.mapToGlobal(parent.rect().bottomLeft()))
        if popup.exec():
            selected_date = popup.selected_date
            if selected_date:
                parent.setText(selected_date.toString("yyyy-MM-dd"))
                self._view_model.birth_date = selected_date.toString("yyyy-MM-dd")
    
    def initUI(self):
        # Main layout
        grid_layout = QGridLayout(self)
        # Set main layout
        self.setLayout(grid_layout)
        # Window settings
        self.setWindowTitle("Student Information Form")

        # Remove the maximize and minimize buttons
        self.setWindowFlags(self.windowFlags() & Qt.WindowType.WindowCloseButtonHint)
    
        # First Column: First Name, Last Name, Student ID
        fname_label = QLabel("First Name:")
        grid_layout.addWidget(fname_label, 0, 0)

        self.fname_input = QLineEdit()
        self.fname_input.setPlaceholderText("First name")
        grid_layout.addWidget(self.fname_input, 0, 1)

        lname_label = QLabel("Last Name:")
        grid_layout.addWidget(lname_label, 1, 0)

        self.lname_input = QLineEdit()
        self.lname_input.setPlaceholderText("Last name")
        grid_layout.addWidget(self.lname_input, 1, 1)

        id_label = QLabel("ID:")
        grid_layout.addWidget(id_label)
        grid_layout.addWidget(id_label, 2, 0)

        self.id_input = QLineEdit()
        grid_layout.addWidget(self.id_input) 

        self.id_input.setPlaceholderText("student ID")
        grid_layout.addWidget(self.id_input, 2, 1)

        # Second Column: Date of Birth, Gender, Phone
        dob_label = QLabel("Date of Birth:")
        grid_layout.addWidget(dob_label, 0, 2)


        # Calendar dropdown button
        self.calendar_button = QPushButton("Select Date")
        self.calendar_button.clicked.connect(lambda _, sender= self.calendar_button: self.show_calendar(sender))

        grid_layout.addWidget(self.calendar_button, 0, 3)

        gender_label = QLabel("Gender:")
        grid_layout.addWidget(gender_label, 1, 2)

        self.gender_input = QComboBox()
        self.gender_input.addItems(["Not specified","Male", "Femal"])
        self.gender_input.setPlaceholderText("Select gender")
        grid_layout.addWidget(self.gender_input, 1, 3)

        phone_label = QLabel("Phone:")
        grid_layout.addWidget(phone_label, 2, 2)
        self.phone_input = QLineEdit()
        
        self.phone_input.setPlaceholderText("Enter phone number")
        grid_layout.addWidget(self.phone_input, 2, 3)

        self.photo_label = QLabel("No Photo\nUploaded")
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Set photo box dimensions to the formal size (35mm x 45mm ≈ 138x177 pixels at 96 DPI)
        self.photo_label.setFixedSize( 145 , 167)
        self.photo_label.setStyleSheet("border: 1px solid #88888888; color:#888888; border-radius: 4px; padding:2px; margin:0px 0px 0px 10px")
        
        grid_layout.addWidget(self.photo_label, 0, 4, 6, 2)  # Span across 3 rows and 1 column
        grid_layout.setAlignment(self.photo_label,Qt.AlignmentFlag.AlignTop)
        
        upload_photo_button = QPushButton("")
        upload_photo_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\upload.svg'))
        upload_photo_button.setProperty('class','grouped_mini')
        grid_layout.addWidget(upload_photo_button,5,4,alignment=Qt.AlignmentFlag.AlignRight)
        upload_photo_button.clicked.connect(self._upload_photo)
        
        self.remove_photo_button = QPushButton("")
        self.remove_photo_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\x.svg'))
        self.remove_photo_button.setProperty('class','grouped_mini')
        self.remove_photo_button.clicked.connect(self._remove_photo)
        grid_layout.addWidget(self.remove_photo_button,5,5,alignment=Qt.AlignmentFlag.AlignLeft)

        # Address (stretched across 2 columns)
        address_label = QLabel("Address:")
        grid_layout.addWidget(address_label, 4, 0)

        self.address_input = QLineEdit()#self.data[4] if self.data else '')
        self.address_input.setPlaceholderText("Enter address")
        grid_layout.addWidget(self.address_input, 4, 1, 1,3)  # Span across 1 row and 2 columns
        
        # Parent/Guardian Name
        parent_name_label = QLabel("Parent Name:")
        grid_layout.addWidget(parent_name_label, 3, 0)

        self.parent_name_input = QLineEdit()#self.data[7] if self.data else '')
        self.parent_name_input.setPlaceholderText("Enter parent/guardian name")
        grid_layout.addWidget(self.parent_name_input, 3, 1)

        # Parent/Guardian Phone
        parent_phone_label = QLabel("Parent Phone:")
        grid_layout.addWidget(parent_phone_label, 3, 2)

        self.parent_phone_input = QLineEdit()#self.data[8] if self.data else '')
        self.parent_phone_input.setPlaceholderText("Enter parent/guardian phone")
        grid_layout.addWidget(self.parent_phone_input, 3, 3)

        # Additional Details Section
        grid_layout.addWidget(QLabel("Additional Details:"), 5, 0)

        self.additional_details_input = QTextEdit()#self.data[9] if self.data else '')
        self.additional_details_input.setPlaceholderText("Enter additional details (e.g., medical conditions, special needs)...")
        grid_layout.addWidget(self.additional_details_input, 6, 0, 1, 7)  # Span across 1 row and 5 columns

        self.clear_form_button = QPushButton("Clear")
        grid_layout.addWidget(self.clear_form_button, 7, 0)

        self.save_button = QPushButton("Save")
        grid_layout.addWidget(self.save_button, 7, 4)

        self.close_form_button = QPushButton("Close")
        self.close_form_button.clicked.connect(self.close)
                # Save button action
        self.save_button.clicked.connect(lambda _: self._view_model.save())

        self.clear_form_button.clicked.connect(self._clear_form)

        grid_layout.addWidget(self.close_form_button, 7, 5)

        self.setLayout(grid_layout)

    def set_model_data(self,data):

        self._view_model.old_id = data[0]
        self._view_model.id = data[0]
        self._view_model.fname = data[1]
        self._view_model.lname = data[2]
        self._view_model.phone = data[3]
        self._view_model.address = data[4]
        self._view_model.photo = data[5]
        self._view_model.parent_name = data[8]
        self._view_model.parent_phone = data[9]
        self._view_model.additional_details = data[10]
        self._view_model.birth_date = str(data[11])
        self._view_model.gender = data[12]
        
        self._bind_view_model() 
    
    
    def _bind_view_model(self):
        # Bind ViewModel properties to UI elements
        self.id_input.setText(self._view_model.id)
        self.fname_input.setText(self._view_model.fname)
        self.lname_input.setText(self._view_model.lname)
        self.phone_input.setText(self._view_model.phone)
        self.address_input.setText(self._view_model.address)
        self.parent_name_input.setText(self._view_model.parent_name)
        self.parent_phone_input.setText(self._view_model.parent_phone)
        self.additional_details_input.setPlainText(self._view_model.additional_details)
        self.calendar_button.setText(self._view_model.birth_date)
        self.gender_input.setCurrentText(self._view_model.gender)
        
        pixmap = bytea_to_pixmap(self._view_model.photo)
        scaled_pixmap = pixmap.scaled(self.photo_label.size(), 
                                      Qt.AspectRatioMode.IgnoreAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        self.photo_label.setPixmap(scaled_pixmap)
        if not pixmap:
            self.photo_label.setText("No photo\nuploaded")
        
        # Connect UI changes to ViewModel
        self.id_input.textChanged.connect(lambda text: setattr(self._view_model, "id", text))
        self.fname_input.textChanged.connect(lambda text: setattr(self._view_model, "fname", text))
        self.lname_input.textChanged.connect(lambda text: setattr(self._view_model, "lname", text))
        self.phone_input.textChanged.connect(lambda text: setattr(self._view_model, "phone", text))
        self.address_input.textChanged.connect(lambda text: setattr(self._view_model, "address", text))
        self.parent_name_input.textChanged.connect(lambda text: setattr(self._view_model, "parent_name", text))
        self.parent_phone_input.textChanged.connect(lambda text: setattr(self._view_model, "parent_phone", text))
        self.additional_details_input.textChanged.connect(lambda: setattr(self._view_model,'additional_details',self.additional_details_input.toPlainText()))
        self.gender_input.currentTextChanged.connect(lambda text: setattr(self._view_model, "gender", text))
        #self.dob_input.textChanged.connect(lambda text: setattr(self._view_model, "birth_date", text))

        # Update date when a date is selected
        #self.calendar_widget.clicked.connect(self._update_date)  
        

    #Update the UI when a ViewModel property changes.    
    def _update_id(self, property_name):

        if property_name == "id": self.id_input.setText(self._view_model.id)

    def _clear_form(self):
        # Clear all input fields
        self.id_input.clear()
        self.fname_input.clear()
        self.lname_input.clear()
        self.dob_input.clear()
        self.gender_input.setCurrentIndex(0)
        self.phone_input.clear()
        self.address_input.clear()
        self.parent_name_input.clear()
        self.parent_phone_input.clear()
        self.additional_details_input.clear()
        self._remove_photo()  # Clear the photo as well

    def _update_date(self, date):
        # Update the date input field when a date is selected
        self.dob_input.setText(date.toString("yyyy/MM/dd"))
        self.calendar_menu.close()  # Close the dropdown after selecting a date

    def _remove_photo(self):
        self.photo_label.setPixmap(QPixmap())  # Clear the photo
        self.photo_label.setText("No Photo\nUploaded")
        
        self._view_model.photo = QByteArray()

    def _upload_photo(self):

        dialog = QFileDialog(parent=self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp)")
        
        if dialog.exec():
            file_name = dialog.selectedFiles()
            if file_name[0]:
                pixmap = QPixmap(file_name[0])
                self._view_model.photo = convert_qpixmap_to_binary(pixmap)
                # Scale the photo to fill the entire photo box (ignore aspect ratio)
                scaled_pixmap = pixmap.scaled(self.photo_label.size(), 
                                              Qt.AspectRatioMode.IgnoreAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                self.photo_label.setPixmap(scaled_pixmap)
                self.photo_label.setText("")

class GroupsManagerDialog(QDialog):
    
    def __init__(self,cursor,title='',parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        #self.setBaseSize(800,500)
        self.cursor = cursor
        self.init_ui()
        self.load_data()



    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        self.table_widget.setHorizontalHeaderLabels(["Grade", "Book", "Title", "Events", "Members", "Description"])
        # Connect selectionChanged signal
        self.table_widget.selectionModel().selectionChanged.connect(self.handle_selection_changed)
        layout.addWidget(self.table_widget)
        
        form_layout = QFormLayout()
        self.grade_input = QLineEdit()
        #self.grade_input.setRange(1, 12)
        form_layout.addRow("Grade:", self.grade_input)
        
        self.book_input = QLineEdit()
        form_layout.addRow("Book:", self.book_input)
        
        self.title_input = QLineEdit()
        form_layout.addRow("Title:", self.title_input)
        
        self.events_input = QLineEdit()
        form_layout.addRow("Events:", self.events_input)
        
        self.members_input = QLineEdit()
        form_layout.addRow("Members:", self.members_input)
        
        self.description_input = QLineEdit()
        form_layout.addRow("Description:", self.description_input)
        
        layout.addLayout(form_layout)
        
        self.add_button = QPushButton("Add Group")
        self.add_button.clicked.connect(self.add_group)
        layout.addWidget(self.add_button)
        
        self.update_button = QPushButton("Update Selected Group")
        self.update_button.clicked.connect(self.update_group)
        layout.addWidget(self.update_button)
        
        self.delete_button = QPushButton("Delete Selected Group")
        self.delete_button.clicked.connect(self.delete_group)
        layout.addWidget(self.delete_button)
        
    def handle_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        # Get the currently selected items
        selected_items = self.table_widget.selectedItems()
        if selected_items:
            selected_text = ", ".join([item.text() for item in selected_items])
            #self.selected_label.setText(f"Selected: {selected_text}")
        #else:
            #self.selected_label.setText("Selected: None")


    def load_data(self):
        self.cursor.execute("SELECT grade_, book_, title_, events_, members_, description_ FROM groups")
        records = self.cursor.fetchall()
        self.table_widget.setRowCount(len(records))
        for row_idx, row_data in enumerate(records):
            for col_idx, col_data in enumerate(row_data):
                self.table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

    def add_group(self):
        try:
            self.cursor.execute(
                "INSERT INTO groups (grade_, book_, title_, events_, members_, description_) VALUES (%s, %s, %s, %s, %s, %s)",
                (self.grade_input.text(), self.book_input.text(), self.title_input.text(),
                 self.events_input.text(), self.members_input.text(), self.description_input.text())
            )
            self.load_data()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def update_group(self):
        selected = self.table_widget.currentRow()
        if selected >= 0:
            grade = self.grade_input.text()
            book = self.book_input.text()
            title = self.title_input.text()
            events = self.events_input.text()
            members = self.members_input.text()
            description = self.description_input.text()
            original_title = self.table_widget.item(selected, 2).text()
            try:
                self.cursor.execute("""
                    UPDATE groups SET grade_ = %s, book_ = %s, title_ = %s, 
                    events_ = %s, members_ = %s, description_ = %s
                    WHERE title_ = %s
                """, (grade, book, title, events, members, description, original_title))
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
    
    def delete_group(self):
        if QMessageBox.warning(self,'','DELETE RECORD?',QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Cancel:
            return
        
        selected = self.table_widget.currentRow()
        if selected >= 0:
            grade = self.table_widget.item(selected, 0).text()
            title = self.table_widget.item(selected, 2).text()
            try:
                self.cursor.execute("DELETE FROM groups WHERE grade_ = %s AND title_ = %s", (grade, title))
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

class GroupSelectionDialog(QDialog):
   
    def __init__(self, groups, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Select Group")
        #self.setGeometry(200, 200, 400, 300)

        # Main layout
        layout = QVBoxLayout(self)

        # List view for group titles
        self.list_view = QListView()
        self.list_view.setSelectionMode(QListView.SingleSelection)
        #self.model = QStringListModel(groups)
        self.list_view.setModel(groups)
        layout.addWidget(self.list_view)

        # Buttons layout
        button_layout = QHBoxLayout()
        self.select_button = QPushButton("Select")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Connect buttons
        self.select_button.clicked.connect(self.select_group)
        self.cancel_button.clicked.connect(self.reject)

        self.selected_group = None

    def select_group(self):
        selected_index = self.list_view.currentIndex()#.selectedIndexes()
       
        if selected_index:
            self.selected_group = selected_index
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a group from the list.")
