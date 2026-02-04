import enum
import os
import sys
from utils.Json_manager import JSONManager
from core.theme_manager import ThemeManager
from data.database import psycopg2_database

# IMPORTANT: Registers the resources automatically
# this module embeds icon resources to the app without includeing main files to
# the installable package 
from resources import resources_rc

class AppContext:

    def __init__(self):

        self.EDU_ITEM_PIXELS = 0.0
        self.A4_PIXELS = 0.0
        self.EDU_CONTENT_WIDTH = 6.19 # inches
        self.PDI = 96
        self.Language = 'English'
        self.__database__  = psycopg2_database()
        self.resource_path =''
        self.settings_manager = JSONManager()
        self.template_config = JSONManager()
        self.theme_manager = ThemeManager()
    
    @property 
    def database(self): return self.__database__

    @property
    def FileTypes(self): return FileTypes
    @property
    def SupportedFileTypes(self): return SupportedFileTypes

    @property
    def ToolTips(self): return ToolTips

    #@property
    #def svg_path(self): return f'{self.icon_path}svg'

    #@property
    #def png_path(self): return f'{self.icon_path}png'
    # Setup the appdata path
    # Run this command to create pyInstaller exe
    def setup_app_directories(self):
        # Get the appdata path
        appdata_dir = os.getenv('LOCALAPPDATA')
        appdata_dir = os.path.join(appdata_dir, 'Abdh\\TeacherAssistant')
        # Create the directory if it doesn't exist
        os.makedirs(appdata_dir, exist_ok=True)
        # Set the appdata path
        self.appdata_path = appdata_dir

        # Get the app path
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundled executable (e.g., PyInstaller)
            app_path = os.path.dirname(sys.executable) + '\\TeacherAssistant'
        else:
            # If the application is run as a script(main.py)
            app_path = os.path.dirname(os.path.abspath(__file__))
        
        # Set the application path
        self.application_path = app_path

        # Set the settings manager path
        self.settings_manager.set_path(self.appdata_path +'\\settings.json')

        self.resource_path = app_path.replace('core','') +'resources' 
        # Set the config manager path
        tmp_file_path = self.resource_path +'\\templates\\01-Quiz-config.json'
        self.template_config.set_path(tmp_file_path)
    
    def display_calulation(self, dpi):
        
        self.DPI = dpi
        
        self.EDU_ITEM_PIXELS =  dpi * self.___EDU_ITEM_INCHES()

        self.A4_PIXELS = dpi* self.___A4_INCHES()
     
    
    def ___EDU_ITEM_INCHES(self): return 6.19


    def ___A4_INCHES(self): return 8.27


app_context = AppContext()


class DocumentType(enum.Flag):

    PlainText = ...  # 0x0 
    RTF       = ...  # 0x1
    LaTeX     = ...  # 0x2
    Html      = ...  # 0x3
    Image     = ...  # 0x4

# Supported files to upload as a learning items
class SupportedFileTypes(enum.Flag):
    IMAGE = 'Image'
    PDF   = 'PDF'
    RTF   = 'RTF'
    TEXT  = 'Text'
    HTML  = 'HTML'
    LaTeX = 'LaTeX'
    DOCX  = 'Word'

# File types for RESOURCE EDITOR 
FileTypes = {SupportedFileTypes.IMAGE:'Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);',
             SupportedFileTypes.PDF  :'PDFs (*.PDF)',
             SupportedFileTypes.DOCX :'Word documents (*.docx);',
             SupportedFileTypes.RTF  :'Rich text format(*.rtf)',
             SupportedFileTypes.TEXT :'Plain texts(*.txt);',
             SupportedFileTypes.HTML :'HTML(*.html);',
             SupportedFileTypes.LaTeX:'LaTeX(*.tex);'}


ToolTips = {
    'Language':'Currently this feature is not used much,\n it will be used in future updates.',
    'StyleSheet':'There are a number of custom styles can be applied to the UI.\nChanging it will affects all UI objects of the application.',
    'Direction':'Page direction options: It is provided Left-to-Right and Right-to-Left.\nThe direction is applied on the content of main frame,\nTitlebar, left panel and right panel are not affected currently.',
    'LaTeX Settings':'Will be supported in future updates!',
    'Back':'Navigate to the previous record.',
    'Next':'Navigate to the next record.',
    'Generate LaTeX':'Generate basic LaTeX code for new content.',
    'Generate HTML':'Generate basic HTML code for new content.',
    'Insert Image':'Insert an image into the current content.',
    'Insert Image from screen':'Insert an image using the screen capture tool.',
    'Upload File':'Upload a file to the current content.',
    'Find in database':'Find content in the database.',
    'New Content':'Clear the current content and start a new content.',
    'Set bookmark':'Bookmark to emphasize and review before distribution',
    'Marked Item':'Bookmarked item: this item need to review before distribution',
    'Score change warning':'It is better not to change the score after recording. Changing the value of the score may cause inconsistency in data analysis.',
    'Activity status':'''Status of activities from all requested activities:\n
                         Replyed: Activities that have been replied to within the specified time.\n
                         Remained: Activities that still have time to be delivered.\n
                         Time-passed: Activities that have not been delivered on time.'''
}

