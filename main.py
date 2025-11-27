
# HOW TO USE THIS PROJECT:
#     ACTIVATE ENVIRONMENT: Terminal> env\Scripts\activate
#     RUN THE APP         : USE Run option from the vscode menu or run from Terminal-> python main.py
#   
# HOW TO BUILD THIS PROJECT:           
# INSTALL PySideAbdhUI:
# OPTION 1                        : pip install F:\Projects\Python\PySideAbdhUI\dist\PySideAbdhUI-1.0.4-py3-none-any.whl
# EDITABLE INSTALL(FOR DEVELOPERS): pip install -e F:\Projects\Python\PySideAbdhUI
# INSTALL FROM GIT                : pip install git+https://github.com/abdhmohammadi/PySideAbdhUI.git
# 
#
# HOW TO INSTALL THE APP:
# 1. Create executable package for Windows OS:
#    1. PyInstaller:
#       pyinstaller  \TeacherAssistant.spec,
#       if not works--> C:\Users\AbdhM\AppData\Roaming\Python\Python314\Scripts\pyinstaller TeacherAssistant.spec

# 2. Use InnoSetup tool to create windows installer.
#
# ICONS: All icons has been downloaded from https://lucide.dev/icons/categories (and modified if needed).

from TeacherAssistant import state
from TeacherAssistant.cli import CLI
# Setup the app directories
state.setup_app_directories()

cli = CLI() 

cli.Run()
