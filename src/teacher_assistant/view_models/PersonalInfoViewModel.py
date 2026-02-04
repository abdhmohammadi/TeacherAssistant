from PySide6.QtCore import Signal, Property
from PySide6.QtWidgets import QApplication
from typing import overload, Optional

from PySideAbdhUI.Notify import NotifyPropertyChanged, PopupNotifier

from services.personal_info_service import PersonalInfoService
#from services.personal_info_service import PersonalInfoService

# ViewModel (Intermediary between View and Model)
class PersonalInfoViewModel(NotifyPropertyChanged):
    
    @overload
    def __init__(self)-> None:...
        # Initialization for INSERT mode.
        #pass

    @overload
    def __init__(self, arg__1:PersonalInfoService) -> None:...
        # Initialization for UPDATE mode.
        #pass
      
    def __init__(self, arg__1: Optional[PersonalInfoService] = None) -> None:
        
        super().__init__()

        if arg__1 is None:
            # INSERT mode
            self.old_id = None
            self.__service = PersonalInfoService()#TeacherAssistant.db_connection.cursor())
        else:
            # UPDATE mode
            self.old_id = arg__1[0]
            self.__service = arg__1  # Use the provided model instance

        # Initialize properties
        self._properties['id','fname','lname','phone','address','parent_name','parent_phone',
                         'additional_details','photo','gender','birth_date'] = '','','','','','','','',bytes(),'','' 

    def save(self):  
        
        bool_, result = self.__service.save(self.id, self.fname, self.lname, self.birth_date, self.gender, self.phone, self.address,
                                          self.parent_name, self.parent_phone, self.additional_details, self.photo, self.old_id)

        if bool_: msg = 'Data saved successfully'
        else:     msg = f'Database Error: {result}.'

        PopupNotifier.Notify(QApplication.activeWindow(),"Message",msg)

    old_id :Optional[str] = None

    # Signals for notifying changes
    id_changed = Signal(str)
    fname_changed = Signal(str)
    lname_changed = Signal(str)
    photo_changed = Signal(bytes)
    phone_changed = Signal(str)
    address_changed = Signal(str)
    parent_name_changed = Signal(str)
    parent_phone_changed = Signal(str)
    additional_details_changed = Signal(str)
    birth_date_changed = Signal(str)
    gender_changed = Signal(str)
    
    # Define a property for 'id'
    id = Property(
        str,
        lambda self: self._get_property("id"),
        lambda self, value: self._set_property("id", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    # Define a property for 'id'
    fname = Property(
        str,
        lambda self: self._get_property("fname"),
        lambda self, value: self._set_property("fname", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    # Define a property for 'id'
    lname = Property(
        str,
        lambda self: self._get_property("lname"),
        lambda self, value: self._set_property("lname", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )   
    # Define a property for 'id'
    phone = Property(
        str,
        lambda self: self._get_property("phone"),
        lambda self, value: self._set_property("phone", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    address = Property(
        str,
        lambda self: self._get_property("address"),
        lambda self, value: self._set_property("address", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    parent_name = Property(
        str,
        lambda self: self._get_property("parent_name"),
        lambda self, value: self._set_property("parent_name", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    parent_phone = Property(
        str,
        lambda self: self._get_property("parent_phone"),
        lambda self, value: self._set_property("parent_phone", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    additional_details = Property(
        str,
        lambda self: self._get_property("additional_details"),
        lambda self, value: self._set_property("additional_details", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    
    # Define a property for 'id'
    photo = Property(
        bytes,
        lambda self: self._get_property("photo"),
        lambda self, value: self._set_property("photo", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    gender = Property(
        str,
        lambda self: self._get_property("gender"),
        lambda self, value: self._set_property("gender", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    birth_date = Property(
        str,
        lambda self: self._get_property("birth_date"),
        lambda self, value: self._set_property("birth_date", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    

    