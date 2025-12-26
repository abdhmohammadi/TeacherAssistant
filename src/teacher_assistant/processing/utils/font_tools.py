from PySide6.QtGui import QFontDatabase#, QFont
from PySide6.QtGui import QFont
#os.environ["QT_FONT_ENGINE"] = "gdi" Use GDI instead of DirectWrite
#icon_font_family = QFont('Segoe Fluent Icons', 14, QFont.Weight.Normal)
def get_fonts(): return QFontDatabase.families()

def create_font(path):

    font_id = QFontDatabase.addApplicationFont(path)
    if font_id == -1:
        print("Failed to load the font file.")

    # Get the font family name
    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

    # Create a QFont object
    return QFont(font_family,12)  # Font family and size


