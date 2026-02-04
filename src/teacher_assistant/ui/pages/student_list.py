
import pandas as pd
from typing import Iterable
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QMessageBox, 
                               QCheckBox, QFileDialog, QTableView, QAbstractItemView, 
                               QDialog, QScrollArea, QGridLayout, QApplication, QMenu,
                               QLabel, QLineEdit, QComboBox,QAbstractScrollArea, QPushButton)

from PySide6.QtGui import (Qt, QAction, QIcon, QStandardItemModel, QStandardItem)

from PySideAbdhUI.Notify import PopupNotifier
from processing.Imaging.Tools import bytea_to_pixmap
from processing.text.text_processing import is_mostly_rtl
from view_models.EduItems import ClassroomGroupViewModel
from ui.widgets.widgets import ObservedBehaviourWidget
from ui.dialogs.dialogs import CustomAssignmentDialog, GroupSelectionDialog, GroupsManagerDialog, PersonalInfoDialog
from ui.pages.activity_tracking import StudentActivityTrackingPage
from ui.pages.edu_resource_view import EduResourcesView
from core.app_context import app_context 

# Constants for better maintainability

# UI Layout Constants
PHOTO_WIDTH = 90           # Width of student photo display in pixels
PHOTO_HEIGHT = 130         # Height of student photo display in pixels
PHOTO_PADDING = 10         # Additional padding around photo widget in pixels
NOTES_SCROLL_HEIGHT = 120  # Fixed height for the last note scroll area in pixels
NAME_LABEL_WIDTH = 150     # Fixed width for student name/info label in pixels
ADDRESS_LABEL_WIDTH = 250  # Fixed width for address/contact label in pixels
SEARCH_INPUT_WIDTH = 200   # Fixed width for search input field in pixels
CSV_CHUNK_SIZE = 1000      # Number of rows to process per chunk when importing CSV files

# Table Column Indices
# These constants represent the column positions in the QTableView
COL_PHOTO = 0      # Column index for student photo
COL_INFO = 1       # Column index for student ID and name information
COL_ADDRESS = 2    # Column index for address and contact details
COL_LAST_NOTE = 3  # Column index for last observed behaviour note

# Database Record Field Indices:
# These constants represent the field positions in the database query result tuple
# Query returns: Id, fname_, lname_, phone_, address_, photo_, date_time_, 
#                observed_behaviour_, parent_name_, parent_phone_, additional_details_, 
#                birth_date_, gender_
REC_ID = 0                   # Student ID field index
REC_FNAME = 1                # First name field index
REC_LNAME = 2                # Last name field index
REC_PHONE = 3                # Phone number field index
REC_ADDRESS = 4              # Address field index
REC_PHOTO = 5                # Photo (bytea) field index
REC_DATE_TIME = 6            # Date/time of last observation field index
REC_OBSERVED_BEHAVIOUR = 7   # Last observed behaviour text field index
REC_PARENT_NAME = 8          # Parent name field index
REC_PARENT_PHONE = 9         # Parent phone field index
REC_ADDITIONAL_DETAILS = 10  # Additional details field index
REC_BIRTH_DATE = 11          # Birth date field index
REC_GENDER = 12              # Gender field index

class StudentListPage(QWidget):
    """Main page for displaying and managing student lists."""
    
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        
        # Instance variables
        # Note: Student record data is now stored in model items (UserRole) instead of self.data
        self.search_index = 0
        self._multi_select_enabled = False
        self._current_group_id = None  # Track current group for operations
        
        self.initUI()
    
    def initUI(self):
        """Initialize the user interface components."""
        self.setContentsMargins(10, 0, 10, 10)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Header section with title, search, filter, and options
        page_title = QLabel('STUDENT LIST')
        page_title.setProperty('class', 'heading2')

        group_model = self.load_groups()
        search_input = QLineEdit()
        search_input.setPlaceholderText('Search students...')
        search_input.setFixedWidth(SEARCH_INPUT_WIDTH)
        search_input.textChanged.connect(self.find_in_list)

        class_filter_combo = QComboBox()
        class_filter_combo.setModel(group_model)
        class_filter_combo.currentIndexChanged.connect(lambda _: self.load_students(class_filter_combo))

        edu_btn = self.create_more_option_menu(group_model)
        edu_btn.setToolTip('Open options menu')

        command_layout = QHBoxLayout()
        command_layout.setSpacing(10)
        command_layout.addWidget(page_title)
        command_layout.addStretch()
        command_layout.addWidget(search_input)
        command_layout.addWidget(class_filter_combo)
        command_layout.addWidget(edu_btn)

        header_widget = QWidget()
        header_widget.setLayout(command_layout)
        main_layout.addWidget(header_widget)
        
        # Create and configure table model
        self.model = QStandardItemModel(0, 4)
        self.model.setHorizontalHeaderLabels(['PHOTO', 'INFO', 'ADDRESS', 'LAST NOTE'])
        
        # Create and configure table view
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setShowGrid(False)

        # Configure column widths and resize modes
        header = self.table.horizontalHeader()
        self.table.setColumnWidth(COL_PHOTO, PHOTO_WIDTH + PHOTO_PADDING)
        header.setSectionResizeMode(COL_PHOTO, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_INFO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_ADDRESS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_LAST_NOTE, QHeaderView.ResizeMode.Stretch)

        main_layout.addWidget(self.table)
        
        # Footer with student count
        self.footer = QLabel('')
        self.footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.footer.setProperty('class', 'caption')
        main_layout.addWidget(self.footer)
        
        # Initial load
        class_filter_combo.setCurrentIndex(0)
        self.load_students(class_filter_combo)

    def show_csv_load_message(self):
        """Show warning message about CSV format requirements."""
        option = app_context.settings_manager.find_value('csv_show_option_message')
        
        # If user previously chose "Don't show again", skip the message
        if option:
            return QMessageBox.StandardButton.Ok

        column_mapping = ["ID", "First Name", "Last Name", "Parent Name",
                         "Phone", "Address", "Parent Phone", "Additional Details",
                         "Gender", "Date"]
                    
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("CSV Import Warning")
        msg = ('Note!\n\nThis feature currently only accepts CSV files with the following format.\n'
               'The columns of the CSV file must be as follows:\n\n'
               f'{", ".join(column_mapping)}\n\n'
               'If these are not followed, the data may not be saved as you expect.\n\n'
               'Additionally, if you need to upload a "photo" for each record, this must be done separately. '
               'After saving the profile, select the desired person from the list and upload the photo '
               'from the edit profile section.\n\n'
               'If you are sure, click "OK" to continue.')
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

        checkbox = QCheckBox("Don't show again")
        msg_box.setCheckBox(checkbox)
        btn = msg_box.exec()

        # Store the user preference
        app_context.settings_manager.write({"csv_show_option_message": checkbox.isChecked()})
        return btn

    def load_from_csv(self):
        """Load student data from a CSV file."""
        if self.show_csv_load_message() == QMessageBox.StandardButton.Cancel:
            return
    
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("CSV Files (*.csv)")
        dialog.setWindowTitle("Select CSV File to Import")
        
        if not dialog.exec():
            return
            
        csv_file = dialog.selectedFiles()
        if not csv_file:
            return
            
        try:
            # Get database column names
            table_columns = app_context.database.get_columns('personal_info')
            if not table_columns:
                PopupNotifier.Notify(self, "Error", "Could not retrieve database columns.", 'bottom-right', delay=5000)
                return
            
            # Read CSV headers dynamically
            csv_headers = pd.read_csv(csv_file[0], nrows=0).columns.tolist()

            # Case-sensitive column mapping
            column_mapping = {
                "ID": "id",
                "First Name": "fname_",
                "Last Name": "lname_",
                "Parent Name": "parent_name_",
                "Phone": "phone_",
                "Address": "address_",
                "Parent Phone": "parent_phone_",
                "Additional Details": "additional_details_",
                "Gender": "gender_",
                "Date": "birth_date_"
            }

            # Validate mapping
            valid_mapping = {
                csv_col: sql_col 
                for csv_col, sql_col in column_mapping.items() 
                if csv_col in csv_headers and sql_col in table_columns
            }

            if not valid_mapping:
                PopupNotifier.Notify(self, "Error", "No valid column mapping found. Please check CSV format.", 
                                      'bottom-right', delay=5000)
                return

            # Load and insert data in chunks
            data = pd.read_csv(csv_file[0], chunksize=CSV_CHUNK_SIZE, dtype_backend='numpy_nullable')
            app_context.database.bulk_insert_csv(data, 'personal_info', valid_mapping)
            
            msg = f'Successfully loaded data from {csv_file[0]}'
            PopupNotifier.Notify(self, "Success", msg, 'bottom-right', delay=5000)
            
            # Reload student list if currently showing "All"
            if self._current_group_id == 'All':
                # Trigger reload by finding the combo box
                for widget in self.findChildren(QComboBox):
                    if widget.model() == self.load_groups():
                        self.load_students(widget)
                        break

        except Exception as e:
            msg = f'Error loading CSV: {str(e)}'
            PopupNotifier.Notify(self, "Error", msg, 'bottom-right', delay=5000)

    def create_more_option_menu(self, group_model=None) -> QPushButton:
        """Create the options menu button with all available actions."""
        btn = QPushButton('')            
        btn.setProperty('class', 'grouped_mini')
        btn.setIcon(QIcon(":/icons/menu.svg"))
        btn.setToolTip('Open options menu')

        menu = QMenu(btn)
        btn.setMenu(menu)
        
        # Multi-selection toggle
        action_multi = QAction(icon=QIcon(':/icons/list-checks.svg'),
                               text='Enable multi-selection', parent=menu)
        action_multi.setCheckable(True)
        action_multi.setChecked(self._multi_select_enabled)
        action_multi.setToolTip('Toggle multi-row selection in the students list')

        def _toggle_multi(checked):
            self._multi_select_enabled = checked
            if hasattr(self, 'table') and self.table is not None:
                mode = (QAbstractItemView.SelectionMode.MultiSelection if checked 
                       else QAbstractItemView.SelectionMode.SingleSelection)
                self.table.setSelectionMode(mode)

        action_multi.triggered.connect(_toggle_multi)
        
        # Student management actions
        action_add = QAction(icon=QIcon(':/icons/id-card.svg'), text='Add new student', parent=menu)
        action_add.triggered.connect(lambda: self.open_personal_info_dialog(None))
        menu.addAction(action_add)

        action_import = QAction(icon=QIcon(':/icons/sheet.svg'), text='Import from CSV file', parent=menu)
        action_import.setToolTip('Opens file dialog to load list of students to database')
        action_import.triggered.connect(self.load_from_csv)
        menu.addAction(action_import)

        menu.addSeparator()
        menu.addAction(action_multi)
        menu.addSeparator()

        # Educational items assignment
        action_edu_all = QAction(icon=QIcon(':/icons/drafting-compass.svg'), 
                                text='Set Edu-Item to group', parent=menu)
        action_edu_all.triggered.connect(lambda: self.send_edu_items('all'))
        menu.addAction(action_edu_all)

        action_edu_selected = QAction(icon=QIcon(':/icons/drafting-compass.svg'), 
                                     text='Set Edu-Item to selected students', parent=menu)
        action_edu_selected.triggered.connect(lambda: self.send_edu_items('selected-list'))
        menu.addAction(action_edu_selected)
        
        menu.addSeparator()
        
        # Group management
        action_group_selected = QAction(icon=QIcon(':/icons/users-selected.svg'), 
                                       text='Group selected students', parent=menu)
        action_group_selected.triggered.connect(
            lambda: self.show_group_dialog(group_model, 'selected-list'))
        menu.addAction(action_group_selected)
        
        action_group_all = QAction(icon=QIcon(':/icons/users.svg'), text='Group all', parent=menu)
        action_group_all.triggered.connect(lambda: self.show_group_dialog(group_model, 'all'))
        menu.addAction(action_group_all)
                    
        action_manage_groups = QAction(icon=QIcon(':/icons/combine.svg'), 
                                      text='Manage groups', parent=menu)
        action_manage_groups.triggered.connect(self.show_manage_groups_dialog)
        menu.addAction(action_manage_groups)
        
        return btn
    
        # Creates menu for each student
    
    def create_menu_btn(self, record,row):

            btn = QPushButton('')
            btn.setIcon(QIcon(':/icons/menu.svg'))            
            btn.setProperty('class','grouped_mini')

            menu = QMenu(btn)
            
            btn.setMenu(menu)
            
            # Menu item to display student's learning progress
            # Opens new page to view learning profile(not personal profile)
            action3 = QAction(icon=QIcon(':/icons/chart-spline.svg'), text= 'Learning progress',parent=menu)
            action3.triggered.connect(lambda _, data=record: self.open_behaviour_list_page(data))
            menu.addAction(action3)

            action7 = QAction(icon=QIcon(':/icons/chart-spline.svg'),
                              text= 'Add custom score',
                              statusTip='No need to Edu-Item',
                              parent=menu)
            action7.triggered.connect(lambda _, stu=record[0]: self.open_custom_assignment_dialog(stu))
            menu.addAction(action7)
            
            action1 = QAction(icon=QIcon(':/icons/drafting-compass.svg'), text= 'Assign Edu-item',parent=menu)
            action1.triggered.connect(lambda _, stu = {'Id':record[0], "Name":f'{record[1]} {record[2]}'}:self.assign_edu_to_student(stu))
            menu.addAction(action1)
                    

            action2 = QAction(icon=QIcon(':/icons/pencil.svg'),text='write behavioral observation', parent=menu)
            action2.triggered.connect(lambda _, data=record: self.open_behaviour_note_editor(data))
            menu.addAction(action2)

            action4 = QAction(icon=QIcon(':/icons/id-card.svg'),text='Personal data',parent=menu)
            action4.triggered.connect(lambda _, data=record: self.open_personal_info_dialog(data))
            menu.addAction(action4)
            
            menu.addSeparator()

            action5 = QAction(icon=QIcon(':/icons/x.svg'),text='Remove from group',parent=menu)
            action5.triggered.connect(lambda _, stu = {'Id':record[0], "Name":f'{record[1]} {record[2]}'}: self.remove_from_group(stu))
            menu.addAction(action5)

            action6 = QAction(icon=QIcon(':/icons/database-x.svg'), text= 'Remove from database',parent=menu)
            action6.triggered.connect(lambda _, student_id= record[0],r=row: self.delete_person(student_id,r))
            menu.addAction(action6)

            return btn
    
    def open_custom_assignment_dialog(self, stu_Id:str):
        dialog = CustomAssignmentDialog()
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            status, message = self.update_custom_assignment(stu_Id,99,data['description'],data['feedback'],data['response_date'],
                                          data['deadline'],data['assignment_date'],data['score_earned'],data['max_score'])

            PopupNotifier.Notify(self,message= message)
        else:
            PopupNotifier.Notify(self,message= "Dialog cancelled")
    
    def update_custom_assignment(self, stu_id: str, qb_Id: int, answer: str, feedback: str, 
                                 reply_date: str, deadline: str, assignment_date: str, 
                                 score_earned: float, max_score: float):
        """Insert a custom assignment record into the database."""
        try:
            cmd = ('INSERT INTO quests (qb_Id, student_id, max_point_, earned_point_, '
                   'assign_date_, deadline_, reply_date_, answer_, feedback_) '
                   'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);')

            app_context.database.execute(
                cmd, (qb_Id, stu_id, max_score, score_earned, assignment_date, 
                     deadline, reply_date, answer, feedback))

            status = True
            message = f'Custom assignment for student {stu_id} was saved successfully.'

        except Exception as e:
            status = False
            message = f'Error saving assignment: {str(e)}'

        return status, message
        
    def show_group_dialog(self, model: QStandardItemModel, option='selected-list'):
        """Show dialog to assign selected students to a group."""
        if option == 'all':
            self.table.selectAll()
        elif not self.table.selectedIndexes(): 
            PopupNotifier.Notify(self, '', 'First select at least one student')
            return

        dlg = GroupSelectionDialog(model)
        
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
            
        try:
            item = model.item(dlg.selected_group.row())
            if not item:
                PopupNotifier.Notify(self, 'Error', 'Invalid group selection')
                return
                
            group: ClassroomGroupViewModel = item.data(Qt.ItemDataRole.UserRole)
            if not group or isinstance(group, str):  # Skip "All" option
                PopupNotifier.Notify(self, 'Error', 'Please select a valid group')
                return
            
            # Collect student IDs from selected rows (get data from model items)
            selected_rows = {index.row() for index in self.table.selectedIndexes()}
            student_ids = []
            for row in selected_rows:
                record = self._get_record_from_row(row)
                if record:
                    student_ids.append(str(record[REC_ID]))
            
            if not student_ids:
                PopupNotifier.Notify(self, 'Error', 'No valid students selected')
                return
            
            # Join IDs with comma
            id_list = ',' + ','.join(student_ids)  # Add leading comma for format
            
            status, message = group.model.add_member(int(group.Id), id_list)
            
            if status:
                # Reload groups to refresh the combo box
                for widget in self.findChildren(QComboBox):
                    if widget.model() == model:
                        widget.setModel(self.load_groups())
                        break
            
            PopupNotifier.Notify(self, '', message)
            
        except Exception as e:
            PopupNotifier.Notify(self, 'Error', f'Failed to add students to group: {str(e)}')
        
    def show_manage_groups_dialog(self):
        """Show dialog for managing classroom groups."""
        try:
            # Get a cursor from the database connection for the dialog
            # Note: The dialog should be refactored to use app_context.database directly
            cursor = app_context.database.connection.cursor()
            dlg = GroupsManagerDialog(cursor)
            dlg.setFixedSize(675, 500)
            result = dlg.exec()
            cursor.close()  # Clean up cursor after dialog closes
            
            # Reload groups after dialog closes if changes were made
            if result == QDialog.DialogCode.Accepted:
                for widget in self.findChildren(QComboBox):
                    if isinstance(widget.model(), QStandardItemModel):
                        widget.setModel(self.load_groups())
                        break
        except Exception as e:
            PopupNotifier.Notify(self, 'Error', f'Failed to open groups manager: {str(e)}')
            
    def load_groups(self):
            
            model = QStandardItemModel()
            #load groups
            if not app_context.database:
                 return model
            
            groups = app_context.database.fetchall('SELECT id, grade_, book_, title_, events_, members_, description_ FROM groups;')                
            
            item = QStandardItem('All')
            item.setData('All', Qt.ItemDataRole.UserRole)
            model.appendRow(item)

            for row , record in enumerate(groups): 

                item = QStandardItem()

                item.setData(record[3],Qt.ItemDataRole.DisplayRole)

                group = ClassroomGroupViewModel()

                group.Id = record[0]
                group.grade = str(record[1])
                group.book = record[2]
                group.title = record[3]
                group.events = record[4]
                group.members = record[5]
                group.description = record[6]
                item.setData(group, Qt.ItemDataRole.UserRole)
                model.appendRow(item)

            return model
    
    def clear_by_new_model(self):
        """Clear everything by creating a new model"""
        # 1. Remove old widgets
        for row in range(self.model.rowCount()):
            for col in range(self.model.columnCount()):
                widget = self.table.indexWidget(self.model.index(row, col))
                if widget:
                    widget.deleteLater()
        
        # 2. Create and set a new model
        new_model = QStandardItemModel(0, 4)  # Empty model
        new_model.setHorizontalHeaderLabels(['PHOTO', 'INFO', 'ADDRESS', 'LAST NOTE'])
        
        # 3. Set the new model
        self.table.setModel(new_model)
        self.model = new_model  # Update reference
        
        # 4. Reapply header settings
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 150)
    
        print("Table completely reset with new model")
    
    def load_students(self, sender: QComboBox):
        """Load students from database based on selected group filter."""
        try:
            selected = sender.currentData(Qt.ItemDataRole.UserRole)
            
            # Build SQL query with proper parameterization to prevent SQL injection
            base_query = (
                'SELECT t1.Id, t1.fname_, t1.lname_, t1.phone_, t1.address_, t1.photo_, '
                't2.date_time_, t2.observed_behaviour_, t1.parent_name_, t1.parent_phone_, '
                't1.additional_details_, t1.birth_date_, t1.gender_ '
                'FROM personal_info t1 '
                'LEFT JOIN ('
                '  SELECT t2.* FROM observed_behaviours t2 '
                '  INNER JOIN ('
                '    SELECT student_id, MAX(date_time_) AS max_created_at '
                '    FROM observed_behaviours '
                '    GROUP BY student_id'
                '  ) last_records ON t2.student_id = last_records.student_id '
                '    AND t2.date_time_ = last_records.max_created_at'
                ') t2 ON t1.id = t2.student_id'
            )
            
            # Handle group filtering with parameterized query
            if isinstance(selected, str) or not selected:
                # Load all students
                query = base_query + ' ORDER BY t1.fname_, t1.lname_;'
                params = None
                self._current_group_id = 'All'
            else:
                # Filter by group members - use parameterized query for safety
                # Parse members string (format: ",id1,id2,id3" or "id1,id2,id3")
                members_str = str(selected.members) if selected.members else ''
                members_list = [m.strip() for m in members_str.split(',') if m.strip()]
                
                if not members_list:
                    # Empty group
                    self._clear_table()
                    return
                
                # Use IN clause with parameterized query (safer than ANY with array)
                # Create placeholders for each ID
                placeholders = ','.join(['%s'] * len(members_list))
                query = base_query + f' WHERE t1.Id IN ({placeholders}) ORDER BY t1.fname_, t1.lname_;'
                params = tuple(members_list)
                self._current_group_id = selected.Id
            
            # Execute query
            data = app_context.database.fetchall(query, params) if params else app_context.database.fetchall(query)
            
            self._update_table_display(data)
            
        except Exception as e:
            error_msg = f"Error loading students: {str(e)}"
            print(error_msg)
            PopupNotifier.Notify(self, "Error", error_msg, 'bottom-right', delay=5000)
            self._clear_table()
    
    def _clear_table(self):
        """Clear all rows from the table."""
        # Clear existing widgets
        for row in range(self.model.rowCount()):
            for col in range(self.model.columnCount()):
                widget = self.table.indexWidget(self.model.index(row, col))
                if widget:
                    widget.deleteLater()
        
        # Clear model
        self.model.setRowCount(0)
        self.footer.setText('Students: 0')
    
    def _update_table_display(self, data):
        """Update the table display with current data."""
        try:
            # Clear existing widgets
            for row in range(self.model.rowCount()):
                for col in range(self.model.columnCount()):
                    widget = self.table.indexWidget(self.model.index(row, col))
                    if widget:
                        widget.deleteLater()
            
            # Set row count
            self.model.setRowCount(len(data))
            
            # Populate table with data and store records in model items
            for row, record in enumerate(data):
                # Store record data in the first column's item (UserRole)
                # This allows us to retrieve it later without maintaining self.data
                item = QStandardItem()
                item.setData(record, Qt.ItemDataRole.UserRole)
                self.model.setItem(row, COL_PHOTO, item)  # Store in first column
                
                # Create widgets for display
                self._create_student_row(row, record)
            
            # Update footer
            self.footer.setText(f'Students: {len(data)}')
            self.table.resizeRowsToContents()
            self.table.horizontalHeader().adjustSize()
            
        except Exception as e:
            print(f"Error updating table display: {e}")
    
    def _get_record_from_row(self, row: int):
        """Get student record data from model item for the given row."""
        if 0 <= row < self.model.rowCount():
            item = self.model.item(row, COL_PHOTO)
            if item:
                record = item.data(Qt.ItemDataRole.UserRole)
                return record
        return None
    
    def _get_all_records(self):
        """Get all student records from model items."""
        records = []
        for row in range(self.model.rowCount()):
            record = self._get_record_from_row(row)
            if record:
                records.append(record)
        return records
    
    def _create_student_row(self, row: int, record: tuple):
        """Create widgets for a single student row."""
        # Photo column
        photo_label = QLabel()
        photo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        photo_label.setText("No\nPhoto")
        photo_label.setStyleSheet('background-color: transparent; padding: 5px; text-align: center; margin: 0px;')
        photo_label.setFixedSize(PHOTO_WIDTH + PHOTO_PADDING, PHOTO_HEIGHT)
        
        if record[REC_PHOTO]:  # If has a photo
            try:
                pixmap = bytea_to_pixmap(record[REC_PHOTO])
                scaled_pixmap = pixmap.scaled(
                    photo_label.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                photo_label.setPixmap(scaled_pixmap)
                photo_label.setText("")
            except Exception as e:
                print(f"Error loading photo for row {row}: {e}")
        
        self.table.setIndexWidget(self.model.index(row, COL_PHOTO), photo_label)

        # Info column (ID + Name)
        name_label = QLabel(f"{record[REC_ID]}<br><strong>{record[REC_FNAME]} {record[REC_LNAME]}</strong>")
        name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        name_label.setFixedWidth(NAME_LABEL_WIDTH)
        self.table.setIndexWidget(self.model.index(row, COL_INFO), name_label)
        
        # Address column
        address_text = f"{record[REC_ADDRESS] or ''}\nCall: {record[REC_PHONE] or ''}"
        address_label = QLabel(address_text)
        address_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        address_label.setFixedWidth(ADDRESS_LABEL_WIDTH)
        self.table.setIndexWidget(self.model.index(row, COL_ADDRESS), address_label)
        
        # Last note column with menu button
        notes_widget = QWidget()
        notes_layout = QGridLayout(notes_widget)
        notes_layout.setContentsMargins(5, 5, 5, 5)
        
        date_str = ''
        if record[REC_DATE_TIME]:
            try:
                date_str = record[REC_DATE_TIME].strftime("%Y-%m-%d %H:%M:%S")
            except (AttributeError, ValueError):
                date_str = str(record[REC_DATE_TIME])
        
        note_text = f"{date_str}\n{record[REC_OBSERVED_BEHAVIOUR] or ''}"
        last_note = QLabel(note_text)
        last_note.setWordWrap(True)
        last_note.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea()
        scroll_area.setWidget(last_note)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(NOTES_SCROLL_HEIGHT)
        scroll_area.setMaximumHeight(NOTES_SCROLL_HEIGHT)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        notes_layout.addWidget(scroll_area, 0, 0)
        
        menu_btn = self.create_menu_btn(record, row)
        rtl = is_mostly_rtl(last_note.text())
        alignment = (Qt.AlignmentFlag.AlignTop | 
                    (Qt.AlignmentFlag.AlignLeft if rtl else Qt.AlignmentFlag.AlignRight))
        notes_layout.addWidget(menu_btn, 0, 0, alignment)
        
        self.table.setIndexWidget(self.model.index(row, COL_LAST_NOTE), notes_widget)
                
    
    def remove_from_group(self, stu):
        """Remove a student from the current group."""
        if not self._current_group_id or self._current_group_id == 'All':
            PopupNotifier.Notify(self, 'Error', 'No group selected or cannot remove from "All" group')
            return
        
        try:
            # Get current members
            result = app_context.database.fetchone(
                'SELECT members_ FROM groups WHERE id = %s;', 
                (self._current_group_id,))
            
            if not result or not result[0]:
                PopupNotifier.Notify(self, 'Error', 'Group not found or has no members')
                return
            
            members = result[0]
            student_id = str(stu['Id'])
            
            # Remove student ID from members string
            # Handle comma-separated format: ",id1,id2,id3"
            members_list = [m.strip() for m in str(members).split(',') if m.strip() and m.strip() != student_id]
            updated_members = ',' + ','.join(members_list) if members_list else ''
            
            # Update database
            app_context.database.execute(
                'UPDATE groups SET members_ = %s WHERE id = %s;',
                (updated_members, self._current_group_id))
            
            PopupNotifier.Notify(self, 'Success', 'Student removed from group successfully.')
            
            # Reload students to reflect changes
            for widget in self.findChildren(QComboBox):
                if isinstance(widget.model(), QStandardItemModel):
                    self.load_students(widget)
                    break
                    
        except Exception as e:
            PopupNotifier.Notify(self, 'Error', f'Failed to remove student from group: {str(e)}')
            
    def assign_edu_to_student(self,stu:dict):
            
            window = QApplication.activeWindow()
            window.add_page(EduResourcesView(window,[stu]))
        
    def send_edu_items(self, options='selected-list'):
        """Open educational resources view for selected or all students."""
        if options == 'all':
            self.table.selectAll()
        
        # Get selected row indices
        selected_rows = list({index.row() for index in self.table.selectedIndexes()})
        
        if len(selected_rows) == 0:
            PopupNotifier.Notify(self, '', 'No student selected')
            return
        
        # Build student list (get data from model items)
        stu_list = []
        for row_idx in selected_rows:
            record = self._get_record_from_row(row_idx)
            if record:
                stu_list.append({
                    "Id": record[REC_ID],
                    "Name": f"{record[REC_FNAME]} {record[REC_LNAME]}"
                })
        
        if not stu_list:
            PopupNotifier.Notify(self, 'Error', 'No valid students found')
            return
        
        window = QApplication.activeWindow()
        if window:
            window.add_page(EduResourcesView(window, stu_list))

    def delete_person(self, student_id: str, row_index: int):
        """Delete a student from the database after confirmation."""
        button = QMessageBox.warning(
            self,
            'DELETE STUDENT',
            f'ARE YOU SURE TO DELETE THE STUDENT WITH ID: \'{student_id}\'?\n\n'
            'This action cannot be undone.',
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.No)
        
        if button == QMessageBox.StandardButton.No:
            return
        
        try:
            # Delete in transaction order: dependencies first
            app_context.database.execute(
                'DELETE FROM observed_behaviours WHERE student_Id = %s;',
                (student_id,))
            
            app_context.database.execute(
                'DELETE FROM personal_info WHERE Id = %s;',
                (student_id,))
            
            # Remove from table
            self.model.removeRow(row_index)
            
            # Update footer
            self.footer.setText(f'Students: {self.model.rowCount()}')
            
            msg = f'Student {student_id} removed from database successfully.'
            PopupNotifier.Notify(self, "Success", msg, 'bottom-right', delay=3000, 
                               background_color='#353030', border_color="#2E7D32")

        except Exception as e:
            msg = f"Database error: {str(e)}"
            PopupNotifier.Notify(self, "Error", msg, 'bottom-right', delay=5000)
                
    def open_personal_info_dialog(self,data:Iterable):
            
            view =  PersonalInfoDialog(title='PERSONAL INFO')
            view.setFixedSize(800,400)
            if data: view.set_model_data(data)
            
            view.exec()

    def open_behaviour_list_page(self,data): self.parent().add_page(StudentActivityTrackingPage(student=data))

    def open_behaviour_note_editor(self,data):

            self.dialog = QDialog(parent=self)
            self.dialog.setWindowTitle('OBSERVED BEHAVIOUR EDITOR')
            self.dialog.setMinimumWidth(800)
            self.dialog.setMaximumWidth(800)
            self.dialog.setMaximumHeight(500)
            student_info_form = ObservedBehaviourWidget(profile_data= data, parent= self.dialog)
            
            # Set up the layout
            layout = QVBoxLayout()
            layout.addWidget(student_info_form)
        
            # Set the layout for the dialog
            self.dialog.setLayout(layout)
            self.dialog.exec()

    def find_in_list(self, search_text: str):
        """Search for students in the list based on search text."""
        if not search_text or not search_text.strip():
            # Clear selection if search is empty
            self.table.clearSelection()
            self.search_index = 0
            return

        search_text = search_text.strip().lower()
        model = self.table.model()
        row_count = model.rowCount()
        
        if row_count == 0:
            return

        found = False
        start_row = self.search_index
        
        # Search from current index to end, then wrap around
        for offset in range(row_count):
            row = (start_row + offset) % row_count
            
            # Search through all columns
            for col in range(model.columnCount()):
                index = model.index(row, col)
                widget = self.table.indexWidget(index)
                
                cell_text = ""
                if widget:
                    if isinstance(widget, QLabel):
                        cell_text = widget.text()
                    else:
                        # Try to extract text from widget
                        if hasattr(widget, "text"):
                            try:
                                cell_text = widget.text()
                            except Exception:
                                pass
                        elif hasattr(widget, "toPlainText"):
                            try:
                                cell_text = widget.toPlainText()
                            except Exception:
                                pass
                        else:
                            # Look for QLabel child
                            lbl = widget.findChild(QLabel)
                            if lbl:
                                cell_text = lbl.text()

                # Also check data directly for better search coverage (get from model)
                if not cell_text:
                    record = self._get_record_from_row(row)
                    if record:
                        # Search in ID, name, phone, address
                        searchable_text = ' '.join([
                            str(record[REC_ID]),
                            str(record[REC_FNAME] or ''),
                            str(record[REC_LNAME] or ''),
                            str(record[REC_PHONE] or ''),
                            str(record[REC_ADDRESS] or '')
                        ]).lower()
                        if search_text in searchable_text:
                            cell_text = searchable_text

                if cell_text and search_text in cell_text.lower():
                    # Found a match
                    self.table.selectRow(row)
                    self.table.setCurrentIndex(index)
                    self.table.scrollTo(index, QAbstractItemView.ScrollHint.EnsureVisible)
                    self.search_index = (row + 1) % row_count
                    found = True
                    break
            
            if found:
                break

        if not found:
            # Reset search index and show message
            self.search_index = 0
            PopupNotifier.Notify(self, "Search", f"No match found for '{search_text}'.", 
                               'bottom-right', delay=2000)

