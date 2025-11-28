import os
import io
from datetime import datetime, timedelta
from typing import Iterable
#import pypandoc
import psycopg2
import pymupdf
from PIL import Image
import pandas as pd

from PySide6.QtCore import QMarginsF, QPoint, QBuffer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

from PySide6.QtGui import (Qt, QTextOption, QPageLayout, QPageSize, QIcon, QAction, QStandardItemModel,QImage,
                           QStandardItem, QPixmap, QColor, QTextCharFormat, QTextDocument,QTextCursor, QTextImageFormat)

from PySide6.QtWidgets import (QFileDialog, QListWidget, QListWidgetItem, QScrollArea,QInputDialog,
                               QTextEdit, QHeaderView, QTableWidget, QDialogButtonBox, QCheckBox,
                               QGridLayout, QWidget, QLabel,QApplication,QDialog, QListView, QMessageBox,
                               QPushButton, QHBoxLayout, QLineEdit,QVBoxLayout,QMainWindow,QAbstractItemView,
                               QPlainTextEdit, QComboBox, QAbstractScrollArea,QMenu,QWidgetAction)

from Imaging.SnippingTool import SnippingWindow
from Imaging.ImageEditor import ImageEditor
from Imaging.Tools import pixmap_to_base64, bytea_to_pixmap
                
from PySideAbdhUI.Notify import PopupNotifier
from PySideAbdhUI.CardGridView import CardGridView
from PySideAbdhUI.Widgets import StackedWidget, Separator

import TeacherAssistant
from TeacherAssistant import SupportedFileTypes, ToolTips, state, template_config, FileTypes, settings_manager
from TeacherAssistant.utils import database_tools, helpers, analysis,text_processing
from TeacherAssistant.utils.text_processing import is_mostly_rtl, local_culture_digits
from TeacherAssistant.utils.image_tools import pdf_to_base64
from TeacherAssistant.utils.database_tools import get_postgres_columns, bulk_insert_csv

from TeacherAssistant.views.dialogs import GroupSelectionDialog
from TeacherAssistant.views.dialogs import GroupsManagerDialog
from TeacherAssistant.views.dialogs import PersonalInfoDialog        
from TeacherAssistant.views import Pages, Widgets
from TeacherAssistant.view_models import EduItems as viewModels


class RichTextEdit(QTextEdit):
    
    def __init__(self):
        super().__init__()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_custom_context_menu)



    def get_image_from_position(self):

        cursor = self.textCursor()
        doc = self.document()
        block = cursor.block()

        for frag in block.begin():
            if frag.fragment().isValid():
                char_format = frag.fragment().charFormat()
                if char_format.isImageFormat():
                    image_name = char_format.toImageFormat().name()
                    resource = doc.resource(QTextDocument.ResourceType.ImageResource, image_name)
                    if isinstance(resource, (QPixmap, QImage)): return resource
        
        return None
    

    def show_custom_context_menu(self, pos: QPoint):
        
        resource = self.get_image_from_position()
        menu = self.createStandardContextMenu()

        if isinstance(resource, (QPixmap, QImage)):
            
            action = QAction("Edit image", self)

            action.triggered.connect(lambda _, resource = resource: self.open_in_editor(resource))
            
            first_action = menu.actions()[0] if menu.actions() else None
            menu.insertAction(first_action, action)

            if first_action: menu.insertSeparator(first_action)

        menu.exec(self.mapToGlobal(pos))

 
    def update_resource(self, image_name:str, qimage:QImage, cursor:QTextCursor, replace=True):
        
        if not qimage: return
        
        self.document().addResource(QTextDocument.ResourceType.ImageResource, image_name, qimage)

        image_format = QTextImageFormat()
        image_format.setName(image_name)

        if replace:
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                cursor.insertImage(image_format)
        else:
                cursor.clearSelection()
                cursor.insertImage(image_format)


    def _get_image_from_document(self, image_name: str):
        """
        Retrieve QImage from QTextDocument's resource system using image name.
        """
        # Retrieve QPixmap data
        qimage = self.document().resource(QTextDocument.ResourceType.ImageResource, image_name)
        if not qimage: return None

        # Convert QImage to PIL Image
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.ReadWrite)

        qimage.save(buffer, "PNG")

        pil_img = Image.open(io.BytesIO(buffer.data()))

        return pil_img

    def open_in_editor(self, resource):
        
        editor = ImageEditor()
        editor.load_from_resource(resource)

        editor.task_completed.connect(lambda name, img, cursor = self.textCursor(): self.update_resource(name,img,cursor,True))

        editor.show()


# File names of Edu-Content templates
Edu_Template_Files = ['01-Quiz','02-Formal-Exam']

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
        self.view_model = viewModels.MaintenanceViewModel()
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

        settings_manager.write({"postgreSQL tools path": self.view_model.postgresql_tools_path})
        settings_manager.write({"backup to": self.view_model.backup_path})
        settings_manager.write({"restore from": self.view_model.restore_path})
        settings_manager.write({"overwrite restore": self.view_model.overwrite_restore})

        settings_list = [('host',self.view_model.host),
                         ('port',self.view_model.port),
                         ('database',self.view_model.database_name),
                         ('user',self.view_model.user_name),
                         ('password',self.view_model.password)]
        
        # Create a dictionary with the list elements as key-value pairs under 'connection'
        connection_settings = {"connection": dict(settings_list)}
        settings_manager.write(connection_settings)  

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
                
        status, msg , path = database_tools.backup_postgres_db(
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

            status, msg, db = database_tools.restore_postgres_db(dump_file,
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
                status, msg = database_tools.create_database(connection, database= database)
            
                if status: 
                    # Active the created database
                    status, connection, msg = database_tools.change_database_in_session(connection,database,password)
            
                    if status:
                        # Initalize database(Create all tables)
                        status, msg = database_tools.initialize_database(connection)
            
        except Exception as e: msg = f'Error: {e}'
        
        finally:

            connection.close()

            PopupNotifier.Notify(self,'', msg)



"""
# EduationalResourceEditor.py
# ###################################################################################################
#                                 EDUCATION RESOURCE EDITOR                                         #
# ################################################################################################### 
# This is an Editor for education resources like questions and other learning units, here           #
# we able to manage education resources as Plain Text, RTF, image, PDF, html and LaTeX.             #
# main technology to manage these contents is HTML script, However two usage of Html concept        # 
# is applyed here, first, as an editor to write learning unit, this type is pure usage of html      #
# script to create a learning unit, but it does not support the math formulas. second usage         #
# is to save and restore other datatypes in the database.                                           #
# We save all of other types in html format indexed by tag of 'meta' and name = 'qrichtext'         #
# (the 'meta' is a tag of html). this usage is more integrated with QTextEdit object and            #
# QTextDocument. Each script indexed by meta name='viewport' is raw script and is shown to user     #
# as pure Html script and other scripts indexted by mata name ='qrichtext' is shown as processed    #
# text, These scripts is ready to publish. However, it is possible to edit and it can be edited     #
# as normal text(without direct use of HTML or LaTeX codes).                                        #
# Supported text datatypes is listed as follow:                                                     #
#                                                                                                   #
# Plain Text: is directy written in QTextEdit and is converted to html by toHtml() method at        #
#             save time and when is read from database is loaded to the QTextEdit by calling        #
#             setHtml(...) method. this method does not support formated texts  and other           #
#             special scripts as math formola and image. it is proper to simple resources.          #
#                                                                                                   #
# Rich Text : Rich Text is a document that is saved by .rtf file extension, like Plain Text         #
#             is written directly in QTextEdit an is saved using toHtml() and is restored by        #
#             setHtml(...) method. it supports formatted texts, image contents and tables.          #
#             Also it able to support other more advanced properies against Plain Text.             #
#                                                                                                   #
# LaTeX     : The LaTeX script is written and saved as plain text. in saveing method of this        #
#             content is not used any conversion. It is saved by calling toPlainText() method.      #
#             Also at read time from database will been used setPlainText(...). this is row data,   #
#             befor using it must be processed by a LaTeX engine like PDFlatex, xelatex and etc.    #                                                                              #
#             The LaTeX raw script is recognized  at reading time by 'regular expresion processing' #
#             techniques over \\documentclass{...}, \\begin{document}... \\end{document} and other     #
#             keywords of LaTeX script.                                                             #
#                                                                                                   #
# Html      : is very similar to LaTeX, we use this script to write Html code directly. LaTex       #
#             and Html data are raw and must be processed befor useing. to process the Html code    #
#             it is enugh we reset content with setHtml(...). at first step we access to the        #
#             Html script of QTextEdit by toPlainText(), next we reset using setHtml(...).          #
#                                                                                                   #
# Image     : Image conent is converted to base64 string at load time and is updated by setting to  #
#             html tag <img src="data:image/png;base64,{base64_image}"/> then uses setHtml(...)     #
#             method to upload in QTextEdit document. after this step, at save and read time it is  #
#             considered as an Html content.                                                        #
#                                                                                                   #
# PDF       : In this code we supose the PDF contents has One page, we don't need more page to use  #
#             as a learning resource. if the loaded content has been more pages we use first page   #
#             and other pages is skipped. If we don't need to manipulation, PDF content can load as #
#             image. becuase of editing porpose, we can load as html raw string. all actions on the #
#             PDF content after load is like image and html.                                        #
#                                                                                                   #
# docx      : This file type currently is not fully supported. but It can load as  html using       #
#             'pypandoc' package. currently word documents that loaded by this method loses many    #
#             formating properties. however the docx files is loaded as html.                       #
#                                                                                                   #
# All of data is saved using HTML format with width = 6.19 inches, this value is avilable space for #
# edu-content in the A4 paper, because there are 0.5 inches space for left and right margin and 0.54#
# inches is used for columns 1 and 3 in the our 3-columns paper. Below is output table.             #
#                                                                                                   #
# │     ┌──────┬─────────────────────────────────────────────────────────────────────┬──────┐     │ #
# │ 0.5 │POINT │                              HEADER                                 │  ROW │ 0.5 │ #
# │     ├──────┼─────────────────────────────────────────────────────────────────────┼──────┤     │ #
# │     │ 0.54 │                       CONTENT - 6.19 INCHES                         │ 0.54 │     │ #
# │     ├──────┼─────────────────────────────────────────────────────────────────────┼──────┤     │ #
# │     │      │                               CONTENT                               │      │     │ #
# │     │      │                                                                     │      │     │ #
# │     │──────┼─────────────────────────────────────────────────────────────────────┼──────┤     │ #
# │     │  SUM │                               FOOTER                                │      │     │ #
# │     └──────┴─────────────────────────────────────────────────────────────────────┴──────┘     │ #
#                                                                                                   #
# The 6.19 inches must be converted to pixels. this coversion is done by DPI(dots per inches), final#
# pixels is equal to 6.19xDPI. to keep quality of images durng conversion, using of 'width=6.19dpi' #
# property of HTML script is good choise against other methods.                                     #
# For editable porpose the content is not saved as final version, It is save as raw data. In case   #
# of LaTeX script if a content be ready to use or publish, it had been provided by a command 'RUN-  #
# TEX' this command needs a latex engine to process. After processing it is saved as byte64 image   #
# in the html body or tag of <img ... width='6.19xDPI'/>.                                           #
#                                                                                                   #
#####################################################################################################
"""

class EducationalResourceEditor(QWidget):

    # Managed with QGridLayout
    # Grid divided into 5x6 (rows x columns)
    
    def __init__(self):

        super().__init__()
        self.id = 0

        main_layout = QGridLayout(self)
        self.setContentsMargins(10,0,10,25)

        page_title = QLabel('RESOURCE EDITOR')
        page_title.setProperty('class','heading2')

        main_layout.addWidget(page_title,0,0,1,1,Qt.AlignmentFlag.AlignTop)
        
        self.content_description_input = RichTextEdit()        

        # 10 + 10 margins of tow edges and 15 pixel for scroll bar = 35 pixels
        self.content_description_input.setFixedWidth(state.EDU_ITEM_PIXELS + 35)

        self.content_description_input.setPlaceholderText("Content")
        self.content_description_input.setAcceptRichText(True)  # Enable rich text support
        main_layout.addWidget(self.content_description_input,2,0)
        
        self.answer_input = QTextEdit(self)
        # 10 + 10 margins of tow edges and 15 pixel for scroll bar = 35 pixels
        self.answer_input.setFixedWidth(state.EDU_ITEM_PIXELS + 35)  
        self.answer_input.setPlaceholderText("Answer")
        self.answer_input.setAcceptRichText(True)  # Enable rich text support
        main_layout.addWidget(self.answer_input,4,0)

        
        self.create_right_panel(main_layout)
        
        widget = self.create_content_commands()
        main_layout.addWidget(widget,1,0)
        widget = self.create_answer_commands()
        main_layout.addWidget(widget,3,0)


        btn = QPushButton('  DELETE')
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\trash-2'))

        btn.setToolTip('Removes the current record form database')
        btn.clicked.connect(self.remove_record)
        main_layout.addWidget(btn,3,3,1,1,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop)
        
        save_button = QPushButton('  SAVE')
        save_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\database.svg'))
        save_button.clicked.connect(self.save_to_database)
        main_layout.addWidget(save_button,3,4,1,1,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop)


    def create_right_panel(self,layout:QGridLayout):

        self.Id_label = QLabel()
        self.Id_label.setProperty('class','caption')
        layout.addWidget(self.Id_label, 0,2,1,2,Qt.AlignmentFlag.AlignBottom)
        layout.setColumnStretch(3,1)
        back_button = QPushButton() 
        # Back Navigation
        back_button.setText('')
        back_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\chevron-left.svg'))
        back_button.setProperty('class','grouped_mini')
        back_button.setToolTip(ToolTips['Back'])
        back_button.clicked.connect(lambda _, direction='<':self.load_record(direction))

        layout.addWidget(back_button,0,4,1,1,Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignBottom)
        next_button = QPushButton()

        next_button.setText('')
        next_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\chevron-right.svg'))
        next_button.setProperty('class','grouped_mini')
        next_button.setToolTip(ToolTips['Next'])
        next_button.clicked.connect(lambda _ , direction='>':self.load_record(direction))
        
        layout.addWidget(next_button,0,4,1,1,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignBottom)

        layout.addWidget(QLabel('Source:'),1,1)
        
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Source")
        layout.addWidget(self.source_input,1,2,1,3)
        

        self.additional_details_input = QTextEdit(self)
        
        self.additional_details_input.setPlaceholderText("Additional Details")
        self.additional_details_input.setAcceptRichText(True)  # Enable rich text support
        layout.addWidget(self.additional_details_input,2,1,1,4)

        layout.addWidget(QLabel('Score'),3,1)
        self.score_input = QLineEdit('1')
        self.score_input.setFixedWidth(100)
        layout.addWidget(self.score_input,3,2)


    def create_content_commands(self):

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,3,0)
        layout.setSpacing(2)

        layout.addWidget(QLabel('Content'))
        layout.addStretch(1)
        
        # LaTeX
        btn_latex = QPushButton('')
        btn_latex.setProperty('class','mini')
        btn_latex.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\TeX.svg'))
        btn_latex.setToolTip(ToolTips['Generate LaTeX'])

        menu_latex = QMenu(self)
        btn_latex.setMenu(menu_latex)
        menu_latex.addAction('New LaTeX script', lambda sender=self.content_description_input: self.___config_latex(sender))
        menu_latex.addAction('Run LaTeX', lambda sender= self.content_description_input: self.run_latex(sender))
                 
        layout.addWidget(btn_latex)

        # HTML
        btn_html = QPushButton('')
        btn_html.setProperty('class','mini')
        btn_html.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\html-code.svg'))
        btn_html.setToolTip(ToolTips['Generate HTML'])
        menu_html = QMenu(self)
        btn_html.setMenu(menu_html)
        menu_html.addAction('New HTML Script',lambda sender=self.content_description_input: self.___config_basic_html(sender))
        menu_html.addAction('Run HTML',lambda _, sender=self.content_description_input: self.run_html(sender))
        
        layout.addWidget(btn_html)
        
        # INSERT BUTTON(Upload Image and insert into current content)
        add_img_button = QPushButton('')
        add_img_button.setProperty('class','mini')
        add_img_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\image-plus.svg'))
        add_img_button.setToolTip(ToolTips['Insert Image'])
        add_img_button.clicked.connect(lambda _, sender= self.content_description_input, arg=SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg, options='+'))
        
        layout.addWidget(add_img_button)

        # Add Snipping tools button
        snip_button = QPushButton("")
        snip_button.setProperty('class','mini')
        snip_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\square-bottom-dashed-scissors.svg'))
        snip_button.setToolTip(ToolTips['Insert Image from screen'])
        snip_button.clicked.connect(lambda _, t = self.content_description_input :self.run_snipping_tool(t))
        layout.addWidget(snip_button)

        ####################################################################################################
        # INSERT MENU(Clean content and upload files as new content)
        button = QPushButton('')
        button.setProperty('class','mini')
        button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\upload.svg'))
        button.setToolTip(ToolTips['Upload File'])

        menu = QMenu(button)
        menu.addAction('Plain text',lambda sender= self.content_description_input, arg= SupportedFileTypes.TEXT: self.upload_file(sender=sender,arg=arg))
        menu.addAction('RTF',lambda sender= self.content_description_input,arg= SupportedFileTypes.RTF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Image',lambda sender= self.content_description_input, arg=SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg))
        menu.addAction('PDF(Editable)',lambda sender= self.content_description_input,arg= SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='Editable'))
        menu.addAction('PDF(Readonly)',lambda sender= self.content_description_input,arg=SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='ReadOnly'))
        menu.addAction('Word(docx)',lambda sender= self.content_description_input,arg= SupportedFileTypes.DOCX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('LaTeX',lambda sender= self.content_description_input,arg= SupportedFileTypes.LaTeX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Html',lambda sender= self.content_description_input,arg=SupportedFileTypes.HTML: self.upload_file(sender=sender,arg=arg))
        
        button.setMenu(menu)
        
        layout.addWidget(button)
        ####################################################################################################
  
        from_db_btn = QPushButton("")
        from_db_btn.setProperty('class','mini')
        from_db_btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\database-search.svg'))
        from_db_btn.setToolTip(ToolTips['Find in database'])

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

        menu_layout = QHBoxLayout(widget)        
        # Add a QLineEdit
        line_edit = QLineEdit('')
        line_edit.setPlaceholderText("Id of edu resource ...")
        menu_layout.addWidget(line_edit)

        # Add Find Id QPushButton
        inner_button = QPushButton('')
        inner_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\search.svg'))
        inner_button.setProperty('class','mini')
        inner_button.clicked.connect(lambda _, sender= line_edit: self.load_from_database(sender))
        menu_layout.addWidget(inner_button)

        # Set the menu to the QPushButton
        from_db_btn.setMenu(menu)

        layout.addWidget(from_db_btn)
        ######################################################################################################


        btn = QPushButton('')
        btn.setProperty('class','mini')
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\text.svg'))
        btn.setToolTip(ToolTips['New Content'])
        btn.clicked.connect(self.clear_content)
        layout.addWidget(btn)

        # separator
        layout.addWidget(QLabel('|'))

        btn_mark = QPushButton('')
        btn_mark.setProperty('class','mini')
        btn_mark.setToolTip(ToolTips['Set bookmark'])
        # Marking an Edu-Item is done in order to revise before distribution.
        # For variety of reasons, it may be necessary to make changes to it
        # or it may be necessary to temporarily prevent its distribution.
        # Keyword [MARKED] in the text emphasizes this point. User can insert
        # some notes after this keyword, The text that has this keyword should
        # not be distributed before it is removed.
        # Notice: application of this mark is in the 'EduResourceViewer' form. 
        btn_mark.clicked.connect(lambda :(
                                    self.additional_details_input.moveCursor(QTextCursor.MoveOperation.Start),
                                    self.additional_details_input.insertPlainText('[MARKED]\n' ),
                                    self.additional_details_input.moveCursor(QTextCursor.MoveOperation.Up),
                                    self.additional_details_input.setFocus(Qt.FocusReason.MouseFocusReason)
                                        ))
        
        btn_mark.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\bookmark.svg'))
        layout.addWidget(btn_mark)


        widget = QWidget()
        widget.setFixedWidth(state.EDU_ITEM_PIXELS + 35)
        widget.setLayout(layout)

        return widget
        
    def create_answer_commands(self):

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,3,0)
        layout.setSpacing(2)
        layout.addWidget(QLabel('Answer'))
        layout.addStretch(1)
        # LaTeX
        btn_latex = QPushButton('')
        btn_latex.setProperty('class','mini')
        btn_latex.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\Tex.svg'))
        btn_latex.setToolTip(ToolTips['Generate LaTeX'])
        menu_latex = QMenu(self)
        btn_latex.setMenu(menu_latex)
        menu_latex.addAction('New LaTeX script', lambda sender=self.answer_input: self.___config_latex(sender))
        menu_latex.addAction('Run LaTeX', lambda sender= self.answer_input: self.run_latex(sender))
                 
        layout.addWidget(btn_latex)

        # HTML
        btn_html = QPushButton('')
        btn_html.setProperty('class','mini')
        btn_html.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\html-code.svg'))
        btn_html.setToolTip(ToolTips['Generate HTML'])
        menu_html = QMenu(self)
        btn_html.setMenu(menu_html)
        menu_html.addAction('New HTML Script',lambda sender=self.answer_input: self.___config_basic_html(sender))
        menu_html.addAction('Run HTML',lambda _, sender=self.answer_input: self.run_html(sender))
        
        layout.addWidget(btn_html)
        
        # INSERT BUTTON(Upload Image and insert into current content)
        button = QPushButton('')
        button.setProperty('class','mini')
        button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\image-plus.svg'))
        button.setToolTip(ToolTips['Insert Image'])
        button.clicked.connect(lambda _, sender= self.answer_input, arg=SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg, options='+'))
        
        layout.addWidget(button)

        # Add Snipping tools button
        snip_button = QPushButton("")
        snip_button.setProperty('class','mini')
        snip_button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\square-bottom-dashed-scissors.svg'))
        snip_button.setToolTip(ToolTips['Insert Image from screen'])
        snip_button.clicked.connect(lambda _, t = self.answer_input:self.run_snipping_tool(t))

        layout.addWidget(snip_button)

        # INSERT MENU(Clean content and upload files as new content)
        button = QPushButton('')
        button.setProperty('class','mini')
        button.setToolTip(ToolTips['Upload File'])
        button.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\upload.svg'))
        menu = QMenu(button)
        menu.addAction('Plain text',lambda sender= self.answer_input, arg= SupportedFileTypes.TEXT: self.upload_file(sender=sender,arg=arg))
        menu.addAction('RTF',lambda sender= self.answer_input,arg= SupportedFileTypes.RTF: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Image',lambda sender= self.answer_input, arg=SupportedFileTypes.IMAGE: self.upload_file(sender=sender,arg=arg))
        menu.addAction('PDF(Editable)',lambda sender= self.answer_input,arg= SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='Editable'))
        menu.addAction('PDF(Readonly)',lambda sender= self.answer_input,arg=SupportedFileTypes.PDF: self.upload_file(sender=sender,arg=arg, options='ReadOnly'))
        menu.addAction('Word(docx)',lambda sender= self.answer_input,arg= SupportedFileTypes.DOCX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('LaTeX',lambda sender= self.answer_input,arg= SupportedFileTypes.LaTeX: self.upload_file(sender=sender,arg=arg))
        menu.addAction('Html',lambda sender= self.answer_input,arg=SupportedFileTypes.HTML: self.upload_file(sender=sender,arg=arg))
        
        button.setMenu(menu)
        
        layout.addWidget(button)
        widget = QWidget()
        widget.setLayout(layout)

        return widget    

    def ___config_basic_html(self,sender:QTextEdit):
        
        sender.document().clear()
        
        text = '<b>Add here main content.</b>'

        html_template  = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
        html_template += '<html lang="en">\n'
        html_template += '<head> <meta charset="UTF-8" name="viewport" content="width=device-width, initial-scale=1.0"></head>\n'
        html_template += f'<body style="width:{state.EDU_ITEM_PIXELS}px;">\n'
        html_template += '   <main>\n'
        html_template += '      ' + text + '\n'
        html_template += '   </main>\n'
        html_template += '</body>\n'
        html_template += '</html>'

        sender.document().setPlainText(html_template)
        
        #self.___highlightText(sender, text)
    

    def ___config_latex(self,sender:QTextEdit):

        #self.___document_type = MyJobAssistant.DocumentType.LaTeX

        sender.document().clear()

        text = '   Add here main content '
        documentclass = 'article'
        package = 'xepersian'
        font='Yas'

        # Generates latex template
        latex_content = ('\\documentclass{{{}}}\n'
                          '\\usepackage{{{}}}\n'
                          '\\settextfont{{{}}}\n'
                          '\\begin{{document}}\n{}\n'
                          '\\end{{document}}'
                         ).format(documentclass, package, font, text)

        sender.document().setPlainText(latex_content)
        
        self.___highlightText(sender, text)  


    def ___highlightText(self,sender:QTextEdit,search_text):
        # The text to search for
        # Get the QTextDocument from the QTextEdit
        document = sender.document()

        # Create a QTextCharFormat to define the highlighting style
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("yellow"))  # Set background color
        highlight_format.setForeground(QColor("red"))     # Set text color (optional)

        # Create a QTextCursor to manipulate the document
        cursor = sender.textCursor()

        # Move the cursor to the beginning of the document
        cursor.movePosition(QTextCursor.Start)

        # Loop to find and highlight all occurrences of the text
        while True:
            # Search for the text using QTextDocument's find method
            cursor = document.find(search_text, cursor, QTextDocument.FindFlag.FindCaseSensitively)
            if cursor.isNull():
                break  # Exit the loop if no more occurrences are found

            # Apply the highlighting format to the found text
            cursor.mergeCharFormat(highlight_format)


    def clear_content(self):

        self.id=0
        self.Id_label.setText('(New item)')
        self.source_input.clear()
        self.score_input.clear()
        self.content_description_input.document().clear()
        self.answer_input.document().clear()
        self.additional_details_input.clear()


    def upload_PDF_as_html(self, PDF_path, sender:QTextEdit):

        try:

            # Open the PDF file using PyMuPDF
            PDF_document = pymupdf.open(PDF_path)

            # Iterate through each page in the PDF
            for page in PDF_document:
                # Load the page
                html = page.get_text('html')
                #html = '<html><br><head><br><meta name="PDF" charset="utf-8"/><br></head><br>'
                #html += f'<body style="width:{MyJobAssistant.EDU_CONTENT_WIDTH*DPI}px"><br>{html}<br></body><br></html>'
                # Set the HTML content in the QTextEdit
                sender.setHtml(html)
                
                sender.insertPlainText("\n\n")  # Add a newline after each page

        except Exception as e:
            print(f"Error processing PDF: {e}")


    def upload_file(self,sender:QTextEdit, arg:str=SupportedFileTypes.IMAGE, options=None):
        
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

                html_content = f'<img src="data:image/png;base64,{base64_image}" width="{state.EDU_ITEM_PIXELS}"/>'
                # Set the HTML content in the QTextEdit
                if options == '+': 
                    sender.insertHtml(html_content)
                else: 
                    sender.document().clear()
                    sender.setHtml(html_content)

            elif arg == SupportedFileTypes.PDF:
                sender.document().clear()
                if options == 'Editable':
                    self.upload_PDF_as_html(file_path, sender)
                else:

                    base64s = pdf_to_base64(file_path)
                    html_content = f'<img src="data:image/png;base64,{base64s[0]}" width="{state.EDU_ITEM_PIXELS}"/>'
                    
                    # Set the HTML content in the QTextEdit
                    sender.setHtml(html_content)


            elif arg in [SupportedFileTypes.TEXT,
                         SupportedFileTypes.RTF,
                         SupportedFileTypes.LaTeX,
                         SupportedFileTypes.PDF,
                         SupportedFileTypes.HTML]:
                sender.document().clear()
                self.read_plain_text(sender, file_path)


            #elif arg == SupportedFileTypes.DOCX:
            #    # Loses text formatting
            #    sender.document().clear()
            #    html = pypandoc.convert_file(file_path,'html',extra_args=['--embed-resources'])
            #    sender.document().setHtml(html)


    # we read Plain text, but save in HTML format as RTF data
    def read_plain_text(self,sender:QTextEdit, file_path):
        
        file_name, extension = os.path.splitext(file_path)
        
        data = ''        

        if extension == '.txt':

            with open(file_path, 'r') as file: data = file.read()
            sender.document().setHtml(data)

        elif extension in ['.tex','.html']:

            with open(file_path, 'r', encoding='utf-8') as file: data = file.read()
            sender.document().setPlainText(data)
        
        #elif extension == '.rtf':
            # Prerequisits of using pypandoc:
            # 1) Install Pandoc using windows installer
            # 2) set path to environment variable
            #   1) Press WINDOWS LOGO + R
            #   2) run sysdm.cpl
            #   3) go to  advanced tab
            #   4) click Enviorenment Variables ...
            #   5) go to system variables section
            #   6) scroll to and select 'Path' item
            #   7) click Edit\ click New and add 'C:\Program Files\pandoc-3.6.3\'
            #   8) save changes
            # 2) install pypandoc using pip install pypandoc
            # import pypandoc

            #html = pypandoc.convert_file(file_path, "html")
        
            #sender.document().setHtml(html)
    

    def run_html(self, sender:QTextEdit):

        html = sender.document().toPlainText()

        sender.document().clear()

        sender.document().setHtml(html)
    

    def run_latex(self,sender:QTextEdit):

        html = helpers.run_latex(sender.toPlainText(), compile='xepersian', output_PDF_name= 'edu-resource.PDF')
        # Set the HTML content in the QTextEdit
        sender.clear()
        sender.insertHtml(html)
        
        
    def run_snipping_tool(self,target:QTextEdit):

        active = QApplication.activeWindow()
        active.hide()
        snipping_window = SnippingWindow(self)
        snipping_window.screen_captured.connect(lambda data:
            (
            target.insertHtml(f'<img src="data:image/png;base64,{pixmap_to_base64(data)}" width="{state.EDU_ITEM_PIXELS}"/>'),
            active.show()
            ))

        snipping_window.screen_capture_canceled.connect(active.show)

        snipping_window.showFullScreen()  # Ensure full coverage
        snipping_window.activateWindow()
        snipping_window.raise_()

    def remove_record(self):

        b = QMessageBox.warning(self,'WARNING',f'Current record with id "{self.id}" will be removed.\n' + 
                            'After removing is not retrived. Are you sure?',
                            QMessageBox.StandardButton.Yes,QMessageBox.StandardButton.Cancel)
        
        if b == QMessageBox.StandardButton.Cancel: return

        query  = f"DELETE FROM educational_resources WHERE id={self.id};" 
        
        try:

            cursor = TeacherAssistant.db_connection.cursor()
            cursor.execute(query)
            msg = f'The record {self.id} removed from database.'
            self.clear_content()

        except psycopg2.Error as e:
            msg = f'Database error: {e}.'
        
        PopupNotifier.Notify(self,"Message", msg, 'bottom-right', delay=3000, background_color='#353030',border_color="#2E7D32")

    def load_record(self, direction:str=' >'):
        
        try:
            order = 'ORDER BY Id DESC' if direction == '<' else ' ORDER BY Id ASC'
            where =  f'WHERE Id {direction} {self.id} {order} LIMIT 1;' if not direction == '' else f'WHERE Id>0 {order} LIMIT 1;'

            # Fetch the data from the database
            query  = "SELECT Id, source_, score_, content_description_, additional_details_, answer_ FROM educational_resources " + where
            
            cursor = TeacherAssistant.db_connection.cursor()
            cursor.execute(query)

            row = cursor.fetchone()
            
            msg = f"No content found in the database for Id {direction} {self.id}."

            if row:

                self.clear_content()

                self.id = int(row[0])
                self.source_input.setText(row[1])
                self.score_input.setText(str(row[2]))
                if not helpers.is_rtf(row[3]):
                
                    # this used to HTML and LaTeX source files(pure LaTeX or HTML data)
                    self.content_description_input.document().setPlainText(row[3])

                else:                     
                
                    # This is used to RTF or txt to display in the QTextEdit properly
                    self.content_description_input.document().setHtml(row[3])
                
                self.additional_details_input.setText(row[4])

                if helpers.is_rtf(row[4]):
                    self.answer_input.document().setHtml(row[5])
                else:
                    self.answer_input.document().setPlainText(row[5])

                msg = "Content loaded from database."
                
                self.Id_label.setText('Content editing | ' + str(self.id))

                self.content_description_input.minimumSizeHint()
            
        except psycopg2.Error as e:
            
            msg = f"Database error: {e}."
            print(msg)

        PopupNotifier.Notify(self,"Message", msg, 'bottom-right')

    def load_from_database(self,sender:QLineEdit):
        
        id  = sender.text()
        id  = 0 if id == '' else int(id)
        
        if id == int(self.id) :return
        
        self.id = id
        self.load_record('=')

    # We save the all data as text, but to manage advanced datatypes of text like rich texts with image, 
    # table or formulas we need advanced control on our data, becuase of this to simple managment, we save:
    # Plaintext and RTF as HTML format, Also we write LaTeX and HTML code in the editor directly, these type
    # of text are saved directly and without any conversion. to resore PlainText and RTF, will useing setHtml()
    # method of QEditText widget, and  for Html and LaTeX types will use setPlainText() method.
    # deference between RTF and HTML format in our contents is: we use HTML format with managing HTML tags, and
    # the text without HTML tags, but containing text formating is RTF. also the RTF text without formated
    # content, is mean PlainText.
    def save_to_database(self):
        
        # Edu-Item source book
        source = self.source_input.text()
        # score to evaluate
        score = self.score_input.text()

        score = float(score) if score !='' and score.replace('.','').isnumeric() else '1'
        
        # Get the entire content of QTextEdit
        content = self.content_description_input.document().toPlainText()

        if helpers.is_rtf(content): content = self.content_description_input.toHtml()

        answer = self.answer_input.document().toPlainText()

        if helpers.is_rtf(answer): answer = self.answer_input.document().toHtml()

        details = self.additional_details_input.toPlainText()
        
        try:

            cursor = TeacherAssistant.db_connection.cursor()

            query ="INSERT INTO educational_resources "\
                   "(source_, score_, content_description_, answer_, additional_details_)"\
                   "VALUES (%s, %s, %s, %s, %s) RETURNING id;"
                
            variables = (source, score, content, answer, details)

            msg = 'inserted'
               
            if self.id>0:
                query = "UPDATE educational_resources SET source_ = %s, score_= %s, content_description_= %s,"\
                        "answer_= %s, additional_details_= %s WHERE Id= %s RETURNING id;"

                variables = (source, score, content, answer, details, self.id)    # Save the HTML content to the database
                                
                msg = 'updated'
            
            cursor.execute(query, variables)
                
            self.id = cursor.fetchone()[0]
            
            self.Id_label.setText(f'{str(self.id)} | Content recently {msg}.')

            msg = f'Data {msg} successfully.'

        except psycopg2.Error as e:

            msg = f'Database error: {e}.'

        PopupNotifier.Notify(self,"Message", msg)


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

class EduResourcesViewer(QWidget):
    
    def __init__(self,parent=None, target_students=[dict]):

        super().__init__(parent)
        #self.filter_stat = 'not-filtered'

        self.initalized = False

        self.selected_card:Widgets.EduItemWidget = None

        self.target_students = target_students

        # Defualt dispaly configs
        self.disply_columns = 2

        self.initUI()
    
    def initUI(self):

        if self.initalized : return

        self.setContentsMargins(10,0,10,10)

        # Initialize the UI. (QGridLayout 3x2)
        # Column 1 contains filter options and edu items list,
        # and column 2 has provided for nessecery command, template settings and other actions.
        main_layout = QGridLayout(self)
        
        header_widget = QWidget()
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(0,0,0,0)
        header.setSpacing(2)
        page_title = QLabel('RESOURCE COLLECTION')
        page_title.setProperty('class','heading2')
        header.addWidget(page_title,1)

        #header.addStretch(1)
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Filter data using 'Source' ...")
        self.source_input.textChanged.connect(lambda text:self.load_data(sender=None, filter=text) )
        header.addWidget(self.source_input,1)
        
        """btn = QPushButton()
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\funnel.svg'))
        btn.setProperty('class','mini')
        btn.clicked.connect(lambda _,sender= btn, input=self.source_input: self.load_data(sender=sender,filter=input.text()))
        header.addWidget(btn,alignment=Qt.AlignmentFlag.AlignCenter)"""

        btn3 = QPushButton('distribute')
        header.addWidget(btn3)

        btn3.setMenu(self.create_distribution_options())
        # Create card grid view
        self.card_grid = CardGridView(self.disply_columns)
       # Connect signals
        self.card_grid.card_selected.connect(self.on_card_selected)
        self.card_grid.card_removed.connect(self.on_card_removed)
        
        # Filter and it's commands
        main_layout.addWidget(header_widget, 0, 0) # Cell [0,0]
        # QListViewWidget for Edu-content
        main_layout.addWidget(self.card_grid,1,0)# Cell [1,0]
        main_layout.setRowStretch(1,1)
        
        self.templates_created = False

        self.initalized = True

        self.load_data()

    def get_deadline(self): return self.deadline_input.text()
    
    def get_distribution_time(self): return self.dist_time_input.text()
    
    def create_distribution_options(self):
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

        dist_options_layout = QGridLayout(widget) 
        dist_options_layout.setSpacing(0)
        dist_options_layout.addWidget(QLabel('Send to:'),0,0)
        
        stu_list = QListView(self)
        stu_list.setFixedWidth(150)
        stu_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        
        model = QStandardItemModel()

        for item in self.target_students:
            new_item = QStandardItem(f'{item['Name']}\n{item['Id']}')
            model.appendRow(new_item)

        stu_list.setModel(model)
        
        dist_options_layout.addWidget(stu_list,1,0,3,1, Qt.AlignmentFlag.AlignTop)

        dist_options_layout.addWidget(QLabel('distribution time'),0,1,Qt.AlignmentFlag.AlignTop)

        self.dist_time_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        dist_options_layout.addWidget(self.dist_time_input,1,1,Qt.AlignmentFlag.AlignTop)

        dist_options_layout.addWidget(QLabel('deadline'),2,1,Qt.AlignmentFlag.AlignTop)
        
        self.deadline_input = QLineEdit((datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        dist_options_layout.addWidget(self.deadline_input,3,1,Qt.AlignmentFlag.AlignTop)

        dist_options_layout.setRowStretch(3,1)

        btn4 = QPushButton('distribute')
        btn4.clicked.connect(self.distribute)

        dist_options_layout.addWidget(btn4,4,0,1,2)        
        
        return menu
        

    def distribute(self):
        '''Distributes selected edu-items to the students'''
        if len(self.target_students) == 0:
            self.show_template_selector_dlg()
        else:

            try:
                
                items = self.get_selected_contents()
        
                if len(items) == 0: 
                    PopupNotifier.Notify(self,'SEND','No Edu-Item selected.')
                    return
                
                stu_cnt = len(self.target_students)
                msg  = f'Number of {len(items)-1} edu-item{'s' if len(items)-1>1 else ''} will be assigned to {stu_cnt} student{'s' if stu_cnt>1 else ''}\n'
                msg += 'are you sure?'

                if QMessageBox.StandardButton.Cancel == QMessageBox.question(self,'',msg,QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Cancel): return
                # Get current UTC time
                utc_time = self.get_distribution_time()

                future_time = self.get_deadline()
                
                for stu in self.target_students: 

                    # List of Edu-Items
                    for item in items[:len(items)-1]: # last index was included sub totlal values
                        cmd = 'INSERT INTO quests(qb_id, student_id, max_point_, earned_point_, assign_date_, deadline_, answer_, reply_date_, feedback_) '
                        cmd += 'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)'
        
                        values = (item['Id'], stu['Id'], item['score'], 0, str(utc_time), str(future_time), None, None, None)

                        TeacherAssistant.db_connection.cursor().execute(cmd,values)
                
                msg  = f'Number of {len(items)-1} edu-item{'s' if len(items)-1>1 else ''} was assigned to {stu_cnt} student{'s' if stu_cnt>1 else ''} successfully'
                
                PopupNotifier.Notify(self,'',msg)
            
            except Exception as e: PopupNotifier.Notify(self,'',f'Database error: {e}.')


    def show_template_selector_dlg(self):

        if not self.templates_created:

            self.config_layout = QGridLayout()
            self.config_layout.setContentsMargins(16,16,16,16)
            self.config_layout.addWidget(QLabel('SELECT OUTPUT TEMPLATE'),0,0)
            template_selector_combo = QComboBox()
            template_selector_combo.setPlaceholderText('-- Select a template --')
            template_selector_combo.addItems(['Classroom quiz','Formal exam'])
            template_selector_combo.currentIndexChanged.connect(lambda _, sender= template_selector_combo: self.template_changed(sender))
            
            self.config_layout.addWidget(template_selector_combo,1,0)

            self.dialog = QDialog(self)
            self.dialog.setWindowTitle('DISTRIPUTION')
            self.dialog.setFixedWidth(400)
            self.dialog.setLayout(self.config_layout)

            geo = QApplication.activeWindow().geometry()
            x = geo.left() + geo.width()//2 - self.dialog.width()/2
            self.dialog.move(x, geo.top() + 40)
            #self.dialog.move(QPoint())
            template_selector_combo.setCurrentIndex(0)

        self.dialog.exec()

    
    def template_changed(self,sender:QComboBox):
        
        index = sender.currentIndex()
        if index<0: return

        self.edu_template_file = ''

        if not self.templates_created: 

            self.stu_info_input = QLineEdit('')
            self.stu_info_input.setPlaceholderText('Student name')
            self.config_layout.addWidget(self.stu_info_input,2,0)
            
            self.stu_id_input = QLineEdit('')
            self.stu_id_input.setPlaceholderText('Student Id')
            self.config_layout.addWidget(self.stu_id_input,3,0)
            
            self.teacher_input = QLineEdit('')
            self.teacher_input.setPlaceholderText('Teacher name')
            self.config_layout.addWidget(self.teacher_input,4,0)

            self.author_input = QLineEdit('')
            self.author_input.setPlaceholderText('Author')
            self.config_layout.addWidget(self.author_input,5,0)

            self.org_info_input = QPlainTextEdit('')
            self.org_info_input.setPlaceholderText('Oragnisation info')
            self.org_info_input.document().setDefaultTextOption(Qt.AlignmentFlag.AlignCenter)
            self.org_info_input.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
            self.config_layout.addWidget(self.org_info_input,6,0)

            self.book_grade_input = QLineEdit('')
            self.book_grade_input.setPlaceholderText('Book and Grade info')
            self.config_layout.addWidget(self.book_grade_input,7,0)

        
            self.field_input = QLineEdit('')
            self.field_input.setPlaceholderText('Field Study')
            self.config_layout.addWidget(self.field_input,8,0)

            self.term_input = QPlainTextEdit()
            self.term_input.document().setHtml('')
            self.term_input.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
            self.term_input.setPlaceholderText('Term')
            self.config_layout.addWidget(self.term_input,9,0)
                        

            self.date_input = QLineEdit('')
            self.date_input.setPlaceholderText('Exam date')
            self.config_layout.addWidget(self.date_input,10,0)


            self.clock_input = QLineEdit('')
            self.clock_input.setPlaceholderText('Clock: --:-- ')
            self.config_layout.addWidget(self.clock_input,11,0)

        
            self.time_input = QLineEdit('')
            self.time_input.setPlaceholderText('Time: --')
            self.config_layout.addWidget(self.time_input,12,0)
            
            btn = QPushButton('Generate Edu-content')
            btn.clicked.connect(lambda: self.generate_edu_contents())
            self.config_layout.addWidget(btn,13,0)
           
            self.templates_created = True

            
   
        
        if self.templates_created:
            self.stu_info_input.setVisible(False)
            self.stu_id_input.setVisible(False)
            self.teacher_input.setVisible(False)
            self.author_input.setVisible(False)
            self.org_info_input.setVisible(False)
            self.book_grade_input.setVisible(False)
            self.field_input.setVisible(False)
            self.term_input.setVisible(False)
            self.date_input.setVisible(False)
            self.clock_input.setVisible(False)
            self.time_input.setVisible(False)
            
        

        new_row_tmp = ''

        language = TeacherAssistant.Language

        config_file  = state.application_path + f'\\resources\\templates\\{Edu_Template_Files[index]}-config.json'
        template_config.set_path(config_file)
        config = template_config.read()

        # Common configs
        self.stu_info_input.setPlaceholderText(config[language]['Student name'])
        self.stu_info_input.setText(config[language]['Student name'])
        self.book_grade_input.setPlaceholderText(config[language]['Book'])
        self.book_grade_input.setText(config[language]['Book'])
        self.date_input.setPlaceholderText(config[language]['Date'])
        self.date_input.setText(config[language]['Date'])
            
        self.stu_info_input.setVisible(True)
        self.book_grade_input.setVisible(True)
        self.date_input.setVisible(True)

        # Special configs
        if index == 0: # Classroom quiz has been selected

                self.stu_id_input.setVisible(False)
                self.teacher_input.setVisible(False)
                self.author_input.setVisible(False)
                self.org_info_input.setVisible(False)
                self.field_input.setVisible(False)
                self.term_input.setVisible(False)
                self.clock_input.setVisible(False)
                self.time_input.setVisible(False)


                new_row_tmp =  '        <tr>\n'
                new_row_tmp += f'            <td style="border-left:none;border-top:none;border-right:none; vertical-align:top;">{{}})</td>\n'
                new_row_tmp += f'            <td style="border-left:none;border-top:none;border-right:none; width:{state.EDU_ITEM_PIXELS}; text-align:{{}}">{{}}</td>\n'
                new_row_tmp += f'            <td style="border-left:none;border-top:none;border-right:none; vertical-align:top">{{}}</td>\n'
                new_row_tmp +=  '        </tr>\n'
        
        # row index,text_align,content,point
        elif index == 1: # Formal template hass been selected
                
                self.stu_id_input.setVisible(True)
                self.teacher_input.setVisible(True)
                self.author_input.setVisible(True)
                self.org_info_input.setVisible(True)
                self.field_input.setVisible(True)
                self.term_input.setVisible(True)
                self.clock_input.setVisible(True)
                self.time_input.setVisible(True)
                

                self.stu_id_input.setPlaceholderText(config[language]['Student Id'])
                self.stu_id_input.setText(config[language]['Student Id'])
                self.teacher_input.setPlaceholderText(config[language]['Teacher name'])
                self.teacher_input.setText(config[language]['Teacher name'])
                self.author_input.setPlaceholderText(config[language]['Author'])
                self.author_input.setText(config[language]['Author'])
                self.org_info_input.setPlaceholderText(config[language]['Organization info'])
                self.org_info_input.setPlainText(config[language]['Organization info'])               
                self.org_info_input.setFixedHeight(100)
                self.field_input.setPlaceholderText(config[language]['Field Study'])
                self.field_input.setText(config[language]['Field Study'])
                self.term_input.setPlaceholderText(config[language]['Academic year'])
                self.term_input.setPlainText(config[language]['Academic year'])
                self.term_input.setFixedHeight(60)
                self.clock_input.setPlaceholderText(config[language]['Clock'])
                self.clock_input.setText(config[language]['Clock'])
                self.time_input.setPlaceholderText(config[language]['Time'])
                self.time_input.setText(config[language]['Time'])

                new_row_tmp =  '        <tr>\n'
                new_row_tmp += f'            <td>{{}}</td>\n'
                new_row_tmp += f'            <td style="width:{state.EDU_ITEM_PIXELS}; text-align:{{}}">{{}}</td>\n'
                new_row_tmp += f'            <td>{{}}</td>\n'
                new_row_tmp +=  '        </tr>\n'
                # row index,text_align,content,point

        self.content_row_template = new_row_tmp
        self.edu_template_file = Edu_Template_Files[index]
        self.config = config

        # Update layout and dialog size after all widgets are added
        self.config_layout.invalidate()
        self.config_layout.activate()
        self.dialog.adjustSize()

    def remove_card(self):
        """Remove the selected card"""
        selected_card = self.card_grid.get_selected_card()
        if selected_card:
            # Find the card ID
            for card_id, card in self.card_grid.cards.items():
                if card.widget == selected_card:
                    self.card_grid.remove_card(card_id)
                    break
    
    def clear_cards(self):
        """Clear all cards"""
        self.card_grid.clear()
        self.next_card_id = 1
    
    def on_card_selected(self,widget:Widgets.EduItemWidget):

        if self.selected_card: self.selected_card.hide_titlebar()
        # Handle card selection:
        # The selected widget is type of EduItemWidget, this Item has a DataModel
        # and the DataModel has a Id Property
        widget.show_titlebar()
        self.selected_card = widget
    
    def on_card_removed(self, widget: QWidget):
        """Handle card removal"""
        pass
    
    def load_data(self,sender:QPushButton = None, filter:str=''):

        if filter =='' : self.source_input.clear()
        
        """if sender:
            if self.filter_stat == 'not-filtered':
                sender.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\refresh-ccw.svg'))
                self.filter_stat = 'filtered'
            else: 
                sender.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\funnel.svg'))
                self.filter_stat = 'not-filtered'
                filter = ''
        """

        # WHERE similarity(source_, 'درس') > 0.1;
        # WHERE name ILIKE '%john%';
        filter = f"WHERE source_ ILIKE '%{filter}%' OR TEXT(Id) ILIKE '%{filter}%'" if filter != '' else ''
        
        cursor = TeacherAssistant.db_connection.cursor()
        cursor.execute(f"SELECT Id, content_description_, score_, source_, additional_details_ FROM educational_resources {filter};")
        data = cursor.fetchall()
        
        if data:
            self.card_grid.clear()
            # Add each HTML item to the list widget
            for record in data:
                # Create a custom widget for the item
                edu_item = Widgets.EduItemWidget(record, state.EDU_ITEM_PIXELS + 20)
                
                self.card_grid.add_card(record[0], edu_item)

    def generate_edu_contents(self):
        # Validate template selection and existence
        if not self.___validate_template__(): return

        # Get selected items and validate
        selected_content = self.get_selected_contents()

        if not selected_content:
            PopupNotifier.Notify(self, 'Info', 'No item selected')
            return

        # Generate HTML content
        html = self.___generate_html_content__(selected_content)
        
        # Show PDF preview window
        self.___show_pdf_preview__(html)

    def ___validate_template__(self) -> bool:
        # Validate template file selection and existence
        if self.edu_template_file == '':
            PopupNotifier.Notify(self, 'Error', 'The output template has not selected.', background_color='RED')
            return False
        
        template_file = state.application_path + f'\\resources\\templates\\{self.edu_template_file}-Template.html'
        if not os.path.exists(template_file):
            PopupNotifier.Notify(self, 'Error', f'The template file not found in the specified path--> {template_file}')
            return False
            
        self.template_file = template_file
        return True
    

    def get_selected_contents(self):
        # Get selected cards and their content
        selected_content = []
        total_points = 0
        row = 0
        
        for card in self.card_grid.get_cards():
            data = card.get_data()
            if data['selected']:
                row += 1
                content = {
                    'Id':data['Id'],
                    'row': row,
                    'content': data['content'],
                    'score': float(data['score'])
                }
                selected_content.append(content)
                total_points += content['score']
        
        if selected_content:
            selected_content.append({'total_points': total_points})
            
        return selected_content

    def ___generate_html_content__(self, selected_content) -> str:
        """Generate HTML content with template placeholders replaced"""
        stream = open(self.template_file, encoding="utf-8",mode='r')
        stream.seek(0)
        html = stream.read()
        stream.close()
        language = TeacherAssistant.Language
        
        # Replace content placeholders
        new_content_template = '<!-- NEW CONTENT -->'
        text_align = self.config[language]['Text align']
        
        for item in selected_content[:-1]:  # Skip last item (total_points)
            new_row = self.content_row_template.format(
                item['row'], 
                text_align,
                item['content'], 
                item['score']
            ) + new_content_template
            html = html.replace(new_content_template, new_row, count=1)

        # Replace dimension placeholders
        dimensions = {
            '-- 2.43 inches --': f'{2.43*state.DPI}px',
            '-- 2.42 Inches --': f'{2.42*state.DPI}px',
            '-- 0.54 Inches --': f'{0.54*state.DPI}px',
            '-- 6.19 Inches --': f'{state.EDU_ITEM_PIXELS}px',
        }

        for old, new in dimensions.items(): html = html.replace(old, new)

        # Replace style placeholders
        html = html.replace('-- font-family --', self.config[language]['Font family'])
        html = html.replace('-- direction --', self.config[language]['Direction'])
        html = html.replace('-- Text Alignment --', text_align)

        # Replace content placeholders
        replacements = {
            '-- In the name of God --': self.config[language]['InTheNameOfGod'],
            '-- Stu-Name --': self.stu_info_input.text(),
            '-- Stu-Id --': self.stu_id_input.text(),
            '-- Organisation Info --': self.org_info_input.toPlainText().replace('\n','<br>'),
            '-- Academic-Year-Term --': self.term_input.toPlainText().replace('\n','<br>'),
            '-- Date --': self.date_input.text(),
            '-- Teacher-Name --': self.teacher_input.text(),
            '-- Clock --': self.clock_input.text(),
            '-- Book-Grade --': self.book_grade_input.text(),
            '-- Field --': self.field_input.text(),
            '-- Time-Pages --': self.time_input.text(),
            '-- Index --': self.config[language]['Row'],
            '-- Edu-Content --': self.config[language]['Header'],
            '-- Point --': self.config[language]['Score'],
            '-- Author: Abdh --': self.author_input.text(),
            '-- SUM --': str(selected_content[-1]['total_points']),
            '-- FOOTER SUM --': self.config[language]['Footer sum']
        }
        
        for placeholder, value in replacements.items(): html = html.replace(placeholder, value)
            
        return html

    def ___show_pdf_preview__(self, html):
        """Show PDF preview window"""
        self.dialog.setModal(False)
        self.dialog.move(10, 10)
        
        window = PdfGeneratorApp(html_content=html, parent=self.dialog)
        window.setWindowModality(Qt.WindowModality.WindowModal)
        window.move(self.dialog.geometry().topRight() + QPoint(10, 0))
        window.show()
        
        self.dialog.setModal(True)


class PdfGeneratorApp(QMainWindow):

    def __init__(self,parent =None, html_content=''):
        super().__init__(parent)
        self.html_content = html_content
        #self.output_pdf = output_pdf

        # Set up the UI
        self.setWindowTitle("HTML to PDF Generator")
        self.setGeometry(100, 100, 900, 600)

        # Create a central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add a QWebEngineView for preview
        self.preview_view = QWebEngineView()
        
        self.preview_view.setHtml(self.html_content)
        layout.addWidget(self.preview_view)

        # Add a button to generate the PDF
        self.generate_button = QPushButton("Generate PDF")
        self.generate_button.clicked.connect(self.generate_pdf)
        layout.addWidget(self.generate_button)

    def generate_pdf(self):
        # Create a QWebEnginePage for PDF generation
        page = QWebEnginePage()
        # Load the HTML content into the page
        page.setHtml(self.html_content)

        # Wait for the page to load completely before printing
        def print_to_pdf(finished):
            if finished:
                print("HTML content loaded successfully.")
                print(f"Attempting to save PDF file")

                # Set up custom margins and page layout
                # 0.5 inches for edges required
                # Margins in millimeters (left, top, right, bottom)
                margins = QMarginsF(24, 5, 24, 5) 
                page_layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                          QPageLayout.Orientation.Portrait,
                                          margins)

                from PySide6.QtWidgets import QFileDialog
                options = QFileDialog.Options()
                file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDFs (*.pdf);", options=options)
                if file_name:
                    # Save the rendered content to a PDF file with custom layout

                    page.printToPdf(file_name, page_layout)
                    #output_html = os.path.dirname(os.path.abspath(file_name)) + '\\Edu.html'
                    #stream = open(output_html, encoding="utf-8",mode='w')
                    #stream.write(self.html_content)
                    #stream.close()
                    #print("PDF saved successfully.")
                    #helpers.open_file_os(file_name)

                    PopupNotifier.Notify(self,'PDF','PDF saved successfully.\n'+file_name)

                # Quit the application after generating the PDF
                #QTimer.singleShot(1000, QApplication.instance().quit)
            else:
                print("Error: HTML content failed to load.")

        # Connect the loadFinished signal to print_to_pdf
        page.loadFinished.connect(print_to_pdf)


class StudentListPage(QWidget):
    data = []
    def __init__(self,parent):
        super().__init__()
        # SVG icons path
        self.setParent(parent)

        self.db_cursor = TeacherAssistant.db_connection.cursor()

        self.initUI()
    
    def initUI(self):
        """
        Layout structure:
        --------------------------------------------------------------------------
        Root QWidget
            └── QVBoxLayout (main_layout)
                |
                └── QWidget (header widget)
                   ├── QHBoxLayout (header_layout)
                   |   ├── QLabel (page_title)
                   |   ├── QLineEdit (search_input)
                   |   ├── QComboBox (class_filter_combo)
                   |   └── QPushButton (hamburger_btn)
                   |
                   └── QTableWidget (tableWidget)  
        --------------------------------------------------------------------------
        """
        self.search_index = 0
        self._multi_select_enabled = False
        self.setContentsMargins(10,0,10,10)
        main_layout = QVBoxLayout(self)
        
        page_title = QLabel('STUDENT LIST')
        page_title.setProperty('class','heading2')
        
        model = self.load_groups()
        # Table Widget setup
        self.tableWidget = QTableWidget()
        self.tableWidget.setAlternatingRowColors(True)

        self.tableWidget.setColumnCount(4)
        self.tableWidget.verticalHeader().hide()
        self.tableWidget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tableWidget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # creates menu with ☰ to access avilable features
        edu_btn = self.create_more_option_menu(model)
        edu_btn.setToolTip('Open options')

        search_input = QLineEdit()
        search_input.setPlaceholderText('Search')
        search_input.setFixedWidth(200)
        #search_input.setEnabled(False)
        search_input.textChanged.connect(lambda _, input= search_input: self.find_in_list(input))

        class_filter_combo = QComboBox()
        class_filter_combo.setModel(model)

        class_filter_combo.currentIndexChanged.connect(lambda _, sender=class_filter_combo:self.load_students(sender))

        class_filter_combo.setPlaceholderText("Select group")
        
        command_layout = QHBoxLayout()
        from PySide6.QtWidgets import QDateEdit
        from PySide6.QtCore import QDate

        command_layout.addWidget(page_title)
        command_layout.setAlignment(page_title,Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        command_layout.addStretch()
        command_layout.addWidget(search_input)
        command_layout.addWidget(class_filter_combo)
        command_layout.addWidget(edu_btn)
        widget = QWidget()
        widget.setLayout(command_layout)

        main_layout.addWidget(widget)
        
                
        main_layout.addWidget(self.tableWidget)

        # Set column resize modes

        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        class_filter_combo.setCurrentIndex(0)
        self.load_students(class_filter_combo)

    def show_csv_load_message(self):
        option = settings_manager.find_value('csv_show_option_message')
    
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
        settings_manager.write({"csv_show_option_message": checkbox.isChecked()})

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
                table_columns = get_postgres_columns('personal_info', TeacherAssistant.db_connection.cursor())
                
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
                    bulk_insert_csv(csv_file[0], 'personal_info', valid_mapping, TeacherAssistant.db_connection.cursor())
                
                else:
                    print("No valid mapping found!")
                
                msg = 'Load data from '+ csv_file[0]

            except Exception as e:
               msg = f'Database Error: {e}'

            PopupNotifier.Notify(self,"Message", msg, 'bottom-right', delay=5000)

    def create_more_option_menu(self,group_model=None):

        btn = QPushButton('')            
        btn.setProperty('class','grouped_mini')
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\menu.svg'))

        menu = QMenu(btn)
                
        btn.setMenu(menu)
        # Multi-selection toggle (checkable). If tableWidget hasn't been created yet,
        # store desired state in self._multi_select_enabled and apply later when table exists.
        if not hasattr(self, '_multi_select_enabled'):
            self._multi_select_enabled = False
        
        action_multi = QAction(icon=QIcon(f'{state.application_path}\\resources\\icons\\svg\\list-checks.svg'),
                               text='Enable multi-selection', parent=menu)
        action_multi.setCheckable(True)
        action_multi.setChecked(self._multi_select_enabled)
        action_multi.setToolTip('Toggle multi-row selection in the students list')

        def _toggle_multi(checked):
            # remember desired state
            self._multi_select_enabled = checked
            # apply if table widget exists
            if hasattr(self, 'tableWidget') and self.tableWidget is not None:
                mode = QAbstractItemView.SelectionMode.MultiSelection if checked else QAbstractItemView.SelectionMode.SingleSelection
                self.tableWidget.setSelectionMode(mode)

        action_multi.triggered.connect(_toggle_multi)
        
        action4 = QAction(icon= QIcon(f'{state.application_path}\\resources\\icons\\svg\\id-card.svg'), text='Add new student', parent= menu)
        action4.triggered.connect(self.open_personal_info_dialog)
        menu.addAction(action4)

        action5 = QAction(icon= QIcon(f'{state.application_path}\\resources\\icons\\svg\\sheet.svg'), text='Import from csv file', parent= menu)
        action5.setToolTip('Opens file dialog to load list of students to database')
        action5.triggered.connect(self.load_from_csv)
        menu.addAction(action5)

        menu.addSeparator()

        menu.addAction(action_multi)

        menu.addSeparator()

        action0 = QAction(icon= QIcon(f'{state.application_path}\\resources\\icons\\svg\\drafting-compass.svg'), text='Set Edu-Item to group', parent= menu)

        action0.triggered.connect(lambda _, option='all': self.send_edu_items(option))
        menu.addAction(action0)

        action1 = QAction(icon= QIcon(f'{state.application_path}\\resources\\icons\\svg\\drafting-compass.svg'), text='Set Edu-Item to selected students',parent=menu)
                          
        action1.triggered.connect(lambda _, option='selected-list':self.send_edu_items(option))
        menu.addAction(action1)
        
        menu.addSeparator()
        
        action3 = QAction(icon= QIcon(f'{state.application_path}\\resources\\icons\\svg\\users-selected.svg'), text='group selected students', parent=menu)

        action3.triggered.connect(lambda _, model= group_model:self.show_group_dialog(model,'selected-list'))
        menu.addAction(action3)
        
        action2 = QAction(icon= QIcon(f'{state.application_path}\\resources\\icons\\svg\\users.svg'), text='group all',parent=menu)

        action2.triggered.connect(lambda _, model= group_model:self.show_group_dialog(model,'all'))
        menu.addAction(action2)
                
        action3 = QAction(icon= QIcon(f'{state.application_path}\\resources\\icons\\svg\\combine.svg'), text='manage groups',parent=menu)
        action3.triggered.connect(lambda _:self.show_manage_groups_dialog())
        menu.addAction(action3)
    
        return btn
  
    # Creates menu for each student
    def create_menu_btn(self, record,row):

        btn = QPushButton('')
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\menu.svg'))            
        btn.setProperty('class','grouped_mini')

        menu = QMenu(btn)
        btn.setMenu(menu)
        # Menu item to display student's learning progress
        # Opens new page to view learning profile(not personal profile)
        action3 = QAction(icon=QIcon(f'{state.application_path}\\resources\\icons\\svg\\chart-spline.svg'), text= 'Learning progress',parent=menu)
        action3.triggered.connect(lambda _, data=record: self.open_behaviour_list_page(data))
        menu.addAction(action3)

        action1 = QAction(icon=QIcon(f'{state.application_path}\\resources\\icons\\svg\\drafting-compass.svg'), text= 'Assign Edu-item',parent=menu)
        action1.triggered.connect(lambda _, stu = {'Id':record[0], "Name":f'{record[1]} {record[2]}'}:self.assign_edu_to_student(stu))
        menu.addAction(action1)
                

        action2 = QAction(icon=QIcon(f'{state.application_path}\\resources\\icons\\svg\\pencil.svg'),text='write behavioral observation', parent=menu)
        action2.triggered.connect(lambda _, data=record: self.open_behaviour_note_editor(data))
        menu.addAction(action2)

        action4 = QAction(icon=QIcon(f'{state.application_path}\\resources\\icons\\svg\\id-card.svg'),text='Personal data',parent=menu)
        action4.triggered.connect(lambda _, data=record: self.open_personal_info_dialog(data))
        menu.addAction(action4)
        
        menu.addSeparator()

        action5 = QAction(icon=QIcon(f'{state.application_path}\\resources\\icons\\svg\\x.svg'),text='Remove from group',parent=menu)
        action5.triggered.connect(lambda _, data=record: self.open_personal_info_dialog(data))
        menu.addAction(action5)

        action6 = QAction(icon=QIcon(f'{state.application_path}\\resources\\icons\\svg\\database-x.svg'), text= 'Remove from database',parent=menu)
        action6.triggered.connect(lambda _, student_id= record[0],r=row: self.delete_person(student_id,r))
        menu.addAction(action6)

        return btn
  
    def show_group_dialog(self, model:QStandardItemModel,option = 'selected-list'):

        if option == 'all':
            self.tableWidget.selectAll()
        elif not self.tableWidget.selectedIndexes(): 
            PopupNotifier.Notify(self,'','First select at least one student')
            return

        dlg = GroupSelectionDialog(model)
        
        if dlg.exec() == QDialog.Accepted:
            
            item = model.item(dlg.selected_group.row())
            group:viewModels.ClassroomGroupViewModel = item.data(Qt.ItemDataRole.UserRole)
            # The user has decided to group the selected list into this group.
            students = self.tableWidget.selectedIndexes()
            id_list = ''
            
            for student in students[:1]:
                id = self.data[student.row()][0] 
                id_list = f'{id_list},{id}'
            
            status, message = group.model.add_member(int(group.Id), id_list)
            
            if status: self.load_groups()
            
            PopupNotifier.Notify(self,'', message)
    
    def show_manage_groups_dialog(self):

        dlg = GroupsManagerDialog(TeacherAssistant.db_connection.cursor())
        dlg.setFixedSize(675,500)
        dlg.exec()
        
    def load_groups(self):
        
         #load groups
        self.db_cursor.execute('SELECT id, grade_, book_, title_, events_, members_, description_ FROM groups;')

        groups = self.db_cursor.fetchall()
            
        model = QStandardItemModel()
        item = QStandardItem('All')
        item.setData('All', Qt.ItemDataRole.UserRole)
        model.appendRow(item)

        for row , record in enumerate(groups): 

            item = QStandardItem()

            item.setData(record[3],Qt.ItemDataRole.DisplayRole)

            group = viewModels.ClassroomGroupViewModel()

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
    
    def load_students(self, sender:QComboBox):
        
        try:
            selected:viewModels.ClassroomGroupViewModel = sender.currentData(Qt.ItemDataRole.UserRole)
            
            if not selected: return
            if isinstance(selected, str):
                group_filter = '' # Where user selected 'All'
            else:
                group_filter =  f'WHERE t1.Id = ANY(string_to_array(\'{selected.members}\',\',\'))'
            
            cmd =  'SELECT t1.Id, t1.fname_, t1.lname_, t1.phone_, t1.address_, t1.photo_, t2.date_time_, '
            cmd += 't2.observed_behaviour_, t1.parent_name_, t1.parent_phone_, t1.additional_details_, '
            cmd += 't1.birth_date_, t1.gender_ FROM personal_info t1 '
            cmd += 'LEFT JOIN (SELECT t2.* FROM observed_behaviours t2 INNER JOIN ( '
            cmd += 'SELECT student_id, MAX(date_time_) AS max_created_at FROM observed_behaviours '
            cmd += 'GROUP BY student_id) last_records ON t2.student_id = last_records.student_id '
            cmd += 'AND t2.date_time_ = last_records.max_created_at) t2 ON t1.id = t2.student_id ' 
            cmd += f'{group_filter};'

            self.db_cursor.execute(cmd)

            self.data = self.db_cursor.fetchall()
            self.tableWidget.clear()
            # Columns:
            # 0- Photo, 
            # 1- Identification information, 
            # 2- address and cantact details, 
            # 3-The last notes of behavioral observations
            # Total: 4 columns
            # Set the scrollbar policy to auto-hide
            self.tableWidget.setHorizontalHeaderLabels(['PHOTO','INFO', 'ADDRESS','LAST NOTE'])
        
            self.tableWidget.setRowCount(len(self.data))

            # fetched columns:
            # 0- student Id,
            # 1- first name,
            # 2- last name,
            # 3- phone,
            # 4- address,
            # 5- photo,
            # 6- date of last modified behavioral observation,
            # 7- last observed behaviour,
            # 8- parent name,
            # 9- parent phone,
            # 10- additional details,
            # 11-birth date,
            # 12-gender
            # Total: 13 columns 
            for row, record in enumerate(self.data):
                # photo data has loaded in 5 column and must be displayed on first column
                photo_label = QLabel()
                photo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                photo_label.setText("No\nPhoto")
                photo_label.setStyleSheet('background-color: transparent;padding: 2px;text-align:center;margin:0px')
                # Set photo box dimensions to the formal size (35mm x 45mm ≈ 138x177 pixels at 96 DPI)
                photo_width  = 80    # Width of the photo box
                photo_height = 110  # Height of the photo box
                photo_label.setFixedSize(photo_width + 10, photo_height)
                photo_label.setProperty('class','caption')
                
                if record[5]: # If has a photo
                    pixmap = bytea_to_pixmap(record[5])
                    # Scale the photo to fill the entire photo box (ignore aspect ratio)
                    scaled_pixmap = pixmap.scaled(photo_label.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    photo_label.setPixmap(scaled_pixmap)
                    photo_label.setText("")

                
                self.tableWidget.setCellWidget(row,0,photo_label)

                # student Id + first name + last name
                # name_label = QLabel(str(record[0]) + '\n<b>' + str(record[1]) + ' ' + str(record[2]))
                name_label = QLabel(f"{record[0]}<br><b>{record[1]} {record[2]}</b>")
                name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                name_label.setFixedWidth(150)
                
                self.tableWidget.setCellWidget(row, 1, name_label)
                
                address_label = QLabel(str(record[4]) + '\nCall: ' + str(record[3]))
                address_label.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft)
                address_label.setFixedWidth(250)
                self.tableWidget.setCellWidget(row, 2, address_label)
                
                w = QWidget()
                notes_layout = QGridLayout(w)
                notes_layout.setContentsMargins(0,0,0,0)
                
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
                
                notes_layout.addWidget(btn,0,0,Qt.AlignmentFlag.AlignTop| (Qt.AlignmentFlag.AlignLeft if rtl else Qt.AlignmentFlag.AlignRight))
                
                self.tableWidget.setCellWidget(row, 3, w)

            self.tableWidget.resizeRowsToContents()
            self.tableWidget.itemSelectionChanged.connect(self.update_menu_visibility)
            self.tableWidget.horizontalHeader().adjustSize()
        
        except Exception as e: print(f"Database error: {e}")
  
    def update_menu_visibility(self):
        """ Show widgets only if their row is selected """
        for row in range(self.tableWidget.rowCount()):
            selected = any(item.row() == row for item in self.tableWidget.selectedItems())
            
            #self.tableWidget.item(row,4).setVisible(selected)
   
    def assign_edu_to_student(self,stu:dict):
        
        window = QApplication.activeWindow()
        window.add_page(EduResourcesViewer(window,[stu]))
    
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
        
        window.add_page(Pages.EduResourcesViewer(window,stu_list))


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
            
            self.tableWidget.removeRow(row_index)

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
        student_info_form = Widgets.ObservedBehaviourWidget(db_cursor= self.db_cursor, profile_data= data, parent= self.dialog)
        
        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(student_info_form)
    
        # Set the layout for the dialog
        self.dialog.setLayout(layout)
        self.dialog.exec()


    def find_in_list(self, search_input:QLineEdit):
        search_text = search_input.text().strip()
        if not search_text:
            PopupNotifier.Notify(self, "Message", "Enter a value to search.", 'bottom-right', delay=3000)
            return

        self.tableWidget.clearSelection()
        model = self.tableWidget.model()
        lower_search = search_text.lower()
        found = False
        
        for row in range(self.search_index,self.tableWidget.rowCount()):
            for col in range(self.tableWidget.columnCount()):
                # try QTableWidgetItem first
                item = self.tableWidget.item(row, col)
                
                cell_text = ""
                if item and item.text(): cell_text = item.text()
                else:
                    # then check for widget placed with setCellWidget(...)
                    widget = self.tableWidget.cellWidget(row, col)
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
                    self.tableWidget.selectRow(row)
                    index = model.index(row, col)
                    self.tableWidget.scrollTo(index, QAbstractItemView.PositionAtCenter)
                    self.tableWidget.setCurrentCell(row, col)

                    # Update search index for next search
                    self.search_index = row + 1
                    found = True

                    break
            
            if found: break

        if not found:
            PopupNotifier.Notify(self, "Message", f"No match for '{search_text}' in the list.", 'bottom-right', delay=1500)

        # Reset search index if it exceeds row count
        self.search_index %= self.tableWidget.rowCount()
        print(self.search_index, self.tableWidget.rowCount())
        
        search_input.setFocus(Qt.FocusReason.PopupFocusReason)


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
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\chevron-left.svg'))
        btn.setToolTip('Observed behaviours')
        btn.setProperty('class', 'grouped_mini')
        btn.clicked.connect(stacked_widget.go_back)
        header_layout.addWidget(btn, 5,0,alignment=Qt.AlignmentFlag.AlignLeft)

        btn  = QPushButton('')
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\chevron-right.svg'))
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
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\printer.svg'))
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
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\pencil-line.svg'))
        btn.setToolTip('Add new behaviour note')
        btn.setProperty('class','grouped_mini')
        btn.clicked.connect(lambda: self.add_behaviour_note(data=None))

        commands.addWidget(btn)

        btn = QPushButton('')
        btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\drafting-compass.svg'))
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

        student_id = QLabel(local_culture_digits(self.student[0],language=TeacherAssistant.Language))
        layout.addWidget(student_id,4,0, alignment=Qt.AlignmentFlag.AlignTop| Qt.AlignmentFlag.AlignHCenter)

        # Name of the student
        name = QLabel(f'{self.student[1]} {self.student[2]}')
        name.setProperty('class','subtitle')
        layout.addWidget(name, 0, 1,alignment=Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        # Phone number 
        phone_label = QLabel(local_culture_digits(self.student[3],language=TeacherAssistant.Language))
        layout.addWidget(phone_label, 1,1,alignment=Qt.AlignmentFlag.AlignLeft)

        # Parent/Guardian Name
        parent_name_input = QLabel(self.student[8])
        layout.addWidget(parent_name_input, 2, 1,alignment=Qt.AlignmentFlag.AlignLeft)
        # Parent/Guardian Phone
        parent_phone_label = QLabel(local_culture_digits(self.student[9],language=TeacherAssistant.Language))

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
        chart.setToolTip(ToolTips['Activity status'])
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
        window.add_page(EduResourcesViewer(window,[stu]))
        
    def edit_behaviour_note(self,record_id, behaviour_widget:QPlainTextEdit, analysis_widget:QPlainTextEdit):
        
        new_behaviour = behaviour_widget.toPlainText()
        new_analysis  = analysis_widget.toPlainText()

        if new_analysis or new_behaviour:
            try:
                query  = 'UPDATE observed_behaviours SET observed_behaviour_=%s, analysis_=%s WHERE Id=%s;'
                
                cursor = TeacherAssistant.db_connection.cursor()

                cursor.execute(query, (new_behaviour,new_analysis,record_id))
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
                cursor = TeacherAssistant.db_connection.cursor()
                cursor.execute(query, (now, self.student[0], behaviuor, analysis))
                id  = cursor.fetchone()

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
            
            cursor = TeacherAssistant.db_connection.cursor()
            cursor.execute(cmd)
            records = cursor.fetchall()
            
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

            cursor = TeacherAssistant.db_connection.cursor()
            cursor.execute(cmd,(self.student[0],))
            records = cursor.fetchall()

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

                item = Widgets.EduItemStudentWidget(record[0], record[8], answer, feedback, record[1],
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
                btn.setIcon(QIcon(f'{state.application_path}\\resources\\icons\\svg\\menu.svg'))
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
            cursor = TeacherAssistant.db_connection.cursor()
            cursor.execute(query, (self.student[0],record_Id))
            
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
        student_info_form = Widgets.ObservedBehaviourWidget(db_cursor=self.db_cursor,profile_data=data,parent=self.dialog)
        
        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(student_info_form)
    
        # Set the layout for the dialog
        self.dialog.setLayout(layout)
        self.dialog.exec()

