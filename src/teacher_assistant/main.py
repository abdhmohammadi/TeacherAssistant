
# HOW TO USE THIS PROJECT:
#     ACTIVATE ENVIRONMENT: Terminal> env\Scripts\activate
#     RUN THE APP         : USE Run option from the vscode menu or run from Terminal-> python main.py
#   
# HOW TO BUILD THIS PROJECT:           
# INSTALL PySideAbdhUI:
# OPTION 1 : pip install F:\Projects\Python\PySideAbdhUI\dist\PySideAbdhUI-1.0.7-py3-none-any.whl
# OPTION 2 : F:/Projects/Python/Teaching-assistant-project/TeacherAssistant/env/Scripts/python.exe' -m pip install -e F:\Projects\Python\PySideAbdhUI
# OPTION 3 (EDITABLE INSTALL FOR DEVELOPERS): 
#            pip install -e F:\Projects\Python\PySideAbdhUI

# OPTION 4 (INSTALL FROM GIT): pip install git+https://github.com/abdhmohammadi/PySideAbdhUI.git
# OPTION 5 :
# cd 'F:\Projects\Python\Teaching-assistant-project\TeacherAssistant'; .\env\Scripts\python.exe -m pip install 'F:\Projects\Python\PySideAbdhUI\dist\PySideAbdhUI-1.0.8-py3-none-any.whl'
#
# HOW TO INSTALL THE APP:
# 1. Create executable package for Windows OS:
#    1. PyInstaller:
#       pyinstaller .\scripts\TeacherAssistant.spec
#       if not works --> C:\Users\AbdhM\AppData\Roaming\Python\Python314\Scripts\pyinstaller .\scripts\TeacherAssistant.spec

# 2. Use InnoSetup tool to create windows installer.
#
# ICONS: All icons has been downloaded from https://lucide.dev/icons/categories (and modified if needed).
#       and placed in the src/teacher_assistant/resources. to portable usage the icons, we created resources.qrc
#       from png and svg files. the scripts/build_qrc.py just generates resources.qrc in resources folder. we  
#       need to compile the resources.qrc to generate embeded icon files. any changes in the resources.qrc needs  
#       to recompile this file. the scripts/compile_qrc.py does this task and created resources_rc.py.
#       We imported resources_rc in the src/teacher_assistant/core/app_context.py to use icons in the app scope.
#    
 
import os
import sys
 
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

# Add the 'src' directory to the Python path to allow for absolute imports
# This is crucial for making the project runnable from any location
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from core.app_context import app_context

from ui.main_window import MainWindow
from ui.widgets import connection_form  # a dialog to validate user and database connection

from version import __version__ as version


if __name__ == "__main__":

    app = QApplication(sys.argv) 

    # Setup the app directories
    app_context.setup_app_directories()
    # computes dpi to display edu-item size
    app_context.display_calulation(QApplication.primaryScreen().logicalDotsPerInch())

    app_context.theme_manager.load()
    app_context.theme_manager.apply_theme(QApplication.instance(), app_context.theme_manager.get_current_theme_name())
    
    main_window = MainWindow(window_title=f'TEACHER ASSISTANT | v{version}', logo=QPixmap(':/icons/app-icon.png'))
    
    main_window.show()

    connection_dialog = connection_form.PostgreSqlConnectionWidget(main_window)

    status, settings = connection_dialog.show_dialog()

    if status: main_window.load_students_page(None)
    
    sys.exit(app.exec())

# SETTINGS:
# - setings.json is placed in: C:\Users\[user]\AppData\Local\Abdh\TeacherAssistant
# - settings included:
# - UI settings e.g stylesheet(theme) , language, language direction, font settings,
# - database settings e.g connection_settings, backup settings
#
# - theme related files is placed in: C:\Users\[user]\AppData\Local\Abdh\TeacherAssistant
