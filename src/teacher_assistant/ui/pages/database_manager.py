import os
from datetime import datetime
#import pypandoc
import psycopg2

from PySide6.QtGui import (Qt)

from PySide6.QtWidgets import (QFileDialog, QInputDialog,
                               QCheckBox, QGridLayout, QWidget, QLabel, QMessageBox,
                               QPushButton, QHBoxLayout, QLineEdit, QComboBox)

from PySideAbdhUI.Notify import PopupNotifier

#from data.view_models.EduItems import MaintenanceViewModel
from core.app_context import app_context
from data.database import backup_postgres_db, change_database_in_session, create_database, initialize_database, restore_postgres_db
from view_models.EduItems import MaintenanceViewModel

class DatabaseManagerPage(QWidget):

    def __init__(self, db_name:str='', host='localhost',port='5432', user='postgres', password = '',
                 postgresql_tools_path='C:\\Program Files\\PostgreSQL\\17\\bin',backup_path='', restore_path='',
                 style_path='', settings_path =''):
        
        super().__init__()

        # Main Layout
        main_layout = QGridLayout(self)
        main_layout.setSpacing(10)
        db_name_input = QLineEdit(db_name)
        
        # Database Connection Section
        connection_layout = QHBoxLayout()
        title_lbl = QLabel('DATABASE MAINTENANCE')
        title_lbl.setProperty('class','heading2')

        host_input = QLineEdit('')
        port_input = QLineEdit('')
        user_input = QLineEdit('')
        password_input = QLineEdit('')
        password_input.setEchoMode(QLineEdit.EchoMode.Password)

        connection_layout.addWidget(QLabel("Host:"))
        connection_layout.addWidget(host_input)
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(port_input)
        connection_layout.addWidget(QLabel("User:"))
        connection_layout.addWidget(user_input)
        connection_layout.addWidget(QLabel("Password:"))
        connection_layout.addWidget(password_input)
        connection_layout.addStretch(1)
        
        db_tools_path_input = QLineEdit('')
        backup_opts_cmb = QComboBox()
        backup_opts_cmb.addItems(['Full backup', 'Export as csv'])
        backup_opts_cmb.setCurrentIndex(0)
        
        backup_output_edit = QLineEdit('')
        restore_path_edit = QLineEdit('')
        
        restore_opts = QHBoxLayout()
        # Create radio buttons
        overwrite_chk = QCheckBox("Overwrite")
        restore_target_db_name_edit = QLineEdit('')
        restore_target_db_name_edit.setPlaceholderText('Database name')
        overwrite_chk.checkStateChanged.connect(lambda checked : restore_target_db_name_edit.setVisible(not checked == Qt.CheckState.Checked))
        # Add them to layout
        restore_opts.addWidget(overwrite_chk)
        restore_opts.addWidget(restore_target_db_name_edit)
        restore_opts.addStretch(1)
       
        # Action Buttons
        action_layout = QHBoxLayout()
        create_db_button = QPushButton("Create") 
        create_db_button.clicked.connect(self.create_database)
        backup_db_button = QPushButton("Backup")
        backup_db_button.clicked.connect(self.backup_database)
        restore_db_button = QPushButton("Restore")
        restore_db_button.clicked.connect(self.restore_database)
        drop_db_button = QPushButton("Drop")
        drop_db_button.clicked.connect(self.drop_database)
        save_settings_btn = QPushButton('Save settings')
        save_settings_btn.clicked.connect(self.save_settings)

        action_layout.addWidget(create_db_button)
        action_layout.addWidget(backup_db_button)
        action_layout.addWidget(restore_db_button)
        action_layout.addWidget(drop_db_button)
        action_layout.addWidget(save_settings_btn)

        main_layout.addWidget(title_lbl,0,0,1,2)        
        main_layout.addWidget(QLabel('Current database:'),1,0)
        main_layout.addWidget(db_name_input,1,1)
        main_layout.addWidget(QLabel('Login options:'),2,0)
        main_layout.addLayout(connection_layout,2,1)
        main_layout.addWidget(QLabel('Database tools:'),3,0)
        main_layout.addWidget(db_tools_path_input,3,1)
        main_layout.addWidget(QLabel('Backup options:'),4,0)
        main_layout.addWidget(backup_opts_cmb,4,1)
        main_layout.addWidget(QLabel('Backup to:'),5,0)
        main_layout.addWidget(backup_output_edit,5,1)
        main_layout.addWidget(QLabel('Restore from:'),6,0)
        main_layout.addWidget(restore_path_edit,6,1)       
        main_layout.addWidget(QLabel('Restore option:'),7,0)
        main_layout.addLayout(restore_opts,7,1,1,2)
        main_layout.addLayout(action_layout,8,0,1,2)

        main_layout.addWidget(QLabel(f'Theme: {style_path}'),9,0,1,2)
        main_layout.addWidget(QLabel(f'Settings: {settings_path}\\settings.json'),10,0,1,2)
        
        main_layout.setRowStretch(11,1)
        
        # Binding View model
        self.view_model = MaintenanceViewModel()
        self.view_model.bind_property("database_name", str(db_name), db_name_input)
        self.view_model.bind_property('host',host, host_input)
        self.view_model.bind_property('port',port, port_input)
        self.view_model.bind_property('user_name', user, user_input)
        self.view_model.bind_property('password',password, password_input)
        self.view_model.bind_property('postgresql_tools_path', postgresql_tools_path, db_tools_path_input)
        self.view_model.bind_property('backup_type', backup_opts_cmb.itemText(0), backup_opts_cmb)
        self.view_model.bind_property('backup_path', backup_path,backup_output_edit)
        self.view_model.bind_property('restore_path', restore_path, restore_path_edit)
        self.view_model.bind_property('overwrite_restore', True, overwrite_chk)
        self.view_model.bind_property('restore_target_name', '', restore_target_db_name_edit)


    def save_settings(self):

        app_context.settings_manager.write({"postgreSQL tools path": self.view_model.postgresql_tools_path})
        app_context.settings_manager.write({"backup to": self.view_model.backup_path})
        app_context.settings_manager.write({"restore from": self.view_model.restore_path})
        app_context.settings_manager.write({"overwrite restore": self.view_model.overwrite_restore})

        settings_list = [('host',self.view_model.host),
                         ('port',self.view_model.port),
                         ('database',self.view_model.database_name),
                         ('user',self.view_model.user_name),
                         ('password',self.view_model.password)]
        
        # Create a dictionary with the list elements as key-value pairs under 'connection'
        connection_settings = {"connection": dict(settings_list)}
        app_context.settings_manager.write(connection_settings)  

        PopupNotifier.Notify(self,'Settings','Settings saved successfully.')

    def backup_database(self):
        # Update this path to match your PostgreSQL installation
        PG_DUMP_PATH = self.view_model.postgresql_tools_path + '\\pg_dump.exe'

        # Check if pg_dump.exe exists
        if not os.path.exists(PG_DUMP_PATH):
           PopupNotifier.Notify(self, 'Backup report', f"❌ PostgreSQL tools not found. Ensure pg_dump.exe exists at: {PG_DUMP_PATH}.")
           return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{self.view_model.database_name}_backup_{timestamp}.dump"
    
        try:
            os.makedirs(self.view_model.backup_path, exist_ok=True)
        except Exception as e:
            msg = f"❌ Failed to create output directory: {e}."

        output_file = os.path.join(self.view_model.backup_path, backup_filename)

        database = self.view_model.database_name
        
        warning = f"⚠️ WARNING: You are about to backup the database: '{database}' to:\n"
        warning += f"{output_file}.\n⚡To confirm the action enter password."
        # Create the input dialog
        dialog = QInputDialog()
        dialog.setWindowTitle("Login")
        dialog.setLabelText(warning)

        # Set input mode to text and echo mode to password
        dialog.setTextEchoMode(QLineEdit.EchoMode.Password)

        if not dialog.exec() == QInputDialog.Accepted: return
        
        if not dialog.textValue() == self.view_model.password:
            PopupNotifier.Notify(self,'','Pasword in wrong.')
            return
                
        status, msg , path = backup_postgres_db(
                                        self.view_model.database_name,
                                        self.view_model.user_name,
                                        self.view_model.password,
                                        self.view_model.host,
                                        self.view_model.port,
                                        output_file,
                                        PG_DUMP_PATH)
        
        PopupNotifier.Notify(self, 'Backup report', msg + '\n' + path)

    def restore_database(self):
        # Update these paths according to your PostgreSQL installation
        bin_path = self.view_model.postgresql_tools_path
        
        PG_PSQL_PATH = bin_path + r"\\psql.exe"
        PG_CREATEDB_PATH =bin_path + r"\\createdb.exe"
        PG_RESTORE_PATH = bin_path + r"\\pg_restore.exe"
        # Check if pg_dump.exe exists
        if not os.path.exists(PG_RESTORE_PATH):
           PopupNotifier.Notify(self, 'Restore report', f"❌ PostgreSQL tools not found. Ensure pg_dump.exe exists at: {PG_RESTORE_PATH}.")
           return
        
        dump_file, _ = QFileDialog.getOpenFileName(self, "Open Backup", self.view_model.backup_path, "Dump Files (*.dump)")
        
        if dump_file:
            
            target_db = self.view_model.database_name
            
            if not self.view_model.overwrite_restore: target_db = self.view_model.restore_target_name
            
            if not target_db:
                QMessageBox.warning(self, "Input Error", "Enter a database name to restore into.")
                return
            
            warning = f"⚠️ WARNING: You are about to restore data on the '{target_db}'.\n"
            warning += "⚡To confirm the action, enter password."
            # Create the input dialog
            dialog = QInputDialog()
            dialog.setWindowTitle("Login")
            dialog.setLabelText(warning)

            # Set input mode to text and echo mode to password
            dialog.setTextEchoMode(QLineEdit.EchoMode.Password)

            if not dialog.exec() == QInputDialog.Accepted: return
                
            if not dialog.textValue() == self.view_model.password:
                PopupNotifier.Notify(self,'','Pasword in wrong')
                return

            status, msg, db = restore_postgres_db(dump_file,
                                                                 target_db,
                                                                 self.view_model.user_name,
                                                                 self.view_model.password,
                                                                 self.view_model.host,
                                                                 self.view_model.port,
                                                                 self.view_model.overwrite_restore,
                                                                 self.view_model.postgresql_tools_path)

            QMessageBox.information(self, "Restore Database", f"Database '{db}' restored successfully from '{dump_file}'.")

    def drop_database(self):
        
        database = self.view_model.database_name
        
        warning = f"⚠️ WARNING: You are about to permanently drop the database: '{database}'.\n"
        warning += "⚠️ This action cannot be undone and all data will be lost.\n"
        warning += "⚡To confirm droping process enter password."
        # Create the input dialog
        dialog = QInputDialog()
        dialog.setWindowTitle("Login")
        dialog.setLabelText(warning)

        # Set input mode to text and echo mode to password
        dialog.setTextEchoMode(QLineEdit.EchoMode.Password)

        if not dialog.exec() == QInputDialog.Accepted: return
        
        if not dialog.textValue() == self.view_model.password:
            PopupNotifier.Notify(self,'','Pasword in wrong.')
            return
                
        host = self.view_model.host
        port = self.view_model.port
        user = self.view_model.user_name
        password = self.view_model.password

        try:
            # Connect to another DB (e.g. postgres) to drop target DB
            conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port )
            conn.autocommit = True
            cur = conn.cursor()

            # Terminate all connections to the target database
            cur.execute(psycopg2.sql.SQL("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid();"), [database])

            # Drop the database
            cur.execute(psycopg2.sql.SQL("DROP DATABASE IF EXISTS {}").format(psycopg2.sql.Identifier(database)))
            
            msg = f"🗑️ Database '{database}' has been dropped completely."
        
            cur.close()
            conn.close()

        except Exception as e:
            msg = f"❌ Error dropping database: {e}."

        PopupNotifier.Notify(self,'🗑️',msg)
    
    def create_database(self):
        
        database = self.view_model.database_name

        result = QMessageBox.information(self, '', 
                                         f'You are ready to create a database named "{database}", if you are sure you can continue.',
                                         QMessageBox.StandardButton.Ok,QMessageBox.StandardButton.Discard)

        if result == QMessageBox.StandardButton.Discard: return

        host = self.view_model.host
        port = self.view_model.port
        user = self.view_model.user_name
        password = self.view_model.password
        
        try:
            # Stablish new connection with PostgreSQL server
            connection = psycopg2.connect(host=host, port= port, database= 'postgres',user=user,password=password)
        
            if connection:
                # Create the database
                status, msg = create_database(connection, database= database)
            
                if status: 
                    # Active the created database
                    status, connection, msg = change_database_in_session(connection,database,password)
            
                    if status:
                        # Initalize database(Create all tables)
                        status, msg = initialize_database(connection)
            
        except Exception as e: msg = f'Error: {e}'
        
        finally:

            connection.close()

            PopupNotifier.Notify(self,'', msg)

