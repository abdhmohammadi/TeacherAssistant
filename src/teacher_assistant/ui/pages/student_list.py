
import pandas as pd
from typing import Iterable
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QMessageBox, QLabel, QLineEdit, QComboBox,
                               QCheckBox, QFileDialog, QTableView, QAbstractItemView, QAbstractScrollArea, QPushButton,
                               QDialog, QScrollArea, QGridLayout, QApplication, QMenu)

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

class StudentListPage(QWidget):
    data = []
    def __init__(self,parent):
        super().__init__()
        
        self.setParent(parent)
        
        self.search_index = 0
        self.initUI()
    
    def initUI(self):

        self.setContentsMargins(10, 0, 10, 10)
        main_layout = QVBoxLayout(self)

        page_title = QLabel('STUDENT LIST')
        page_title.setProperty('class', 'heading2')

        group_model = self.load_groups()
        search_input = QLineEdit()
        search_input.setPlaceholderText('Search')
        search_input.setFixedWidth(200)
        search_input.textChanged.connect(lambda text: self.find_in_list(text))

        class_filter_combo = QComboBox()
        class_filter_combo.setModel(group_model)
        class_filter_combo.currentIndexChanged.connect(lambda _: self.load_students(class_filter_combo))

        edu_btn = self.create_more_option_menu(group_model)
        edu_btn.setToolTip('Open options')

        command_layout = QHBoxLayout()
        command_layout.addWidget(page_title)
        command_layout.addStretch()
        command_layout.addWidget(search_input)
        command_layout.addWidget(class_filter_combo)
        command_layout.addWidget(edu_btn)

        header_widget = QWidget()
        header_widget.setLayout(command_layout)
        main_layout.addWidget(header_widget)
        
        # Create and set model
        self.model = QStandardItemModel(0, 4)  # 0 rows, 4 columns initially
        # Set header text
        self.model.setHorizontalHeaderLabels(['PHOTO', 'INFO', 'ADDRESS', 'LAST NOTE'])
        
        self.table = QTableView()
        # If we set the model after table settings, the last column does not streched.        
        self.table.setModel(self.model)

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.table.setShowGrid(False)

        # Column widths (matching your original fixed/contents/stretch)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 300)
        # Column 3 stretches
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        main_layout.addWidget(self.table)
        self.footer = QLabel('')
        self.footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.footer)
        # Initial load
        class_filter_combo.setCurrentIndex(0)
        
        self.load_students(class_filter_combo)

    def show_csv_load_message(self):
            option = app_context.settings_manager.find_value('csv_show_option_message')
        
            #if not option or option == True:  return
            #settings = QSettings("MyCompany", "MyApp")  # Unique identifier for your app
            #if settings.value("dont_show_message", False, type=bool):
            #    return  # Do not show the message if user disabled it
            #QSettings stores values in platform-specific locations. Here’s where the settings are saved depending on the operating system:
            #In Windows stored in the Registry under:📌 HKEY_CURRENT_USER\Software\MyCompany\MyApp

            column_mapping = ["ID", "First Name","Last Name","Parent Name",
                            "Phone","Address","Parent Phone","Additional Details",
                            "Gender", "Date"]
                    
            # Create QMessageBox
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Warning")
            msg = 'Note!\nThis feature currently only accepts csv files with the following format, the columns of the csv file must be as follows:\n'
            msg += f'\n{column_mapping}\n\n' 
            msg += 'If these are not followed, the data may not be saved as you expect.\n'
            msg += 'Additionally, if you need to upload a "photo" for each record, this must be done separately. After saving the profile, select the desired person from the list and upload the photo from the edit profile section.'
            msg += 'If you are sure, click "OK" to continue.'
            msg_box.setText(msg)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

            # Add 'Don't Show Again' checkbox
            checkbox = QCheckBox("Don't show again")
            msg_box.setCheckBox(checkbox)
            #msg_box.setModal(True)
            # Show the message box
            btn = msg_box.exec()

            # Store the user preference
            app_context.settings_manager.write({"csv_show_option_message": checkbox.isChecked()})

            return btn

    def load_from_csv(self):

            if self.show_csv_load_message() == QMessageBox.StandardButton.Cancel: return
    
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("csv utf-8(comma delimited)(*.csv)")
            
            if dialog.exec():
                csv_file = dialog.selectedFiles()
                try:
                    # Get database column names
                    table_columns = app_context.database.get_columns('personal_info')
                    
                    # Read CSV headers dynamically
                    csv_headers = pd.read_csv(csv_file[0], nrows=0).columns.tolist()

                    # Be careful, we have used case-sensitive mapping here. the'column_mapping' data is case-sensitive.
                    # The columns in source csv file must exactly match these values.
                    # **Manual Mapping (We can use GUI to do this dynamically)**
                    column_mapping = {"ID": "id", "First Name": "fname_","Last Name": "lname_", "Parent Name": "parent_name_",
                                    "Phone":"phone_","Address":"address_","Parent Phone":"parent_phone_","Additional Details":"additional_details_",
                                    "Gender":"gender_", "Date":"birth_date_"}#,"Photo":"photo_"}

                    # Make sure only mapped headers are used
                    valid_mapping = {csv_col: sql_col for csv_col, sql_col in column_mapping.items() if csv_col in csv_headers and sql_col in table_columns}

                    if valid_mapping:
                        chunk_size = 1000
                        data = pd.read_csv(csv_file[0], chunksize=chunk_size, dtype_backend='numpy_nullable')
                        app_context.database.bulk_insert_csv(data, 'personal_info', valid_mapping)
                    
                    else:
                        print("No valid mapping found!")
                    
                    msg = 'Load data from '+ csv_file[0]

                except Exception as e:
                    msg = f'Database Error: {e}'

                PopupNotifier.Notify(self,"Message", msg, 'bottom-right', delay=5000)

    def create_more_option_menu(self,group_model=None) -> QPushButton:
                
            btn = QPushButton('')            
            btn.setProperty('class','grouped_mini')
            btn.setIcon(QIcon(":/icons/menu.svg"))

            menu = QMenu(btn)
                    
            btn.setMenu(menu)
            # Multi-selection toggle (checkable). If table hasn't been created yet,
            # store desired state in self._multi_select_enabled and apply later when table exists.
            if not hasattr(self, '_multi_select_enabled'):
                self._multi_select_enabled = False
            
            action_multi = QAction(icon=QIcon(':/icons/list-checks.svg'),
                                text='Enable multi-selection', parent=menu)
            action_multi.setCheckable(True)
            action_multi.setChecked(self._multi_select_enabled)
            action_multi.setToolTip('Toggle multi-row selection in the students list')

            def _toggle_multi(checked):
                # remember desired state
                self._multi_select_enabled = checked
                # apply if table widget exists
                if hasattr(self, 'table') and self.table is not None:
                    mode = QAbstractItemView.SelectionMode.MultiSelection if checked else QAbstractItemView.SelectionMode.SingleSelection
                    self.table.setSelectionMode(mode)

            action_multi.triggered.connect(_toggle_multi)
            
            action4 = QAction(icon= QIcon(':/icons/id-card.svg'), text='Add new student', parent= menu)
            action4.triggered.connect(self.open_personal_info_dialog)
            menu.addAction(action4)

            action5 = QAction(icon= QIcon(':/icons/sheet.svg'), text='Import from csv file', parent= menu)
            action5.setToolTip('Opens file dialog to load list of students to database')
            action5.triggered.connect(self.load_from_csv)
            menu.addAction(action5)

            menu.addSeparator()

            menu.addAction(action_multi)

            menu.addSeparator()

            action0 = QAction(icon= QIcon(':/icons/drafting-compass.svg'), text='Set Edu-Item to group', parent= menu)

            action0.triggered.connect(lambda _, option='all': self.send_edu_items(option))
            menu.addAction(action0)

            action1 = QAction(icon= QIcon(':/icons/drafting-compass.svg'), text='Set Edu-Item to selected students',parent=menu)
                            
            action1.triggered.connect(lambda _, option='selected-list':self.send_edu_items(option))
            menu.addAction(action1)
            
            menu.addSeparator()
            
            action3 = QAction(icon= QIcon(':/icons/users-selected.svg'), text='group selected students', parent=menu)

            action3.triggered.connect(lambda _, model= group_model:self.show_group_dialog(model,'selected-list'))
            menu.addAction(action3)
            
            action2 = QAction(icon= QIcon(':/icons/users.svg'), text='group all',parent=menu)

            action2.triggered.connect(lambda _, model= group_model:self.show_group_dialog(model,'all'))
            menu.addAction(action2)
                    
            action3 = QAction(icon= QIcon(':/icons/combine.svg'), text='manage groups',parent=menu)
            action3.triggered.connect(lambda _:self.show_manage_groups_dialog())
            menu.addAction(action3)
        
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
    
    def update_custom_assignment(self,stu_id:str, qb_Id:int, answer:str, feedback:str, 
                             reply_date:str, deadline:str, assignment_date:str, 
                             score_earned:float, max_score:float, ):
       
        try:
            cmd = 'INSERT INTO quests (qb_Id, student_id, max_point_, earned_point_, assign_date_, deadline_, reply_date_,answer_,  feedback_)'
            cmd += 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);'

            self.db_cursor.execute(cmd,(qb_Id, stu_id, max_score, score_earned, assignment_date, deadline, reply_date, answer, feedback))

            status = True
            message =f'All changes of the Edu-Item with Id:{qb_Id} was updated.'

        except Exception as e:
            status = False
            message = f'Error: {e}.'

        return status, message
        
    def show_group_dialog(self, model:QStandardItemModel,option = 'selected-list'):

            if option == 'all':
                self.table.selectAll()
            elif not self.table.selectedIndexes(): 
                PopupNotifier.Notify(self,'','First select at least one student')
                return

            dlg = GroupSelectionDialog(model)
            
            if dlg.exec() == QDialog.DialogCode.Accepted:
                
                item = model.item(dlg.selected_group.row())
                group:ClassroomGroupViewModel = item.data(Qt.ItemDataRole.UserRole)
                # The user has decided to group the selected list into this group.
                students = self.table.selectedIndexes()
                id_list = ''
                # Iterate over all selected indexes
                for index in students:
                    row = index.row()
                    # We want to get student id from the QWidget, this data is stored in the second column
                    # The second column is a QLabel, so we can access its text
                    index = self.table.model().index(row, 1)  # Create QModelIndex for row, column 1
                    widget:QLabel = self.table.indexWidget(index)    # Get widget at that index
                    if widget is not None:
                        # Process the id
                        id = self.data[row][0] 
                        id_list = f'{id_list},{id}'

                status, message = group.model.add_member(int(group.Id), id_list)
                
                if status: self.load_groups()
                
                PopupNotifier.Notify(self,'', message)
        
    def show_manage_groups_dialog(self):

            dlg = GroupsManagerDialog(self.db_cursor)
            dlg.setFixedSize(675,500)
            dlg.exec()
            
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
    
    def load_students(self, sender:QComboBox):
            
        try:
                selected:ClassroomGroupViewModel = sender.currentData(Qt.ItemDataRole.UserRole)
                                
                # Fully Explain this sql command
                if isinstance(selected, str) or not selected:
                    group_filter = '' # Where user selected 'All'
                    self.table.tag = 'All' # selected
                else:
                    group_filter =  f'WHERE t1.Id = ANY(string_to_array(\'{selected.members}\',\',\'))'
                    self.table.tag = selected.Id
                
                # SQL query to retrieve student personal information along with their MOST RECENT observed behaviour (if any).
                # - Uses a LEFT JOIN to ensure every student appears, even if they have no behaviour records.
                # - The subquery finds the latest record per student using GROUP BY + MAX(date_time_),
                #   then joins back to get the full row of that latest observation.
                # - When a specific group/class is selected, {group_filter} adds a WHERE clause
                #   filtering students by a comma-separated list of IDs using PostgreSQL's string_to_array() + ANY().
                # - WARNING: Current f-string interpolation of 'selected.members' is vulnerable to SQL injection
                #   if the input is not strictly controlled. Prefer parameterized queries in production.
                # - Just add this index once:
                #   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_obs_student_time 
                #   ON observed_behaviours (student_id, date_time_ DESC);
                cmd =  'SELECT t1.Id, t1.fname_, t1.lname_, t1.phone_, t1.address_, t1.photo_, t2.date_time_, '
                cmd += 't2.observed_behaviour_, t1.parent_name_, t1.parent_phone_, t1.additional_details_, '
                cmd += 't1.birth_date_, t1.gender_ FROM personal_info t1 '
                cmd += 'LEFT JOIN (SELECT t2.* FROM observed_behaviours t2 INNER JOIN ( '
                cmd += 'SELECT student_id, MAX(date_time_) AS max_created_at FROM observed_behaviours '
                cmd += 'GROUP BY student_id) last_records ON t2.student_id = last_records.student_id '
                cmd += 'AND t2.date_time_ = last_records.max_created_at) t2 ON t1.id = t2.student_id ' 
                cmd += f'{group_filter};'
                
                self.data = app_context.database.fetchall(cmd)
                
                # Columns to display(4 columns):
                # 0- Photo, 1- Identification information, 2- address and cantact details, 
                # 3-The last notes of behavioral observations
                            
                # fetched columns:
                # 0- student Id, 1- first name, 2- last name, 3- phone,
                # 4- address, 5- photo, 6- date of last modified behavioral observation,
                # 7- last observed behaviour, 8- parent name, 9- parent phone,
                # 10- additional details, 11-birth date, 12-gender
                # Total: 13 columns 
                self.model.setRowCount(len(self.data))
            
                for row, record in enumerate(self.data):
                    # photo data has loaded in 5 column and must be displayed on first column
                    photo_label = QLabel()
                    photo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                    photo_label.setText("No\nPhoto")
                    photo_label.setStyleSheet('background-color: transparent;padding:5px;text-align:center;margin:0px')
                    # Set photo box dimensions to the formal size (35mm x 45mm ≈ 138x177 pixels at 96 DPI)
                    photo_width  = 90    # Width of the photo box
                    photo_height = 130  # Height of the photo box
                    photo_label.setFixedSize(photo_width + 10, photo_height)
                    #photo_label.setProperty('class','caption')
                            
                    if record[5]: # If has a photo
                        pixmap = bytea_to_pixmap(record[5])
                        # Scale the photo to fill the entire photo box (ignore aspect ratio)
                        scaled_pixmap = pixmap.scaled(photo_label.size(), Qt.AspectRatioMode.IgnoreAspectRatio, 
                                                                        Qt.TransformationMode.SmoothTransformation)
                        #rounded = create_rounded_pixmap(scaled_pixmap)
                        photo_label.setPixmap(scaled_pixmap)
                        photo_label.setText("")

                    self.table.setIndexWidget(self.model.index(row, 0), photo_label)

                    # student Id + first name + last name
                    name_label = QLabel(f"{record[0]}<br><strong>{record[1]} {record[2]}</strong>")
                    name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                    name_label.setFixedWidth(150)
                    
                    self.table.setIndexWidget(self.model.index(row, 1), name_label)
                    
                    address_label = QLabel(str(record[4]) + '\nCall: ' + str(record[3]))
                    address_label.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft)
                    address_label.setFixedWidth(250)
                    self.table.setIndexWidget(self.model.index(row,2),address_label)
                    
                    w = QWidget()
                    notes_layout = QGridLayout(w)
                    notes_layout.setContentsMargins(5,5,5,5)
                    
                    last_note = QLabel(str(record[6].strftime("%Y-%m-%d %H:%M:%S") if record[6] else '') + '\n' + str(record[7]))
                    last_note.setWordWrap(True)
                    last_note.setAlignment(Qt.AlignmentFlag.AlignTop)

                    # Create a QScrollArea
                    scroll_area = QScrollArea()
                    
                    scroll_area.setWidget(last_note)
                    scroll_area.setWidgetResizable(True)
                    scroll_area.setMinimumHeight(120)
                    scroll_area.setMaximumHeight(120)
                    notes_layout.addWidget(scroll_area,0,0)
                    
                    btn = self.create_menu_btn(record,row)
                    
                    rtl = is_mostly_rtl(last_note.text())
                    
                    notes_layout.addWidget(btn,0,0,Qt.AlignmentFlag.AlignTop | 
                                        (Qt.AlignmentFlag.AlignLeft if rtl else Qt.AlignmentFlag.AlignRight))
                    
                    self.table.setIndexWidget(self.model.index(row,3), w)

                self.footer.setProperty('class','caption')
                self.footer.setText(f'Students: {str(len(self.data))}')
                self.table.resizeRowsToContents()
                
                # Set selection behavior
                self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)  # Select entire rows
                self.table.horizontalHeader().adjustSize()
            
        except Exception as e: print(f"Error: {e}")
    
    def remove_from_group(self,stu):
            group_Id = str(self.tableWidget.tag)
            
            self.db_cursor.execute('SELECT members_ FROM groups WHERE id = %s;',(group_Id,))
            members = self.db_cursor.fetchone()[0]
                
            if members:
                
                i = str(members).find(stu['Id'])
                if i >= 0:
                    members = str(members).replace(stu['Id'],"")
                    self.db_cursor.execute('UPDATE groups SET members_ = %s WHERE id = %s;',(members,group_Id))

                    PopupNotifier.Notify(self,message='Group updated.')
            
    def assign_edu_to_student(self,stu:dict):
            
            window = QApplication.activeWindow()
            window.add_page(EduResourcesView(window,[stu]))
        
    def send_edu_items(self, options='selected-list'):
            
            if options =='all': self.tableWidget.selectAll()
            # This gives a set of selected row indices
            selected_rows = list({index.row() for index in self.tableWidget.selectedIndexes()})
            
            # select_items handled by tow object, if is called by an item from table, this is
            # means it has to store the selected edu-items for one student but if is called by
            # 'assignment button' from header widgets' it means selected edu-items must be assigned for all students
            if len(selected_rows) == 0 :
                PopupNotifier.Notify(self,'','No student selected')
                return        
            else:
                cnt = len(selected_rows)

                stu_list = []
                for i in range(cnt):
                    # List of student id's
                    stu_list.append({"Id":self.data[selected_rows[i]][0],
                                "Name":self.data[selected_rows[i]][1] + ' ' + self.data[selected_rows[i]][2]}
                            )
            
            window = QApplication.activeWindow()
            
            window.add_page(EduResourcesView(window,stu_list))

    def delete_person(self, id,row_index):

            button = QMessageBox.warning(self,
                                'DELETE STUDENT','ARE YOU SURE TO DELETE THE STUDENT WITH ID: \'' + id + '\'?',
                                QMessageBox.StandardButton.Ok,QMessageBox.StandardButton.No)
            
            if button == QMessageBox.StandardButton.No: return
            
            try:
                query  = 'DELETE FROM observed_behaviours WHERE student_Id=%s;'
                query += 'DELETE FROM personal_info WHERE Id=%s;'
                self.db_cursor.execute(query, (id,id))
                msg = 'Student ' + id + ' removed from database.'
                
                self.table.model().removeRow(row_index)

            except Exception as e:
                msg = f"Database error: {e}."

            
            PopupNotifier.Notify(self,"Message",msg, 'bottom-right', delay=3000, background_color='#353030',border_color="#2E7D32")
                
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

    def find_in_list(self, search_input:QLineEdit):
            search_text = search_input
            if not search_text:
                PopupNotifier.Notify(self, "Message", "Enter a value to search.", 'bottom-right', delay=3000)
                return

            current_index = self.table.currentIndex()

            self.table.clearSelection()
            model = self.table.model()
            lower_search = search_text.lower()
            found = False
            
            for row in range(self.search_index,self.table.model().rowCount()):
                for col in range(self.table.model().columnCount()):
                    # try QTableWidgetItem first
                    item = self.table.model().item(row, col)
                    
                    cell_text = ""
                    if item and item.text(): cell_text = item.text()
                    else:
                        # then check for widget placed with setCellWidget(...)
                        index = self.table.model().index(row, col)  # Create QModelIndex for row, column 1
                        widget = self.table.indexWidget(index)

                        if widget is None:
                            cell_text = ""
                        elif isinstance(widget, QLabel):
                            cell_text = widget.text()
                        else:
                            # common widget interfaces: text(), toPlainText(), document()
                            if hasattr(widget, "text"):
                                try:
                                    cell_text = widget.text()
                                except Exception:
                                    cell_text = ""
                            elif hasattr(widget, "toPlainText"):
                                try:
                                    cell_text = widget.toPlainText()
                                except Exception:
                                    cell_text = ""
                            else:
                                # fallback: look for a QLabel child inside custom widget
                                lbl = widget.findChild(QLabel)
                                cell_text = lbl.text() if lbl else ""

                    if cell_text and lower_search in cell_text.lower():
                        # select row, set current cell and scroll to center
                        self.table.selectRow(row)
                        current_index = model.index(row, col)
                        # Update search index for next search
                        self.search_index = row + 1
                        found = True

                        break
                
                if found: break
            
            self.table.setCurrentIndex(index)
            self.table.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)

            if not found:
                PopupNotifier.Notify(self, "Message", f"No match for '{search_text}' in the list.", 'bottom-right', delay=1500)
            
                        
            # Reset search index if it exceeds row count
            self.search_index %= self.table.model().rowCount()            
            #search_input.setFocus(Qt.FocusReason.PopupFocusReason)

