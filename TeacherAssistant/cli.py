
import sys

from PySideAbdhUI import Window
from PySideAbdhUI.Notify import PopupNotifier
# Local moduls in main.py directory must be imported
import TeacherAssistant
from TeacherAssistant import state, ToolTips, settings_manager, theme_manager
from TeacherAssistant.views import Pages, Widgets

# PySide6 modules
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFontDatabase
from PySide6.QtWidgets import (QApplication, QPushButton, QLabel, QComboBox, QRadioButton, QHBoxLayout, QVBoxLayout, QWidget)

class CLI:
    def __init__(self):

        self.app = QApplication(sys.argv)

        self.window = Window.AbdhWindow()
 
    def on_font_changed(self,size_combo:QComboBox,font_combo:QComboBox):
        # Get the text of the selected item 
        selected_font = font_combo.itemText(font_combo.currentIndex())
        sz = 12 + 2*size_combo.currentIndex()

        theme_manager.add_property_to_widget('QWidget','font-family',selected_font)
        theme_manager.add_property_to_widget('QWidget','font-size',sz)
        
        theme_manager.apply_theme(QApplication.instance(), theme_manager.get_current_theme_name())

        settings_list = [('family',selected_font),('size',sz)]
        settings = {"font": dict(settings_list)}
        settings_manager.write(settings)

    # Creates a vertical panel on the right edge of the mian window
    # This panel is used to settings porpose
    def create_settings_pane(self):

        self.window.add_right_panel_item(QLabel('LANGUAGE'))
        combo1 = QComboBox()
        combo1.setPlaceholderText('-- Choose language --')
        combo1.setToolTip(ToolTips['Language'])
        # Currently the language feature is not used in global scope
        # It is used in the future updates  
        combo1.addItems(['English','فارسی']) 
        self.window.add_right_panel_item(combo1)
        # Changes language in global scope
        combo1.currentIndexChanged.connect(lambda _: (setattr(TeacherAssistant, 'Language', 
                                                     combo1.currentText() if combo1.currentText() =='English' else 'Persian'),
                                                        settings_manager.write({"language": combo1.currentText()})))
        # reads global font from settings.json
        lang = settings_manager.find_value('language')
        # checking validation
        if lang:
            combo1.setCurrentIndex(0 if lang == 'English' else 1)
        else:
            combo1.setCurrentIndex(0)
        
        self.window.add_right_panel_item(QLabel('FONT'))
        # Global Font in the application domain 
        fonts = QFontDatabase.families()
               

        combo2 = QComboBox()
        combo2.setPlaceholderText("Select font")
        combo2.addItems(fonts)
        current_font = settings_manager.find_value('font')
        if current_font:
            combo2.setCurrentText(dict(current_font)['family'])
        else:
            combo2.setCurrentText('Times New Roman')

        self.window.add_right_panel_item(combo2)

        combo3 = QComboBox()
        combo3.setPlaceholderText("Select font size")
        combo3.addItems(['Small', 'Medium', 'Large'])
        #current_font = settings_manager.find_value('font')
        #if current_font:
        #    combo2.setCurrentText(dict(current_font)['family'])
        #else:
        #    combo2.setCurrentText('Times New Roman')

        self.window.add_right_panel_item(combo3)
        # Changes the application font, this change affects all objects in the application
        combo2.currentIndexChanged.connect(lambda _, size_combo= combo3,font_combo=combo2:self.on_font_changed(size_combo,font_combo))
        combo3.currentIndexChanged.connect(lambda _, size_combo= combo3,font_combo=combo2:self.on_font_changed(size_combo,font_combo))
        # Page direction options: It is provided Left-to-Right
        # The direction is applied on the mantent of main frame, and titlebar,
        # left panel and right panel are not affected currently.
        hlayout = QHBoxLayout()
        direction = settings_manager.find_value('direction')
        radio1 = QRadioButton('Right to Left')
        radio1.clicked.connect(lambda _, d= Qt.LayoutDirection.RightToLeft: self.toggle_direction(d))
        radio1.setChecked(direction == 'RightToLeft')
        hlayout.addWidget(radio1)

        radio2 = QRadioButton('Left to Right')
        radio2.setChecked(direction == 'LeftToRight')
        radio2.clicked.connect(lambda _, d= Qt.LayoutDirection.LeftToRight: self.toggle_direction(d))

        radio2.setChecked(direction == 'LeftToRight')

        hlayout.addWidget(radio2)
        self.window.set_direction(Qt.LayoutDirection.RightToLeft if direction == 'RightToLeft' else Qt.LayoutDirection.LeftToRight)
        w = QWidget()
        w.setToolTip(ToolTips['Direction'])
        w.setLayout(hlayout)
        self.window.add_right_panel_item(w)

        # There are a number of custom styles can be applied to the UI.
        # Changing it will affects all UI objects of the application.
        self.window.add_right_panel_item(QLabel('THEME'))
        theme_selector = QComboBox()
        theme_selector.addItems(theme_manager.get_all_themes())
        theme_selector.setCurrentText(theme_manager.get_current_theme_name())
        theme_selector.currentTextChanged.connect(lambda _, sender= theme_selector:self.on_theme_switch(sender=sender))
        self.window.add_right_panel_item(theme_selector)
        

        github = QLabel('\n https://github.com/abdhmohammadi/')
        self.window.add_right_panel_item(github)
        github.setProperty('class','hyperlink')          

    def on_theme_switch(self,sender:QComboBox):

        theme_name = sender.currentText()

        theme_manager.apply_theme(QApplication.instance(),theme_name)
            # Apply theme immediately

    # defined to create menu-like items placed in the left panel
    def create_panel_button(self, icon_path=None,text='',checkable=True, checked = False, class_name ='')->QPushButton:
        
        item = QPushButton(text.upper())
        
        if icon_path: item.setIcon(QIcon(icon_path))
        
        item.setCheckable(checkable)
        item.setChecked(checked)
        item.setProperty('class',class_name)

        self.window.add_left_panel_item(item)

        return item 
        
    def create_left_pane(self):
        # Init left pane
        root = f'{state.application_path}\\resources\\icons\\svg'
        
        item = self.create_panel_button(f'{root}\\graduation-cap.svg','   Students',True, True,'MenuItem')
        item.clicked.connect(lambda _, sender=item:self.load_students_page(sender))

        item = self.create_panel_button(f'{root}\\library.svg','   Resource collection',True, False,'MenuItem')
        item.clicked.connect(lambda _, sender= item: self.load_EduResourcesViewer(sender))
        
        item = self.create_panel_button(f'{root}\\notebook-pen.svg','   Resource Editor',True, False,'MenuItem')
        item.clicked.connect(lambda _, sender= item: self.load_EduResourceEditor(sender))

        item = self.create_panel_button(f'{root}\\database-zap.svg','   Database maintenance',True, False,'MenuItem')
        item.clicked.connect(lambda _, sender= item: self.load_db_maintenance_page(sender))
        
    # It tries to visually display the active/deactive status of each item. 
    def uncheck_items(self,layout:QVBoxLayout):
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if type(item.widget()) is QPushButton:
                item.widget().setChecked(False)

    def toggle_direction(self, direction:Qt.LayoutDirection):
        
        self.window.set_direction(direction)
        
        settings_manager.write({'direction': 'RightToLeft' if direction == Qt.LayoutDirection.RightToLeft else 'LeftToRight'})

    def load_EduResourceEditor(self, sender:QPushButton): 
        
        self.uncheck_items(self.window.left_panel_layout)
        self.window.add_page(Pages.EducationalResourceEditor())
        sender.setChecked(True)

    def load_students_page(self, sender:QPushButton): 
        
        self.uncheck_items(self.window.left_panel_layout)        
        self.window.add_page(Pages.StudentListPage(parent=self.window))
        
        if sender: sender.setChecked(True)

    def load_db_maintenance_page(self, sender:QPushButton):
        
        self.uncheck_items(self.window.left_panel_layout)

        connection_settings :dict = settings_manager.find_value('connection')

        if connection_settings:
            host = connection_settings.get('host','localhost')
            port = connection_settings.get('port','5432')
            database = connection_settings.get('database','')
            user = connection_settings.get('user','postgres')
            password = connection_settings.get('password','')

        postgresql_path = settings_manager.find_value('postgreSQL tools path')
        backup_dir =  settings_manager.find_value('backup to')
        restore_dir = settings_manager.find_value('restore from')
        style_path = settings_manager.find_value('style sheet')        

        page = Pages.DatabaseManagerPage(db_name=database, host= host, port= port, user= user, password=password,
                                         postgresql_tools_path= postgresql_path, backup_path=backup_dir, 
                                         restore_path= restore_dir, style_path= theme_manager.get_current_theme_name(),
                                         settings_path= settings_manager.file_path)

        self.window.add_page(page)

        sender.setChecked(True)


    def load_EduResourcesViewer(self, sender:QPushButton):
        
        self.uncheck_items(self.window.left_panel_layout)
        
        viewer = Pages.EduResourcesViewer(target_students=[])
        
        self.window.add_page(viewer)
        
        sender.setChecked(True)


    def Run(self):

        # reads global font from settings.json
        #font = settings_manager.find_value('font')
        # checking validation
        #if font:
        #    font_family = font['family']
        #    size = int(font['size'])
        #else:
        #    font_family = 'Times New Roman'
        #    size = 12

        # Update style sheet with font values, then is appled on the application
        #theme_manager.add_property_to_widget('QWidget','font-family',font_family)
        #theme_manager.add_property_to_widget('QWidget','font-size',size)
                            
        # Apply stylesheet on the application
        theme_manager.load()
        theme_manager.apply_theme(QApplication.instance(),theme_manager.get_current_theme_name())
        
        connection_settings = settings_manager.find_value('connection')
    
        host = 'localhost' if connection_settings is None else connection_settings["host"]
        port = '5432'      if connection_settings is None else connection_settings["port"]
        database = ''      if connection_settings is None else connection_settings["database"]
        user = 'postgres'  if connection_settings is None else connection_settings["user"]
        password = ''      if connection_settings is None else connection_settings["password"]

        # We can load the connection dialog before we create the main window,
        # but if we done it, selected theme is not applyed.
        connection_dialog = Widgets.PostgreSqlConnectionWidget(host,port,database,user,password)

        status, settings = connection_dialog.show_dialog()

        if not settings or not status: sys.exit('Unsuccess connection or user ignored')
    
        # Update settings.json by new connection values
        settings_manager.write(settings)  

        # calculates display settings dependent on logical dots per inch(DPI)
        state.display_calulation(QApplication.primaryScreen().logicalDotsPerInch())

        # Our custom ICON is available in application_path + "/resources/icons/
        #self.app.setWindowIcon(QIcon(icon_path))
        # Create the main customized UI window
        #self.window = Window.AbdhWindow()

        self.window.initUI(app_title= f'TEACHER ASSISTANT | v{TeacherAssistant.version}', 
                           title_logo_path= state.application_path + "/resources/icons/png/app-icon.png",
                           direction= Qt.LayoutDirection.LeftToRight)
    
        self.create_left_pane()
        self.create_settings_pane()
        self.load_students_page(None)

        self.window.show()
        
        PopupNotifier.Notify(self.window,"Wellcome!", "📚 Teacher Assistant app is in your service.", 'bottom-right')#, 
                            # delay=5000, background_color='#353030',border_color="#2E7D32")
    
        self.app.exec()
    
        if TeacherAssistant.db_connection:
            TeacherAssistant.db_connection.cursor().close()
            TeacherAssistant.db_connection.close()

        sys.exit(0)
