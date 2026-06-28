
from PySideAbdhUI.Widgets import Window, __version__ as ui_version
from PySideAbdhUI.Editor import __version__ as editor_version

# PySide6 modules
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFontDatabase, QPixmap
from PySide6.QtWidgets import (QApplication, QPushButton, QLabel, QComboBox, QRadioButton, QHBoxLayout, QVBoxLayout, QWidget)

# main application mudols

from ui.pages.settings_page import SettingsPage
from ui.pages.database_manager import DatabaseManagerPage
from ui.pages.resource_editor import EducationalResourceEditor
from ui.pages.resource_collection import EduResourcesView
from ui.pages.student_list import StudentListPage
from core.app_context import app_context


class MainWindow(Window.AbdhWindow):
    
    def __init__(self, window_title:str='', language_direction = Qt.LayoutDirection.LeftToRight, logo:QPixmap=None):

        super().__init__()
        
        self.setupUI(window_title=window_title, language_direction=language_direction, logo=logo)

    def setupUI(self, window_title:str='Main Window', language_direction= Qt.LayoutDirection.LeftToRight, logo:QPixmap=None):
        
        self.initUI(app_title= window_title, logo = logo, direction= language_direction)                           
    
        self.create_left_panel()

        self.create_settings_panel()        

    # Creates a vertical panel on the right edge of the mian window, This panel is used to settings porpose.
    # - 'settings_manager' object used to manage application settings, 
    # - This object has been initalized in the __init__.py
    # - 'settings.json' has been located in the APPDATA PATH for windows,
    #   'settings.json' stores settings for data connection and maintainance, fonts, 
    #   settings for UI like style sheet, language and language direction
    def create_settings_panel(self):

        self.add_right_panel_item(QLabel('LANGUAGE'))
        # Setup UI for the list of supported languages 
        combo1 = QComboBox()
        combo1.setPlaceholderText('-- Choose a language --')
        combo1.setToolTip(app_context.ToolTips['Language'])
        # Currently the language feature is not used in global scope
        # It is used in the future updates  
        combo1.addItems(['English','فارسی']) 
        self.add_right_panel_item(combo1)
        # Changes language in global scope
        combo1.currentIndexChanged.connect(lambda _: (setattr(app_context, 'Language', 
                                                    combo1.currentText() if combo1.currentText() =='English' else 'Persian'),
                                                    app_context.settings_manager.write({"language": combo1.currentText()})))
        # reads global font from settings.json
        lang = app_context.settings_manager.find_value('language')
        # checking validation
        if lang:
            combo1.setCurrentIndex(0 if lang == 'English' else 1)
        else:
            combo1.setCurrentIndex(0)
        
        self.right_panel_layout.addStretch(1)
        
        self.add_right_panel_item(QLabel(f'App Version: {app_context.app_version}'))
        self.add_right_panel_item(QLabel(f'UI Version: {ui_version}'))
        self.add_right_panel_item(QLabel(f'Editor Version: {editor_version}'))

        github_repo = 'https://github.com/abdhmohammadi/teacherassisstance'
        gitgub_page = 'https://abdhmohammadi.github.io'
        ui_repo     =  'https://github.com/abdhmohammadi/pysydeabdhui'

        github = QLabel(f'<a href="{gitgub_page}">Home page</a><br>' \
                        f'<a href="{github_repo}">GitHub</a><br>' \
                        f'<a href="{ui_repo}">GitHub for UI</a>', 
                        openExternalLinks=True, 
                        textInteractionFlags= Qt.TextInteractionFlag.LinksAccessibleByMouse)
        
        github.setProperty('class','hyperlink')

        self.add_right_panel_item(github)


    # defined to create menu-like items placed in the left panel
    def create_panel_button(self, icon_path=None, text='',checkable=True, checked = False, class_name ='')->QPushButton:
        
        item = QPushButton(text.upper())
        
        if icon_path: item.setIcon(QIcon(icon_path))
        
        item.setCheckable(checkable)
        item.setChecked(checked)
        item.setProperty('class',class_name)

        self.add_left_panel_item(item)

        return item 
        
    def create_left_panel(self):
        # Init left pane
        
        item = self.create_panel_button(':/icons/book-text.svg','   Notebook',True, True,'MenuItem')
        item.setEnabled(False)
        #item.clicked.connect(lambda _, sender=item:self.load_students_page(sender))

        item = self.create_panel_button(':/icons/graduation-cap.svg','   Students',True, True,'MenuItem')
        item.clicked.connect(lambda _, sender=item:self.load_students_page(sender))

        item = self.create_panel_button(':/icons/library.svg','   Resource collection',True, False,'MenuItem')
        item.clicked.connect(lambda _, sender= item: self.load_EduResourcesViewer(sender))
        
        item = self.create_panel_button(':/icons/notebook-pen.svg','   Resource Editor',True, False,'MenuItem')
        item.clicked.connect(lambda _, sender= item: self.load_EduResourceEditor(sender))

        item = self.create_panel_button(':/icons/database-zap.svg','   Database maintenance',True, False,'MenuItem')
        item.clicked.connect(lambda _, sender= item: self.load_db_maintenance_page(sender))

        item = self.create_panel_button(':/icons/settings.svg','   Settings',True, False,'MenuItem')
        item.clicked.connect(lambda _, sender= item: self.load_SettingsPage(sender))

        
    # It tries to visually display the active/deactive status of each item. 
    def uncheck_items(self,layout:QVBoxLayout):
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if type(item.widget()) is QPushButton:
                item.widget().setChecked(False)

    def toggle_direction(self, direction:Qt.LayoutDirection): self.set_direction(direction)
        
    def load_EduResourceEditor(self, sender:QPushButton): 
        
        self.uncheck_items(self.left_panel_layout)
        self.add_page(EducationalResourceEditor())
        sender.setChecked(True)

    def load_students_page(self, sender:QPushButton): 
        
        self.uncheck_items(self.left_panel_layout) 

        self.add_page(StudentListPage(parent=self))
        
        if sender: sender.setChecked(True)

    def load_db_maintenance_page(self, sender:QPushButton):
        
        self.uncheck_items(self.left_panel_layout)

        connection_settings :dict = app_context.settings_manager.find_value('connection')

        if connection_settings:
            host = connection_settings.get('host','localhost')
            port = connection_settings.get('port','5432')
            database = connection_settings.get('database','')
            user = connection_settings.get('user','postgres')
            password = connection_settings.get('password','')

        postgresql_path = app_context.settings_manager.find_value('postgreSQL tools path')
        backup_dir =  app_context.settings_manager.find_value('backup to')
        restore_dir = app_context.settings_manager.find_value('restore from')
        #style_path = app_context.settings_manager.find_value('style sheet')        

        page = DatabaseManagerPage(db_name=database, host= host, port= port, user= user, password=password,
                                         postgresql_tools_path= postgresql_path, backup_path=backup_dir, 
                                         restore_path= restore_dir,style_path=self.theme['path'],
                                         settings_path= app_context.settings_manager.file_path)
        
        self.add_page(page)

        sender.setChecked(True)

    def load_SettingsPage(self, sender:QPushButton):

        self.uncheck_items(self.left_panel_layout)
        settings_page = SettingsPage()         
        self.add_page(settings_page)

        if sender: sender.setChecked(True)

    def load_EduResourcesViewer(self, sender:QPushButton):
        
        self.uncheck_items(self.left_panel_layout)
        
        viewer = EduResourcesView(target_students=[])
        
        self.add_page(viewer)
        
        sender.setChecked(True)
