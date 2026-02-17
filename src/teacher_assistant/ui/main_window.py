
from PySideAbdhUI import Window

# PySide6 modules
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFontDatabase, QPixmap
from PySide6.QtWidgets import (QApplication, QPushButton, QLabel, QComboBox, QRadioButton, QHBoxLayout, QVBoxLayout, QWidget)

# main application mudols

from ui.pages.settings_page import SettingsPage
from ui.pages.database_manager import DatabaseManagerPage
from ui.pages.edu_resource_editor import EducationalResourceEditor
from ui.pages.edu_resource_view import EduResourcesView
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

    def on_font_changed(self,size_combo:QComboBox,font_combo:QComboBox):
        # Get the text of the selected item 
        selected_font = font_combo.itemText(font_combo.currentIndex())
        # Font-size options: [tiny, small, medium, large]
        #                    [8,    10,    12,     14   ]
        sz = 8 + 2*size_combo.currentIndex()

        app_context.theme_manager.add_property_to_widget('QWidget','font-family',selected_font)
        # to be applicable for QWidgets we need to store font size in the pt unit. 
        app_context.theme_manager.add_property_to_widget('QWidget','font-size',str(sz) + "pt")
        
        app_context.theme_manager.apply_theme(QApplication.instance(), app_context.theme_manager.get_current_theme_name())

        settings_list = [('family',selected_font),('size',sz)]
        settings = {"font": dict(settings_list)}
        app_context.settings_manager.write(settings)

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
        
        self.add_right_panel_item(QLabel('FONT'))
        # Global Font in the application domain 
        fonts = QFontDatabase.families()

        combo2 = QComboBox()
        combo2.setPlaceholderText("Select a font")
        combo2.addItems(fonts)
        current_font = app_context.settings_manager.find_value('font')
        if current_font:
            combo2.setCurrentText(dict(current_font)['family'])
        else:
            combo2.setCurrentText('Times New Roman')

        self.add_right_panel_item(combo2)

        combo3 = QComboBox()
        combo3.setPlaceholderText("Select font size")
        combo3.addItems(['Tiny','Small', 'Medium', 'Large'])
        current_font = app_context.settings_manager.find_value('font')
        if current_font:
            combo2.setCurrentText(dict(current_font)['family'])
        else:
            combo2.setCurrentText('Times New Roman')

        self.add_right_panel_item(combo3)
        # Changes the application font, this change affects all objects in the application
        combo2.currentIndexChanged.connect(lambda _, size_combo= combo3,font_combo=combo2:self.on_font_changed(size_combo,font_combo))
        combo3.currentIndexChanged.connect(lambda _, size_combo= combo3,font_combo=combo2:self.on_font_changed(size_combo,font_combo))
        # Page direction options: It is provided Left-to-Right
        # The direction is applied on the mantent of main frame, and titlebar,
        # left panel and right panel are not affected currently.
        hlayout = QHBoxLayout()
        direction = app_context.settings_manager.find_value('direction')
        radio1 = QRadioButton('Right to Left')
        radio1.clicked.connect(lambda _, d= Qt.LayoutDirection.RightToLeft: self.toggle_direction(d))
        radio1.setChecked(direction == 'RightToLeft')
        hlayout.addWidget(radio1)

        radio2 = QRadioButton('Left to Right')
        radio2.setChecked(direction == 'LeftToRight')
        radio2.clicked.connect(lambda _, d= Qt.LayoutDirection.LeftToRight: self.toggle_direction(d))

        radio2.setChecked(direction == 'LeftToRight')

        hlayout.addWidget(radio2)
        self.set_direction(Qt.LayoutDirection.RightToLeft if direction == 'RightToLeft' else Qt.LayoutDirection.LeftToRight)
        w = QWidget()
        w.setToolTip(app_context.ToolTips['Direction'])
        w.setLayout(hlayout)
        self.add_right_panel_item(w)

        # There are a number of custom styles can be applied to the UI.
        # Changing it will affects all UI objects of the application.
        self.add_right_panel_item(QLabel('THEME'))
        theme_selector = QComboBox()
        theme_selector.addItems(app_context.theme_manager.get_all_themes())
        theme_selector.setCurrentText(app_context.theme_manager.get_current_theme_name())
        theme_selector.currentTextChanged.connect(lambda _, sender= theme_selector:self.on_theme_switch(sender=sender))
        self.add_right_panel_item(theme_selector)
        

        github = QLabel('\n https://github.com/abdhmohammadi/')
        self.add_right_panel_item(github)
        github.setProperty('class','hyperlink')          

    def on_theme_switch(self,sender:QComboBox):

        theme_name = sender.currentText()

        app_context.theme_manager.apply_theme(QApplication.instance(),theme_name)
        # Apply theme immediately

    # defined to create menu-like items placed in the left panel
    def create_panel_button(self, icon_path=None,text='',checkable=True, checked = False, class_name ='')->QPushButton:
        
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

    def toggle_direction(self, direction:Qt.LayoutDirection):
        
        self.set_direction(direction)
        
        #settings_manager.write({'direction': 'RightToLeft' if direction == Qt.LayoutDirection.RightToLeft else 'LeftToRight'})

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
                                         restore_path= restore_dir, style_path= app_context.theme_manager.get_current_theme_name(),
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
