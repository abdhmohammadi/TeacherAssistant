# Import pandas library for CSV data manipulation and processing
import pandas as pd
# Import Iterable from typing for type hints indicating collections of items
from typing import Iterable
# Import GUI widget classes from PySide6.QtWidgets for building user interface components
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QMessageBox, 
                               QCheckBox, QFileDialog, QTableView, QAbstractItemView,
                               QDialog, QScrollArea, QGridLayout, QApplication, QMenu,
                               QLabel, QLineEdit, QComboBox,QAbstractScrollArea, QPushButton)

# Import GUI utility classes from PySide6.QtGui for icons, actions, models, and display roles
from PySide6.QtGui import (Qt, QAction, QIcon, QStandardItemModel, QStandardItem)

# Import custom PopupNotifier for displaying notification messages to users
from PySideAbdhUI.Notify import PopupNotifier
# Import utility function to convert database bytea photo data to QPixmap for display
from processing.Imaging.Tools import bytea_to_pixmap
# Import text processing utility to detect right-to-left language text direction
from processing.text.text_processing import is_mostly_rtl
# Import ClassroomGroupViewModel for managing classroom group data models
from view_models.EduItems import ClassroomGroupViewModel
# Import custom widget for observing and recording student behavioral observations
from ui.widgets.widgets import ObservedBehaviourWidget
# Import dialog classes for various user input and selection operations
from ui.dialogs.dialogs import CustomAssignmentDialog, GroupSelectionDialog, GroupsManagerDialog, PersonalInfoDialog
# Import page class for displaying student activity tracking and learning progress
from ui.pages.activity_tracking import StudentActivityTrackingPage
# Import page class for displaying and assigning educational resources
from ui.pages.edu_resource_view import EduResourcesView
# Import global application context for accessing database and settings
from core.app_context import app_context 
# ==================================================================================
# UI LAYOUT CONFIGURATION CONSTANTS - Defines dimensions and spacing for UI elements
# ==================================================================================

# Width of student photo display in pixels
PHOTO_WIDTH = 90           
# Height of student photo display in pixels
PHOTO_HEIGHT = 130         
# Additional padding around photo widget in pixels
PHOTO_PADDING = 10         
# Fixed height for the last note scroll area in pixels
NOTES_SCROLL_HEIGHT = 120  
# Fixed width for student name/info label in pixels
NAME_LABEL_WIDTH = 150     
# Fixed width for address/contact label in pixels
ADDRESS_LABEL_WIDTH = 250  

# Fixed width for search input field in pixels
SEARCH_INPUT_WIDTH = 200   
# Number of rows to process per chunk when importing CSV files (prevents memory overload)
CSV_CHUNK_SIZE = 1000      

# ============================================================================
# TABLE COLUMN INDEX CONSTANTS - Maps column positions in QTableView display
# ============================================================================
# Column index for student photo display
COL_PHOTO = 0      
# Column index for student ID and name information
COL_INFO = 1       
# Column index for address and contact details
COL_ADDRESS = 2    
# Column index for last observed behaviour note
COL_LAST_NOTE = 3  

# ===================================================================================
# DATABASE RECORD FIELD INDEX CONSTANTS - Maps field positions in query result tuples
# ===================================================================================
# Query returns tuples with fields: Id, fname_, lname_, phone_, address_, photo_, date_time_, 
# observed_behaviour_, parent_name_, parent_phone_, additional_details_, birth_date_, gender_
# Student ID field index in database query result tuple
REC_ID = 0                   
# First name field index in database query result tuple
REC_FNAME = 1                
# Last name field index in database query result tuple
REC_LNAME = 2                
# Phone number field index in database query result tuple
REC_PHONE = 3                
# Address field index in database query result tuple
REC_ADDRESS = 4              
# Photo (bytea format) field index in database query result tuple
REC_PHOTO = 5                
# Date/time of last observation field index in database query result tuple
REC_DATE_TIME = 6            
# Last observed behaviour text field index in database query result tuple
REC_OBSERVED_BEHAVIOUR = 7   
# Parent name field index in database query result tuple
REC_PARENT_NAME = 8          
# Parent phone field index in database query result tuple
REC_PARENT_PHONE = 9         
# Additional details field index in database query result tuple
REC_ADDITIONAL_DETAILS = 10  
# Birth date field index in database query result tuple
REC_BIRTH_DATE = 11          
# Gender field index in database query result tuple
REC_GENDER = 12              
# Score field index if used for input tool
REC_SCORE = 13
# ============================================================================
# StudentListPage CLASS - Main UI page for displaying and managing student lists
# ============================================================================
class StudentListPage(QWidget):
    """Main page for displaying and managing student lists."""
    
    # Constructor method initializes the StudentListPage widget with parent reference
    def __init__(self, parent):
        # Call parent QWidget constructor to initialize base class
        super().__init__()
        # Set the parent widget for this page
        self.setParent(parent)
        
        # Track current position in search results for cycling through matches
        self.search_index = 0
        # Boolean flag to control whether multi-row selection is enabled
        self._multi_select_enabled = False
        # Store the ID of currently selected group for grouping operations
        self._current_group_id = None  
        
        # Call method to initialize all user interface components
        self.initUI()
    
    # Method to initialize and configure all user interface elements
    def initUI(self):

        # Set internal margins around the widget (left, top, right, bottom)
        self.setContentsMargins(10, 0, 10, 10)
        # Create main vertical layout container for the page
        main_layout = QVBoxLayout(self)
        # Set spacing between layout elements
        main_layout.setSpacing(10)

        # Create and configure title label for the page
        page_title = QLabel('STUDENT LIST')
        # Apply CSS class for heading styling
        page_title.setProperty('class', 'heading2')

        # Load list of classroom groups from database into model
        group_model = self.load_groups()
        # Create text input field for searching students
        search_input = QLineEdit()
        # Set placeholder text to guide user input
        search_input.setPlaceholderText('Search students...')
        # Limit search input field width
        search_input.setFixedWidth(SEARCH_INPUT_WIDTH)
        # Connect text change signal to search function
        search_input.textChanged.connect(self.find_in_list)

        # Create dropdown combo box for filtering students by classroom group
        class_filter_combo = QComboBox()
        # Set the data model containing list of groups
        class_filter_combo.setModel(group_model)
        # Connect selection change signal to load students for selected group
        class_filter_combo.currentIndexChanged.connect(lambda _: self.load_students(class_filter_combo))

        # Create options menu button with various student management actions
        edu_btn = self.create_more_option_menu(group_model)
        # Set tooltip text for button
        edu_btn.setToolTip('Open options menu')

        # Create horizontal layout for header controls (title, search, filter, menu)
        command_layout = QHBoxLayout()
        # Set spacing between header controls
        command_layout.setSpacing(10)
        # Add page title label to header layout
        command_layout.addWidget(page_title)
        # Add expandable empty space to push remaining items to the right
        command_layout.addStretch()
        # Add search input field to header
        command_layout.addWidget(search_input)
        # Add group filter dropdown to header
        command_layout.addWidget(class_filter_combo)
        # Add options menu button to header
        command_layout.addWidget(edu_btn)

        # Create intermediate widget to hold header layout
        header_widget = QWidget()
        # Set the header layout to the intermediate widget
        header_widget.setLayout(command_layout)
        # Add header widget to main layout
        main_layout.addWidget(header_widget)
        
        # Create table model with initial 0 rows and 4 columns (PHOTO, INFO, ADDRESS, LAST NOTE)
        self.model = QStandardItemModel(0, 4)
        # Set column header labels for table display
        self.model.setHorizontalHeaderLabels(['PHOTO', 'INFO', 'ADDRESS', 'LAST NOTE'])
        
        # Create table widget to display student data
        self.table = QTableView()
        # Set the data model for the table
        self.table.setModel(self.model)
        # Enable alternating row background colors for better readability
        self.table.setAlternatingRowColors(True)
        # Hide the row number column on the left side
        self.table.verticalHeader().hide()
        # Set selection behavior to select entire rows instead of individual cells
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Set selection mode to single row selection by default
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Adjust table size to fit content on first display
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        # Enable horizontal scrollbar when content exceeds visible width
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Enable vertical scrollbar when content exceeds visible height
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Hide grid lines between cells
        self.table.setShowGrid(False)

        # Get the table header to configure column sizing
        header = self.table.horizontalHeader()
        # Set photo column to fixed width
        self.table.setColumnWidth(COL_PHOTO, PHOTO_WIDTH + PHOTO_PADDING)
        # Configure photo column as fixed width (no resizing)
        header.setSectionResizeMode(COL_PHOTO, QHeaderView.ResizeMode.Fixed)
        # Configure info column to resize based on content
        header.setSectionResizeMode(COL_INFO, QHeaderView.ResizeMode.ResizeToContents)
        # Configure address column to resize based on content
        header.setSectionResizeMode(COL_ADDRESS, QHeaderView.ResizeMode.ResizeToContents)
        # Configure last note column to stretch and fill remaining space
        header.setSectionResizeMode(COL_LAST_NOTE, QHeaderView.ResizeMode.Stretch)
        # Add table widget to main layout
        main_layout.addWidget(self.table)

        self.footer_widget = QWidget()

        footer_layout = QVBoxLayout(self.footer_widget)

        # Create footer label for displaying student count statistics
        self.footer_list_count = QLabel('')
        # Align footer text to the right side
        self.footer_list_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        # Apply CSS class for caption styling
        self.footer_list_count.setProperty('class', 'caption')
        # Add footer to main layout
        #main_layout.addWidget(self.footer_list_count)

        self.footer_upload_btn = QPushButton('Read scores from file')
        self.footer_upload_btn.setVisible(False)
        self.footer_upload_btn.clicked.connect(lambda _:self.open_file_dialog())

        self.footer_save_btn = QPushButton('Save')
        self.footer_save_btn.setVisible(False)
        self.footer_save_btn.clicked.connect(lambda _, stu=None:self.on_save_score_clicked(stu))
        self.footer_cancel_btn = QPushButton('Cancel')
        self.footer_cancel_btn.setVisible(False)
        self.footer_cancel_btn.clicked.connect((lambda _: self.show_score_inputs(False)))
        
        footer_action_widget = QWidget()
        footer_actions_layout = QHBoxLayout(footer_action_widget)

        footer_actions_layout.addWidget(self.footer_list_count)
        footer_actions_layout.addStretch(0)
        footer_actions_layout.addWidget(self.footer_upload_btn)
        footer_actions_layout.addWidget(self.footer_save_btn)
        footer_actions_layout.addWidget(self.footer_cancel_btn)

        footer_layout.addWidget(footer_action_widget)

        main_layout.addWidget(self.footer_widget)

        # Select first group (usually "All") in the dropdown
        class_filter_combo.setCurrentIndex(0)
        # Load and display all students for the initial group selection
        self.load_students(class_filter_combo)

    # Method to display CSV import format requirements dialog message
    def show_csv_load_message(self):
        """Show warning message about CSV format requirements."""
        # Retrieve user's previous preference for showing this message
        option = app_context.settings_manager.find_value('csv_show_option_message')
        
        # If user previously chose "Don't show again", skip the message and return Ok
        if option:
            return QMessageBox.StandardButton.Ok

        # Define the expected column order for CSV import
        column_mapping = ["ID", "First Name", "Last Name", "Parent Name",
                         "Phone", "Address", "Parent Phone", "Additional Details",
                         "Gender", "Date"]
        
        # Create message box dialog for warning user about CSV format
        msg_box = QMessageBox(self)
        # Set the title of the message box window
        msg_box.setWindowTitle("CSV Import Warning")
        # Build detailed message explaining required CSV format and photoupload process
        msg = ('Note!\n\nThis feature currently only accepts CSV files with the following format.\n'
               'The columns of the CSV file must be as follows:\n\n'
               f'{", ".join(column_mapping)}\n\n'
               'If these are not followed, the data may not be saved as you expect.\n\n'
               'Additionally, if you need to upload a "photo" for each record, this must be done separately. '
               'After saving the profile, select the desired person from the list and upload the photo '
               'from the edit profile section.\n\n'
               'If you are sure, click "OK" to continue.')
        # Set the main message text to display
        msg_box.setText(msg)
        # Set warning icon for the message box
        msg_box.setIcon(QMessageBox.Icon.Warning)
        # Add OK and Cancel buttons to the message box
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

        # Create checkbox widget for "Don't show again" option
        checkbox = QCheckBox("Don't show again")
        # Add checkbox to the message box
        msg_box.setCheckBox(checkbox)
        # Execute the message box and capture user's button click response
        btn = msg_box.exec()

        # Save the user's preference for showing this message in future
        app_context.settings_manager.write({"csv_show_option_message": checkbox.isChecked()})
        # Return the button that was clicked
        return btn

    # Method to load student data from a CSV file into the database
    def load_from_csv(self):
        """Load student data from a CSV file."""
        # Show CSV format warning and check if user confirmed to continue
        if self.show_csv_load_message() == QMessageBox.StandardButton.Cancel:
            # User clicked Cancel, exit the method without loading
            return
    
        # Create file dialog for selecting CSV file
        dialog = QFileDialog(self)
        # Limit selection to existing files only
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        # Set file type filter to CSV files only
        dialog.setNameFilter("CSV Files (*.csv)")
        # Set descriptive title for the file dialog
        dialog.setWindowTitle("Select CSV File to Import")
        
        # Execute dialog and check if user selected a file
        if not dialog.exec():
            # User cancelled the file selection dialog
            return
            
        # Get the list of selected files from the dialog
        csv_file = dialog.selectedFiles()
        # Exit if no file was actually selected
        if not csv_file:
            return
            
        # Wrap the entire CSV loading process in try-except for error handling
        try:
            # Retrieve column names from the database personal_info table
            table_columns = app_context.database.get_columns('personal_info')
            # Notify user if unable to retrieve database column information
            if not table_columns:
                PopupNotifier.Notify(self, "Error", "Could not retrieve database columns.", 'bottom-right', delay=5000)
                return
            
            # Read only headers from CSV file without loading entire data yet
            csv_headers = pd.read_csv(csv_file[0], nrows=0).columns.tolist()

            # Define mapping between CSV column names and database field names
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

            # Create filtered mapping containing only valid CSV-to-database column pairs
            valid_mapping = {
                csv_col: sql_col 
                for csv_col, sql_col in column_mapping.items() 
                if csv_col in csv_headers and sql_col in table_columns
            }

            # Notify user if CSV file doesn't contain any recognizable columns
            if not valid_mapping:
                PopupNotifier.Notify(self, "Error", "No valid column mapping found. Please check CSV format.", 
                                      'bottom-right', delay=5000)
                return

            # Read CSV file in chunks to handle large files without memory overflow
            data = pd.read_csv(csv_file[0], chunksize=CSV_CHUNK_SIZE, dtype_backend='numpy_nullable')
            # Insert the CSV data into database using the valid column mapping
            app_context.database.bulk_insert_csv(data, 'personal_info', valid_mapping)
            
            # Build success notification message with filename
            msg = f'Successfully loaded data from {csv_file[0]}'
            # Notify user of successful data import
            PopupNotifier.Notify(self, "Success", msg, 'bottom-right', delay=5000)
            
            # Check if currently viewing "All" students group
            if self._current_group_id == 'All':
                # Find the group filter combo box widget
                for widget in self.findChildren(QComboBox):
                    # Check if this is the group filter combo box
                    if widget.model() == self.load_groups():
                        # Reload student list to show newly imported students
                        self.load_students(widget)
                        # Exit loop after reloading
                        break

        # Catch any exceptions that occur during CSV loading process
        except Exception as e:
            # Build error message with exception details
            msg = f'Error loading CSV: {str(e)}'
            # Notify user of the error
            PopupNotifier.Notify(self, "Error", msg, 'bottom-right', delay=5000)


    # Method to create the main options menu button with various student actions
    def create_more_option_menu(self, group_model=None) -> QPushButton:
        """Create the options menu button with all available actions."""
        # Create a generic menu button with minimal styling
        btn = QPushButton('')            
        # Apply grouped mini button CSS class for styling
        btn.setProperty('class', 'grouped_mini')
        # Set icon from resource file for menu button
        btn.setIcon(QIcon(":/icons/menu.svg"))
        # Set tooltip text displayed on hover
        btn.setToolTip('Open options menu')

        # Create dropdown menu attached to the button
        menu = QMenu(btn)
        # Attach menu to button (displays on click)
        btn.setMenu(menu)
        
        # Create action for toggling multi-row selection mode
        action_multi = QAction(icon=QIcon(':/icons/list-checks.svg'),
                               text='Enable multi-selection', parent=menu)
        # Make this action checkable (can be toggled on/off)
        action_multi.setCheckable(True)
        # Set initial state based on current multi-select setting
        action_multi.setChecked(self._multi_select_enabled)
        # Set tooltip explaining this action
        action_multi.setToolTip('Toggle multi-row selection in the students list')
        ##############################################################################
        # Create action for toggling multi-row selection mode
        action_enable_score_input = QAction(icon=QIcon(':/icons/list-checks.svg'), text='input score', parent=menu)
        # Make this action checkable (can be toggled on/off)
        #action_enable_score_input.setCheckable(True)
        # Set initial state based on current multi-select setting
        #action_enable_score_input.setChecked(self._multi_select_enabled)
        # Set tooltip explaining this action
        action_enable_score_input.setToolTip('enables input mode for each student to accept the score')
        ##############################################################################
        # Define callback function for multi-selection toggle
        def _toggle_multi(checked):
            # Update instance variable tracking multi-select state
            self._multi_select_enabled = checked
            # Check if table exists and is accessible
            if hasattr(self, 'table') and self.table is not None:
                # Determine selection mode based on checked state
                mode = (QAbstractItemView.SelectionMode.MultiSelection if checked 
                       else QAbstractItemView.SelectionMode.SingleSelection)
                # Apply the determined selection mode to the table
                self.table.setSelectionMode(mode)

        # Connect the toggle action to callback function
        action_multi.triggered.connect(_toggle_multi)
        action_enable_score_input.triggered.connect(lambda _: self.show_score_inputs(True))
        # Create action for adding a new student
        action_add = QAction(icon=QIcon(':/icons/id-card.svg'), text='Add new student', parent=menu)
        # Connect action to open personal info dialog with no data (new student)
        action_add.triggered.connect(lambda: self.open_personal_info_dialog(None))
        # Add the add student action to menu
        menu.addAction(action_add)

        # Create action for importing students from CSV file batch
        action_import = QAction(icon=QIcon(':/icons/sheet.svg'), text='Import from CSV file', parent=menu)
        # Set descriptive tooltip for CSV import action
        action_import.setToolTip('Opens file dialog to load list of students to database')
        # Connect action to CSV loading method
        action_import.triggered.connect(self.load_from_csv)
        # Add CSV import action to menu
        menu.addAction(action_import)

        # Add visual separator line in menu
        menu.addSeparator()
        # Add multi-selection toggle action to menu
        menu.addAction(action_multi)
        menu.addAction(action_enable_score_input)
        # Add second visual separator line
        menu.addSeparator()

        # Create action for assigning educational items to all students
        action_edu_all = QAction(icon=QIcon(':/icons/drafting-compass.svg'), 
                                text='Set Edu-Item to group', parent=menu)
        # Connect action to send educational items to all students
        action_edu_all.triggered.connect(lambda: self.send_edu_items('all'))
        # Add action to assign to all to menu
        menu.addAction(action_edu_all)

        # Create action for assigning educational items to selected students only
        action_edu_selected = QAction(icon=QIcon(':/icons/drafting-compass.svg'), 
                                     text='Set Edu-Item to selected students', parent=menu)
        # Connect action to send educational items to selected students
        action_edu_selected.triggered.connect(lambda: self.send_edu_items('selected-list'))
        # Add action to assign to selected to menu
        menu.addAction(action_edu_selected)
        
        # Add third visual separator line
        menu.addSeparator()
        
        # Create action for assigning selected students to a classroom group
        action_group_selected = QAction(icon=QIcon(':/icons/users-selected.svg'), 
                                       text='Group selected students', parent=menu)
        # Connect action to group dialog with selected students only
        action_group_selected.triggered.connect(
            lambda: self.show_group_dialog(group_model, 'selected-list'))
        # Add group selected action to menu
        menu.addAction(action_group_selected)
        
        # Create action for assigning all students to a classroom group
        action_group_all = QAction(icon=QIcon(':/icons/users.svg'), text='Group all', parent=menu)
        # Connect action to group dialog with all students
        action_group_all.triggered.connect(lambda: self.show_group_dialog(group_model, 'all'))
        # Add group all action to menu
        menu.addAction(action_group_all)
                    
        # Create action for opening group management dialog
        action_manage_groups = QAction(icon=QIcon(':/icons/combine.svg'), 
                                      text='Manage groups', parent=menu)
        # Connect action to group manager dialog
        action_manage_groups.triggered.connect(self.show_manage_groups_dialog)
        # Add manage groups action to menu
        menu.addAction(action_manage_groups)
        
        # Return the configured menu button
        return btn
    
    # Method to create individual context menu for each student row
    def create_stu_menu(self, record, row):
        # Create menu button for this student row
        btn = QPushButton('')
        # Set icon for dropdown menu
        btn.setIcon(QIcon(':/icons/menu.svg'))            
        # Apply grouped mini button CSS class for styling
        btn.setProperty('class','grouped_mini')

        # Create dropdown menu for this button
        menu = QMenu(btn)
        
        # Attach menu to button
        btn.setMenu(menu)
        
        # Create action to view student's learning progress and activities
        # Opens new page to view learning profile (not personal profile)
        action3 = QAction(icon=QIcon(':/icons/chart-spline.svg'), text= 'Learning progress',parent=menu)
        # Connect to method opening behavior/activity tracking page
        action3.triggered.connect(lambda _, data=record: self.open_behaviour_list_page(data))
        # Add learning progress action to menu
        menu.addAction(action3)

        # Create action for adding custom score/assignment for this student
        action7 = QAction(icon=QIcon(':/icons/chart-spline.svg'),
                          text= 'Add custom score',
                          statusTip='No need to Edu-Item',
                          parent=menu)
        # Connect to custom assignment dialog
        action7.triggered.connect(lambda _, stu=record[0]: self.on_save_score_clicked(stu))
        # Add custom score action to menu
        menu.addAction(action7)
        
        # Create action for assigning educational items to this student
        action1 = QAction(icon=QIcon(':/icons/drafting-compass.svg'), text= 'Assign Edu-item',parent=menu)
        # Connect to assign educational items method with student information
        action1.triggered.connect(lambda _, stu = {'Id':record[0], "Name":f'{record[1]} {record[2]}'}:self.assign_edu_to_student(stu))
        # Add assign edu-item action to menu
        menu.addAction(action1)
                    
        # Create action for writing behavioral observation notes
        action2 = QAction(icon=QIcon(':/icons/pencil.svg'),text='write behavioral observation', parent=menu)
        # Connect to behavior note editor dialog
        action2.triggered.connect(lambda _, data=record: self.open_behaviour_note_editor(data))
        # Add write observation action to menu
        menu.addAction(action2)

        # Create action for viewing/editing student's personal data
        action4 = QAction(icon=QIcon(':/icons/id-card.svg'),text='Personal data',parent=menu)
        # Connect to personal info dialog with student data
        action4.triggered.connect(lambda _, data=record: self.open_personal_info_dialog(data))
        # Add personal data action to menu
        menu.addAction(action4)
        
        # Add visual separator before destructive actions
        menu.addSeparator()

        # Create action for removing student from current group
        action5 = QAction(icon=QIcon(':/icons/x.svg'),text='Remove from group',parent=menu)
        # Connect to remove from group method with student info
        action5.triggered.connect(lambda _, stu = {'Id':record[0], "Name":f'{record[1]} {record[2]}'}: self.remove_from_group(stu))
        # Add remove from group action to menu
        menu.addAction(action5)

        # Create action for permanently deleting student from database
        action6 = QAction(icon=QIcon(':/icons/database-x.svg'), text= 'Remove from database',parent=menu)
        # Connect to delete person method with student ID and row index
        action6.triggered.connect(lambda _, student_id= record[0],r=row: self.delete_person(student_id,r))
        # Add remove from database action to menu
        menu.addAction(action6)

        # Return the configured student context menu button
        return btn

    def open_file_dialog(self):
        
        # Open file dialog with filters for txt and csv files
        file_path, _ = QFileDialog.getOpenFileName(self,"Select a file","","Text Files (*.txt);;CSV Files (*.csv);;All(*.txt;*.csv)")
        
        if file_path: 
            data = self.read_file(file_path)
            if len(data) != self.model.rowCount():
                PopupNotifier.Notify(self, message= f"The number of scores does not match the number of students.\nScores: {len(data)}\nStudents: {self.model.rowCount()}")
                return
            for i in range(len(data)):
                w = self.get_score_input(i)
                w.setText(data[i])
    
    def read_file(self, file_path):
        # Read file content and convert to list
        try:
            data = []
            # Determine file type and read accordingly
            if file_path.lower().endswith('.csv'):
                data = self.read_csv_file(file_path)
            else:  # Assume txt file
                data = self.read_txt_file(file_path)
            
            return data
        
        except Exception as e:
            PopupNotifier.Notify(self, message="Error reading file: {str(e)}")
            return []
    
    def read_txt_file(self, file_path):
        scores = []
        # Read txt file and convert to list"""
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read all lines and remove newline characters
            lines = [line.strip() for line in f.readlines()]
            
            for line in lines:
                data = line.split(',')
            
                for d in data:
                    if d !='' and d!=None:
                        scores.append(d)
        
        return scores

    def read_csv_file(self, file_path):
        # Read csv file and convert to list of rows
        scores = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Split CSV line by comma and clean each value
                row = [value.strip() for value in line.strip().split(',')]
                for r in row:
                    if r !='' and r !=None:
                        scores.append(r)
        
        return scores
    
        
    def on_save_score_clicked(self,stu_Id):

        data =  self.open_custom_assignment_dialog()

        if data:
            if stu_Id !="" and stu_Id !=None:
                # Call method to save custom assignment to database.
                # qb_Id = 99 is a free record in the database without a resource and is used to custom assignments
                status, message = self.update_custom_assignment(stu_Id, 99,data['description'],
                                                            data['feedback'],data['response_date'],
                                                            data['deadline'],data['assignment_date'],
                                                            data['score_earned'],data['max_score'])
            else:

                for row in range(self.model.rowCount()):

                    stu_Id = self.model.index(row,0).data(Qt.ItemDataRole.UserRole)[0]
                    
                    w = self.get_score_input(row)
                    score_earned = float(w.text() or 0.0)
                
                    status, message = self.update_custom_assignment(stu_Id, 99,data['description'],
                                                            data['feedback'],data['response_date'],
                                                            data['deadline'],data['assignment_date'],
                                                            score_earned, data['max_score'])
                
                self.show_score_inputs(False)

                message = f'Earned scores saved for {self.model.rowCount()} student(s).'

        else:
            message = 'Operation canceled'
        
        PopupNotifier.Notify(self,message=message)

    # Method to open custom assignment dialog for adding custom scores/assignments
    def open_custom_assignment_dialog(self):
        # Create custom assignment dialog instance
        dialog = CustomAssignmentDialog()
        # Execute dialog and wait for user response (Accepted or Rejected)
        # and check if user clicked OK/Accept button
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Retrieve form data from the dialog
           return dialog.get_data()
        else:
            return None
        
    # Method to insert custom assignment record into database
    def update_custom_assignment(self, stu_id: str, qb_Id: int, answer: str, feedback: str, 
                                 reply_date: str, deadline: str, assignment_date: str, 
                                 score_earned: float, max_score: float):
        
        # Wrap database insert in try-except for error handling
        try:
            # Define SQL INSERT statement for quests table
            cmd = ('INSERT INTO quests (qb_Id, student_id, max_point_, earned_point_, '
                    'assign_date_, deadline_, reply_date_, answer_, feedback_) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);')

            # Execute INSERT statement with parameterized query to prevent SQL injection
            app_context.database.execute(cmd, 
                                            (qb_Id, stu_id, max_score, score_earned, assignment_date, 
                                            deadline, reply_date, answer, feedback))

            # Set success status flag
            status = True
            # Build success message
            message = f'Custom assignment was saved successfully for student {stu_id}.'

        # Catch any exceptions from database operation
        except Exception as e:
            # Set failure status flag
            status = False
            # Build error message with exception details
            message = f'Error saving assignment: {str(e)}'

        # Return status and message tuple
        return status, message

        
    def show_group_dialog(self, model: QStandardItemModel, option='selected-list'):
        """Show dialog to assign selected students to a group."""
        # If option is 'all', select all students in the table
        if option == 'all':
            # Select all rows in the table
            self.table.selectAll()
        # If option is 'selected-list', check if at least one student is selected
        elif not self.table.selectedIndexes(): 
            # Notify user to select at least one student
            PopupNotifier.Notify(self, '', 'First select at least one student')
            # Exit method without opening dialog
            return

        # Create group selection dialog with available groups model
        dlg = GroupSelectionDialog(model)
        
        # Execute dialog and check if user confirmed selection
        if dlg.exec() != QDialog.DialogCode.Accepted:
            # User cancelled the dialog
            return
            
        # Wrap group assignment in try-except for error handling
        try:
            # Get the item from model at the selected group row
            item = model.item(dlg.selected_group.row())
            # Check if item was successfully retrieved
            if not item:
                # Notify user of invalid selection
                PopupNotifier.Notify(self, 'Error', 'Invalid group selection')
                return
                
            # Get the ClassroomGroupViewModel data from the item
            group: ClassroomGroupViewModel = item.data(Qt.ItemDataRole.UserRole)
            # Validate that we have a valid group object (skip "All" string option)
            if not group or isinstance(group, str):  # Skip "All" option
                # Notify user that group selection is invalid
                PopupNotifier.Notify(self, 'Error', 'Please select a valid group')
                return
            
            # Collect student IDs from selected rows (get data from model items)
            selected_rows = {index.row() for index in self.table.selectedIndexes()}
            # Initialize empty list to hold student IDs
            student_ids = []
            # Iterate through each selected row
            for row in selected_rows:
                # Retrieve record data from model item for this row
                record = self._get_record_from_row(row)
                # Check if record was successfully retrieved
                if record:
                    # Extract student ID and add to list as string
                    student_ids.append(str(record[REC_ID]))
            
            # Check if any valid students were found
            if not student_ids:
                # Notify user of invalid student selection
                PopupNotifier.Notify(self, 'Error', 'No valid students selected')
                return
            
            # Join student IDs with commas, add leading comma for format compatibility
            id_list = ',' + ','.join(student_ids)  # Add leading comma for format
            
            # Call group model method to add students to the group
            status, message = group.model.add_member(int(group.Id), id_list)
            
            # If operation was successful
            if status:
                # Reload groups combo box to refresh displayed groups
                for widget in self.findChildren(QComboBox):
                    # Check if this combo box uses the group model
                    if widget.model() == model:
                        # Refresh the group model with fresh data
                        widget.setModel(self.load_groups())
                        # Exit loop after refreshing
                        break
            
            # Notify user of operation result
            PopupNotifier.Notify(self, '', message)
            
        # Catch any exceptions from group assignment process
        except Exception as e:
            # Notify user of operation failure with error details
            PopupNotifier.Notify(self, 'Error', f'Failed to add students to group: {str(e)}')
        
    # Method to open dialog for managing classroom groups
    def show_manage_groups_dialog(self):
        """Show dialog for managing classroom groups."""
        # Wrap dialog opening in try-except for error handling
        try:
            # Get a cursor from the database connection for the dialog
            # Note: The dialog should be refactored to use app_context.database directly
            cursor = app_context.database.connection.cursor()
            # Create group manager dialog with database cursor
            dlg = GroupsManagerDialog(cursor)
            # Set fixed dialog dimensions for consistent appearance
            dlg.setFixedSize(675, 500)
            # Execute dialog and capture result (Accepted or Rejected)
            result = dlg.exec()
            # Close the cursor to free database resources
            cursor.close()  # Clean up cursor after dialog closes
            
            # Reload groups after dialog closes if changes were made
            if result == QDialog.DialogCode.Accepted:
                # Find all combo box widgets in the interface
                for widget in self.findChildren(QComboBox):
                    # Check if this combo box's model is a QStandardItemModel
                    if isinstance(widget.model(), QStandardItemModel):
                        # Reload groups from database into the combo box
                        widget.setModel(self.load_groups())
                        # Exit loop after finding and updating the combo box
                        break
        # Catch any exceptions from group management dialog operation
        except Exception as e:
            # Notify user of error with exception details
            PopupNotifier.Notify(self, 'Error', f'Failed to open groups manager: {str(e)}')
            
    # Method to load all classroom groups from database into a model
    def load_groups(self):
            # Create new QStandardItemModel to hold group items
            model = QStandardItemModel()
            # Check if database connection is available and initialized
            if not app_context.database:
                # Return empty model if database not available
                return model
            
            # Execute database query to fetch all group records with their details
            groups = app_context.database.fetchall('SELECT id, grade_, book_, title_, events_, members_, description_ FROM groups;')                
            
            # Create default "All" item as the first option in the list
            item = QStandardItem('All')
            # Set user data to 'All' string to identify this as the all groups option
            item.setData('All', Qt.ItemDataRole.UserRole)
            # Add "All" item to the beginning of the model
            model.appendRow(item)

            # Iterate through each group record from the database query results
            for row , record in enumerate(groups): 
                # Create new QStandardItem for displaying this group in the list
                item = QStandardItem()

                # Set the display text to the group title (from record[3])
                item.setData(record[3],Qt.ItemDataRole.DisplayRole)

                # Create new ClassroomGroupViewModel instance for storing group data
                group = ClassroomGroupViewModel()

                # Populate group object properties from database record fields
                # record[0] contains the group ID
                group.Id = record[0]
                # record[1] contains the grade level, converted to string
                group.grade = str(record[1])
                # record[2] contains the book reference
                # record[2] contains the book reference
                group.book = record[2]
                # record[3] contains the group title/name
                group.title = record[3]
                # record[4] contains events information for the group
                group.events = record[4]
                # record[5] contains comma-separated list of member student IDs
                group.members = record[5]
                # record[6] contains the group description
                group.description = record[6]
                # Store the populated group object in the item's user data
                item.setData(group, Qt.ItemDataRole.UserRole)
                # Add the item to the model
                model.appendRow(item)

            # Return the populated model containing all groups
            return model
    
    # Method to completely clear the table by creating and setting a new model
    def clear_by_new_model(self):
        """Clear everything by creating a new model"""
        # Remove all old widgets from the table to free memory
        for row in range(self.model.rowCount()):
            # Iterate through all columns in the current row
            for col in range(self.model.columnCount()):
                # Get the widget displayed at this cell index
                widget = self.table.indexWidget(self.model.index(row, col))
                # Check if a widget exists at this location
                if widget:
                    # Schedule widget for deletion after executing current code
                    widget.deleteLater()
        
        # Create a new empty QStandardItemModel with 0 rows and 4 columns
        new_model = QStandardItemModel(0, 4)  # Empty model
        # Set column headers for the new model
        new_model.setHorizontalHeaderLabels(['PHOTO', 'INFO', 'ADDRESS', 'LAST NOTE'])
        
        # Set the new model as the table's data source
        self.table.setModel(new_model)
        # Update instance variable reference to point to the new model
        self.model = new_model  # Update reference
        
        # Get header object from table to configure column resizing
        header = self.table.horizontalHeader()
        # Set photo column to fixed width (no resizing)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        # Set info column to resize based on content
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        # Set address column to resize based on content
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        # Set last note column to stretch and fill remaining space
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        # Set photo column width to fixed pixels
        self.table.setColumnWidth(0, 150)
    
        # Print debug message to console for confirmation
        print("Table completely reset with new model")
    
    # Method to load and display students from database based on group selection
    def load_students(self, sender: QComboBox):
        # Wrap database loading in try-except for error handling
        try:
            # Get the selected item's user data (either 'All' string or ClassroomGroupViewModel)
            selected = sender.currentData(Qt.ItemDataRole.UserRole)
            
            # Build base SQL query with proper parameterization to prevent SQL injection
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
            
            # Handle group filtering with parameterized query for safety
            if isinstance(selected, str) or not selected:
                # Load all students from the database (no group filter)
                query = base_query + ' ORDER BY t1.fname_, t1.lname_;'
                # No parameters needed for all students query
                params = None
                # Track that we're viewing all students
                self._current_group_id = 'All'
            else:
                # Filter by group members - use parameterized query for safety
                # Parse members string (format: ",id1,id2,id3" or "id1,id2,id3")
                members_str = str(selected.members) if selected.members else ''
                # Split by comma and strip whitespace from each ID
                members_list = [m.strip() for m in members_str.split(',') if m.strip()]
                
                # Check if the group has any members
                if not members_list:
                    # Group is empty, clear the table display
                    self._clear_table()
                    return
                
                # Use IN clause with parameterized query (safer than ANY with array)
                # Create placeholders for each member ID
                placeholders = ','.join(['%s'] * len(members_list))
                # Build query to filter by group members
                query = base_query + f' WHERE t1.Id IN ({placeholders}) ORDER BY t1.fname_, t1.lname_;'
                # Set parameters to the member IDs
                params = tuple(members_list)
                # Track the currently selected group ID
                self._current_group_id = selected.Id
            
            # Execute the database query with parameters
            data = app_context.database.fetchall(query, params) if params else app_context.database.fetchall(query)
            
            # Update table display with retrieved student data
            self._update_table_display(data)
            
        # Catch any exceptions from the loading process
        except Exception as e:
            # Build error message with exception details
            error_msg = f"Error loading students: {str(e)}"
            # Print error to console for debugging
            print(error_msg)
            # Notify user of the error
            PopupNotifier.Notify(self, "Error", error_msg, 'bottom-right', delay=5000)
            # Clear the table display on error
            self._clear_table()
    
    # Method to clear all rows and data from the table
    def _clear_table(self):
        """Clear all rows from the table."""
        # Iterate through all rows in the current model
        for row in range(self.model.rowCount()):
            # Iterate through all columns in the current row
            for col in range(self.model.columnCount()):
                # Get the widget displayed at this table index
                widget = self.table.indexWidget(self.model.index(row, col))
                # Check if a widget exists at this location
                if widget:
                    # Schedule widget for deletion
                    widget.deleteLater()
        
        # Set model row count to 0 to remove all rows
        self.model.setRowCount(0)
        # Update footer to show zero students
        self.footer_list_count.setText('Students: 0')
    
    # Method to update table display with student data
    def _update_table_display(self, data):

        # Wrap table update in try-except for error handling
        try:
            # Remove all existing widgets from the table
            for row in range(self.model.rowCount()):
                # Iterate through all columns
                for col in range(self.model.columnCount()):
                    # Get the widget at this cell
                    widget = self.table.indexWidget(self.model.index(row, col))
                    # Check if widget exists
                    if widget:
                        # Delete the widget
                        widget.deleteLater()
            
            # Set the table model row count to match number of records
            self.model.setRowCount(len(data))
            
            # Populate table with data and store records in model items
            for row, record in enumerate(data):
                # Store record data in the first column's item (UserRole)
                # This allows us to retrieve it later without maintaining self.data
                item = QStandardItem()
                # Store the entire record tuple in the first column item
                item.setData(record, Qt.ItemDataRole.UserRole)
                # Set the item in the model (store in first column)
                self.model.setItem(row, COL_PHOTO, item)  # Store in first column
                
                # Create and display widgets for this student row
                self._create_student_row(row, record)
            
            # Update footer with count of loaded students
            self.footer_list_count.setText(f'Students: {len(data)}')
            # Resize table rows to fit content
            self.table.resizeRowsToContents()
            # Adjust horizontal header size
            self.table.horizontalHeader().adjustSize()
            
        # Catch exceptions from table update process
        except Exception as e:
            # Print error message to console
            print(f"Error updating table display: {e}")
    
    # Method to retrieve student record data from model item for specific row
    def _get_record_from_row(self, row: int):
        """Get student record data from model item for the given row."""
        # Check if row index is within valid range (0 to row count-1)
        if 0 <= row < self.model.rowCount():
            # Get the item from the first column (photo column) where we stored the record
            item = self.model.item(row, COL_PHOTO)
            # Check if item successfully retrieved
            if item:
                # Extract the stored record from the item's user data role
                record = item.data(Qt.ItemDataRole.UserRole)
                # Return the record tuple
                return record
        # Return None if row is invalid or no record found
        return None
    
    # Method to retrieve all student records currently displayed in table
    def _get_all_records(self):
        """Get all student records from model items."""
        # Initialize empty list to store records
        records = []
        # Iterate through each row in the table model
        for row in range(self.model.rowCount()):
            # Retrieve record for the current row
            record = self._get_record_from_row(row)
            # Check if record was successfully retrieved
            if record:
                # Add record to list
                records.append(record)
        # Return list of all student records
        return records
    

    def get_score_input(self, row):
        # Get the widget at specific row and column
        index = self.model.index(row, COL_INFO)
        widget = self.table.indexWidget(index)
    
        if widget:
            # Find QLineEdit in the widget's layout
            return widget.findChild(QLineEdit)
        
        return None

    def show_score_inputs(self, b:bool):
        
        for row in range(self.model.rowCount()):
            widget = self.get_score_input(row)
            widget.setVisible(b)
        
        self.footer_save_btn.setVisible(b)
        self.footer_cancel_btn.setVisible(b)
        self.footer_upload_btn.setVisible(b)


    # Method to create and configure widgets for displaying a single student row
    def _create_student_row(self, row: int, record: tuple):
        
        # Create label widget for displaying student photo
        photo_label = QLabel()
        # Center photo content both horizontally and vertically
        photo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        # Set default text for placeholder when no photo available
        photo_label.setText("No\nPhoto")
        # Apply stylesheet styling for the photo label
        photo_label.setStyleSheet('background-color: transparent; padding: 5px; text-align: center; margin: 0px;')
        # Set fixed size for photo label based on constants
        photo_label.setFixedSize(PHOTO_WIDTH + PHOTO_PADDING, PHOTO_HEIGHT)
        
        # Check if student record has a photo (bytea data)
        if record[REC_PHOTO]:  # If has a photo
            # Wrap photo loading in try-except for error handling
            try:
                # Convert database bytea format to QPixmap image object
                pixmap = bytea_to_pixmap(record[REC_PHOTO])
                # Scale pixmap to fit label size maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    photo_label.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                # Display the scaled pixmap in the label
                photo_label.setPixmap(scaled_pixmap)
                # Clear placeholder text now that we have a photo
                photo_label.setText("")
            # Catch exceptions from photo conversion process
            except Exception as e:
                # Print error message to console for debugging
                print(f"Error loading photo for row {row}: {e}")
        
        # Set the photo label widget in the photo column of the table
        self.table.setIndexWidget(self.model.index(row, COL_PHOTO), photo_label)

        # Create label for displaying student ID and name information
        name_label = QLabel(f"{record[REC_ID]}<br><strong>{record[REC_FNAME]} {record[REC_LNAME]}</strong>")
        # Align content to top and left
        name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        # Set fixed width for the name label
        name_label.setFixedWidth(NAME_LABEL_WIDTH)
        #self.table.setIndexWidget(self.model.index(row, COL_INFO), name_label)

        # Create line-edit widget to input score for student
        # this enables input mode for classroom(not individual)
        score_input = QLineEdit('')   
        score_input.setPlaceholderText('score')
        #score_input.setStyleSheet('margin: 2px;')
        score_input.setFixedWidth(NAME_LABEL_WIDTH)
        # Align content to top and left
        score_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        score_input.setVisible(False)
        # Set the name label widget in the info column of the table
        #self.table.setIndexWidget(self.model.index(row, 1), score_input)
        name_widget = QWidget()
        name_layout = QVBoxLayout(name_widget)
        name_layout.addWidget(name_label)
        name_layout.addWidget(score_input)
        
        self.table.setIndexWidget(self.model.index(row, COL_INFO), name_widget)

        # Build address and phone information text
        address_text = f"{record[REC_ADDRESS] or ''}\nCall: {record[REC_PHONE] or ''}"
        # Create label for displaying address and contact information
        address_label = QLabel(address_text)
        # Align content to top and left
        address_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        # Set fixed width for address label
        address_label.setFixedWidth(ADDRESS_LABEL_WIDTH)
        # Set the address label widget in the address column of the table
        self.table.setIndexWidget(self.model.index(row, COL_ADDRESS), address_label)
        
        # Create container widget for last note column (includes scrollable notes and menu button)
        notes_widget = QWidget()
        # Create grid layout for organizing notes and menu button
        notes_layout = QGridLayout(notes_widget)
        # Set internal margins for the layout
        notes_layout.setContentsMargins(5, 5, 5, 5)
        
        # Initialize empty string for date/time display
        date_str = ''
        # Check if record has a date/time value
        if record[REC_DATE_TIME]:
            # Try to format date/time as string with specific format
            try:
                # Format datetime object to readable string
                date_str = record[REC_DATE_TIME].strftime("%Y-%m-%d %H:%M:%S")
            # Catch exceptions if date is in unexpected format
            except (AttributeError, ValueError):
                # Convert directly to string as fallback
                date_str = str(record[REC_DATE_TIME])
        
        # Build note text combining date and observed behavior text
        note_text = f"{date_str}\n{record[REC_OBSERVED_BEHAVIOUR] or ''}"
        # Create label to display the combined note text
        last_note = QLabel(note_text)
        # Enable text wrapping so long notes display properly
        last_note.setWordWrap(True)
        # Align content to the top
        last_note.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Create scrollable area to contain the note text
        scroll_area = QScrollArea()
        # Set the note label as the content of the scroll area
        scroll_area.setWidget(last_note)
        # Allow the scroll area to resize its content
        scroll_area.setWidgetResizable(True)
        # Set minimum height for scroll area
        scroll_area.setMinimumHeight(NOTES_SCROLL_HEIGHT)
        # Set maximum height for scroll area
        scroll_area.setMaximumHeight(NOTES_SCROLL_HEIGHT)
        # Hide the frame border of the scroll area
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        # Add scroll area to the layout (row 0, column 0)
        notes_layout.addWidget(scroll_area, 0, 0)
        
        # Create context menu button for student actions
        menu_btn = self.create_stu_menu(record, row)
        # Check if note text is right-to-left language (e.g., Arabic, Hebrew)
        rtl = is_mostly_rtl(last_note.text())
        # Set button alignment based on text direction
        alignment = (Qt.AlignmentFlag.AlignTop | 
                    (Qt.AlignmentFlag.AlignLeft if rtl else Qt.AlignmentFlag.AlignRight))
        # Add menu button to layout with appropriate alignment
        notes_layout.addWidget(menu_btn, 0, 0, alignment)
        
        # Set the composite notes widget in the last note column of the table
        self.table.setIndexWidget(self.model.index(row, COL_LAST_NOTE), notes_widget)

    # Method to remove a student from the currently selected classroom group
    def remove_from_group(self, stu):
        """Remove a student from the current group."""
        # Check if a valid group is selected (not "All" or None)
        if not self._current_group_id or self._current_group_id == 'All':
            # Notify user that no valid group selected
            PopupNotifier.Notify(self, 'Error', 'No group selected or cannot remove from "All" group')
            return
        
        # Wrap removal operation in try-except for error handling
        try:
            # Query database to get current members list for the group
            result = app_context.database.fetchone(
                'SELECT members_ FROM groups WHERE id = %s;', 
                (self._current_group_id,))
            
            # Check if group and its members data exist
            if not result or not result[0]:
                # Notify user if group not found
                PopupNotifier.Notify(self, 'Error', 'Group not found or has no members')
                return
            
            # Get the members string from the query result
            members = result[0]
            # Convert student ID to string for comparison
            student_id = str(stu['Id'])
            
            # Remove student ID from members string
            # Handle comma-separated format: ",id1,id2,id3"
            # Split by comma, strip whitespace, and filter out the target student ID
            members_list = [m.strip() for m in str(members).split(',') if m.strip() and m.strip() != student_id]
            # Re-join members with comma, preserve leading comma if list not empty
            updated_members = ',' + ','.join(members_list) if members_list else ''
            
            # Update database with modified members list
            app_context.database.execute(
                'UPDATE groups SET members_ = %s WHERE id = %s;',
                (updated_members, self._current_group_id))
            
            # Notify user of successful removal
            PopupNotifier.Notify(self, 'Success', 'Student removed from group successfully.')
            
            # Reload students to reflect the removed member
            for widget in self.findChildren(QComboBox):
                # Check if this is a standard model based combo box
                if isinstance(widget.model(), QStandardItemModel):
                    # Reload students for the current group
                    self.load_students(widget)
                    # Exit after reloading
                    break
                    
        # Catch exceptions from removal process
        except Exception as e:
            # Notify user of operation failure with error details
            PopupNotifier.Notify(self, 'Error', f'Failed to remove student from group: {str(e)}')
            
    # Method to open educational resources view for assigning items to a student
    def assign_edu_to_student(self, stu: dict):
        # Get the active application window
        window = QApplication.activeWindow()
        # Add a new page with educational resources view for this student
        window.add_page(EduResourcesView(window, [stu]))
        
    # Method to send/assign educational items to selected or all students
    def send_edu_items(self, options='selected-list'):
        """Open educational resources view for selected or all students."""
        # Check if assigning to all students
        if options == 'all':
            # Select all rows in the table
            self.table.selectAll()
        
        # Get set of selected row indices to eliminate duplicates
        selected_rows = list({index.row() for index in self.table.selectedIndexes()})
        
        # Check if any students are selected
        if len(selected_rows) == 0:
            # Notify user to select at least one student
            PopupNotifier.Notify(self, '', 'No student selected')
            return
        
        # Build student list by retrieving data from model items
        stu_list = []
        # Iterate through each selected row
        for row_idx in selected_rows:
            # Retrieve record for this row from model item
            record = self._get_record_from_row(row_idx)
            # Check if record was successfully retrieved
            if record:
                # Create student dictionary with ID and name
                stu_list.append({
                    "Id": record[REC_ID],
                    "Name": f"{record[REC_FNAME]} {record[REC_LNAME]}"
                })
        
        # Check if any valid students were found
        if not stu_list:
            # Notify user of invalid student selection
            PopupNotifier.Notify(self, 'Error', 'No valid students found')
            return
        
        # Get the active application window
        window = QApplication.activeWindow()
        # Check if window reference exists
        if window:
            # Add new page with educational resources view
            window.add_page(EduResourcesView(window, stu_list))

    # Method to delete a student from the database after user confirmation
    def delete_person(self, student_id: str, row_index: int):
        """Delete a student from the database after confirmation."""
        # Show warning dialog asking for confirmation before deletion
        button = QMessageBox.warning(
            self,
            'DELETE STUDENT',
            f'ARE YOU SURE TO DELETE THE STUDENT WITH ID: \'{student_id}\'?\n\n'
            'This action cannot be undone.',
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.No)
        
        # Check if user clicked No button to cancel deletion
        if button == QMessageBox.StandardButton.No:
            # Exit method without deleting
            return
        
        # Wrap deletion in try-except for error handling
        try:
            # Delete in transaction order: dependencies first (observed_behaviours before personal_info)
            # Delete all recorded behavioral observations for this student
            app_context.database.execute(
                'DELETE FROM observed_behaviours WHERE student_Id = %s;',
                (student_id,))
            
            # Delete the student's personal information from database
            app_context.database.execute(
                'DELETE FROM personal_info WHERE Id = %s;',
                (student_id,))
            
            # Remove the row from the table display
            self.model.removeRow(row_index)
            
            # Update footer with new student count
            self.footer_list_count.setText(f'Students: {self.model.rowCount()}')
            
            # Build success message
            msg = f'Student {student_id} removed from database successfully.'
            # Notify user of successful deletion with success styling
            PopupNotifier.Notify(self, "Success", msg, 'bottom-right', delay=3000, 
                               background_color='#353030', border_color="#2E7D32")

        # Catch any exceptions from database deletion
        except Exception as e:
            # Build error message with exception details
            msg = f"Database error: {str(e)}"
            # Notify user of deletion failure
            PopupNotifier.Notify(self, "Error", msg, 'bottom-right', delay=5000)
                
    # Method to open personal information dialog for viewing/editing student data
    def open_personal_info_dialog(self, data: Iterable):
        # Create instance of personal information dialog
        view = PersonalInfoDialog(title='PERSONAL INFO')
        # Set fixed dialog window size
        view.setFixedSize(800, 400)
        # If data is provided, populate dialog with student information
        if data: 
            # Set the student data in the dialog
            view.set_model_data(data)
        
        # Execute dialog and wait for user interaction
        view.exec()

    # Method to open student activity tracking page to view learning progress
    def open_behaviour_list_page(self, data): 
        # Add new page to show student's learning progress and activity tracking
        self.parent().add_page(StudentActivityTrackingPage(student=data))

    # Method to open dialog for recording behavioral observations about a student
    def open_behaviour_note_editor(self, data):
        # Create new dialog window for editing behavioral observations
        self.dialog = QDialog(parent=self)
        # Set the dialog window title
        self.dialog.setWindowTitle('OBSERVED BEHAVIOUR EDITOR')
        # Set minimum window width
        self.dialog.setMinimumWidth(800)
        # Set maximum window width
        self.dialog.setMaximumWidth(800)
        # Set maximum window height
        self.dialog.setMaximumHeight(500)
        # Create widget for entering behavioral observations
        student_info_form = ObservedBehaviourWidget(profile_data= data, parent= self.dialog)
        
        # Create vertical layout container for the dialog
        layout = QVBoxLayout()
        # Add the behavioral observation widget to the layout
        layout.addWidget(student_info_form)
        
        # Set the layout for the dialog
        self.dialog.setLayout(layout)
        # Execute the dialog and wait for user completion
        self.dialog.exec()

    # Method to search for students in the list by name, ID, phone, or address
    def find_in_list(self, search_text: str):
        """Search for students in the list based on search text."""
        # Check if search text is empty or whitespace only
        if not search_text or not search_text.strip():
            # Clear any selected rows
            self.table.clearSelection()
            # Reset search position to beginning
            self.search_index = 0
            # Exit method without searching
            return

        # Convert search text to lowercase for case-insensitive comparison
        search_text = search_text.strip().lower()
        # Get the model from the table
        model = self.table.model()
        # Get total number of rows in the table
        row_count = model.rowCount()
        
        # Exit if table is empty
        if row_count == 0:
            return

        # Flag to track if a match was found
        found = False
        # Remember starting row for cycling through results
        start_row = self.search_index
        
        # Search from current index to end, then wrap around to beginning
        for offset in range(row_count):
            # Calculate row index with wrapping (cycle back to beginning if at end)
            row = (start_row + offset) % row_count
            
            # Search through all columns in the current row
            for col in range(model.columnCount()):
                # Get the model index for this cell
                index = model.index(row, col)
                # Get the widget associated with this cell
                widget = self.table.indexWidget(index)
                
                # Initialize empty string for extracted cell text
                cell_text = ""
                # Check if a widget exists at this cell
                if widget:
                    # If widget is a simple label, get its text directly
                    if isinstance(widget, QLabel):
                        cell_text = widget.text()
                    else:
                        # Try to extract text from other widget types
                        if hasattr(widget, "text"):
                            # Try text() method for text-based widgets
                            try:
                                cell_text = widget.text()
                            except Exception:
                                # Fail silently if method doesn't work
                                pass
                        elif hasattr(widget, "toPlainText"):
                            # Try toPlainText() method for text edit widgets
                            try:
                                cell_text = widget.toPlainText()
                            except Exception:
                                # Fail silently if method doesn't work
                                pass
                        else:
                            # Look for a QLabel child widget within composite widget
                            lbl = widget.findChild(QLabel)
                            if lbl:
                                # Extract text from child label
                                cell_text = lbl.text()

                # Also check record data directly for better search coverage
                if not cell_text:
                    # Retrieve the student record from model item
                    record = self._get_record_from_row(row)
                    if record:
                        # Build searchable text from ID, name, phone, address fields
                        searchable_text = ' '.join([
                            str(record[REC_ID]),
                            str(record[REC_FNAME] or ''),
                            str(record[REC_LNAME] or ''),
                            str(record[REC_PHONE] or ''),
                            str(record[REC_ADDRESS] or '')
                        ]).lower()
                        # Check if search text is found in searchable fields
                        if search_text in searchable_text:
                            # Update cell_text if found
                            cell_text = searchable_text

                # Check if search term is found in the cell text
                if cell_text and search_text in cell_text.lower():
                    # Found a match - select and highlight this row
                    self.table.selectRow(row)
                    # Set this as the current index for the table
                    self.table.setCurrentIndex(index)
                    # Scroll table to ensure the found row is visible
                    self.table.scrollTo(index, QAbstractItemView.ScrollHint.EnsureVisible)
                    # Update search position to next row for cycling through results
                    self.search_index = (row + 1) % row_count
                    # Set flag indicating match was found
                    found = True
                    # Exit column loop since match is found
                    break
            
            # Exit row loop if match was found
            if found:
                break

        # Execute this block if no match was found
        if not found:
            # Reset search index to beginning for next search
            self.search_index = 0
            # Notify user that no matching student was found
            PopupNotifier.Notify(self, "Search", f"No match found for '{search_text}'.", 
                               'bottom-right', delay=2000)

