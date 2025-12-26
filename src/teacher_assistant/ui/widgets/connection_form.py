
from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QFormLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox
import psycopg2

from core.app_context import app_context
from data.database import change_database_in_session, create_database, initialize_database

class PostgreSqlConnectionWidget(QObject):
    
    def __init__(self,parent=None):
        
        super().__init__()
        
        # a dictionary for cannection parameters
        connection_settings = app_context.settings_manager.find_value('connection')
        
        host = 'localhost' if connection_settings is None else connection_settings["host"]
        port = '5432'      if connection_settings is None else connection_settings["port"]
        database = ''      if connection_settings is None else connection_settings["database"]
        user = 'postgres'  if connection_settings is None else connection_settings["user"]
        password = ''      if connection_settings is None else connection_settings["password"]

        #self.connection = None
        self.dialog = QDialog(parent=parent)
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

            status, msg = create_database(connection, database= self.database)
            
            if not status: 
                QMessageBox.warning(self,'',msg)
                return
            
            status, connection, msg = change_database_in_session(connection,self.database,self.password)
            
            if not status:
                QMessageBox.warning(self,'',msg)    
                return
            
            status, msg = initialize_database(connection)
            
            if not status:
                QMessageBox.warning(self,'',msg)    
                return
            
            
            connection.autocommit =True
            self.connection = connection
            self.connection.autocommit = True

            self.dialog.hide()


    def connect_to_database(self):
        
        self.host = self.host_field.text()
        self.port = self.port_field.text()
        self.database = self.database_field.text()# postgres
        self.user = self.user_field.text()
        self.password = self.password_field.text()
        
        try:
  
            app_context.database.connect(host=self.host, port=self.port, database= self.database, user=self.user, password=self.password)
            
            if app_context.database.connection:
                if app_context.database.connection.status == 1: # STATUS_READY
                    self.dialog.close()
        
        except Exception as e:

            QMessageBox.critical(self, "Error", f"Failed to connect to database,\nError: {e}")
       
    def show_dialog(self):

        self.dialog.resize(550, 250)
        self.dialog.setMaximumSize(550,250)
        self.dialog.setMinimumWidth(550)
        
        self.dialog.exec()

        # this part is executed after the dialog is closed
        if app_context.database.connection:
            
            #self.connection.autocommit = True

            host = '' if self.host is None else self.host
            port = '' if self.port is None else self.port
            database = '' if self.database is None else self.database
            user = '' if self.user is None else self.user
            password = '' if self.password is None else self.password
            settings_list = [('host',host),('port',port),('database',database),('user',user),('password',password)]
            # Create a dictionary with the list elements as key-value pairs under 'connection'
            connection_settings = {"connection": dict(settings_list)}
            
            #app_context.register_database(self.connection)
            
            status = True
        else:
            connection_settings = None
            status = False

        return status, connection_settings

