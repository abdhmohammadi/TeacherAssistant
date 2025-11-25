
from PySide6.QtCore import Property, Signal

import TeacherAssistant
from TeacherAssistant.models import EduItems
from PySideAbdhUI.Notify  import NotifyPropertyChanged

        
# View model for Edu-content      
class EduItemViewModel(NotifyPropertyChanged):
    
    __answer_loaded = False
    
    def __init__(self, arg__1= None) -> None:
        
        super().__init__()
        # Initialize properties
        self._properties['Id','selected','score','source','content','details','answer'] = 0, False, 0.0,'','','',''
    
    # Signals for notifying changes
    id_changed = Signal(int)
    selected_changed = Signal(bool)
    score_changed = Signal(float)
    
    # Define a property for 'id'
    Id = Property(
        int,
        lambda self: self._get_property("Id"),
        lambda self, value: self._set_property("Id", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    source = Property(
        str,
        lambda self: self._get_property("source"),
        lambda self, value: self._set_property("source", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
     
    content = Property(
        str,
        lambda self: self._get_property("content"),
        lambda self, value: self._set_property("content", value),
        notify= NotifyPropertyChanged.property_changed 
    )
      
    answer = Property(
        str,
        lambda self: self._get_property("answer"),
        lambda self, value: self._set_property("answer", value),
        notify= NotifyPropertyChanged.property_changed
    )
    
    details = Property(
        str,
        lambda self: self._get_property("details"),
        lambda self, value: self._set_property("details", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
       # Define a property for 'id'
    
    # Define a property for 'score'
    score = Property(
        float,
        lambda self: self._get_property("score"),
        lambda self, value: self._set_property("score", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    
    selected = Property(
        bool,
        lambda self: self._get_property("selected"),
        lambda self, value: self._set_property("selected", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )


    
    def load_answer(self):

        if self.__answer_loaded: return True, 'Answers recently uploaded.'
        
        msg =''
        try:
            cursor = TeacherAssistant.db_connection.cursor()
            cursor.execute(f'SELECT answer_, additional_details_ FROM educational_resources WHERE Id = {self.Id};')
            data = cursor.fetchone()
            self.answer = data[0]
            self.details = data[1]
            msg = 'answer loaded.'
            self.__answer_loaded = True
        except Exception as e:
            msg = f'Database error:{e}'

 
    def update_value(self,column_name, value):
        msg =''
        try:
            cursor =  TeacherAssistant.db_connection.cursor()
            cursor.execute(f"UPDATE educational_resources SET {column_name} = '{value}' WHERE Id = {self.Id};")
            
            return True, f'The column "{column_name}" updated successfully.'
        except Exception as e:
            
            return False, f'Database error:{e}'
        
class MaintenanceViewModel(NotifyPropertyChanged):
    
    database_name = Property(
        str,
        lambda self: self._get_property("database_name"),
        lambda self, value: self._set_property("database_name", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    host = Property(
        str,
        lambda self: self._get_property("host"),
        lambda self, value: self._set_property("host", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    port = Property(
        str,
        lambda self: self._get_property("port"),
        lambda self, value: self._set_property("port", value),
        notify= NotifyPropertyChanged.property_changed
    )

    user_name = Property(
        str,
        lambda self: self._get_property("user_name"),
        lambda self, value: self._set_property("user_name", value),
        notify= NotifyPropertyChanged.property_changed
    )

    password = Property(
        str,
        lambda self: self._get_property("password"),
        lambda self, value: self._set_property("password", value),
        notify= NotifyPropertyChanged.property_changed
    )

    postgresql_tools_path = Property(
        str,
        lambda self: self._get_property("postgresql_tools_path"),
        lambda self, value: self._set_property("postgresql_tools_path", value),
        notify= NotifyPropertyChanged.property_changed
    )

    backup_path = Property(
        str,
        lambda self: self._get_property("backup_path"),
        lambda self, value: self._set_property("backup_path", value),
        notify= NotifyPropertyChanged.property_changed
    )

    backup_type = Property(
        str,
        lambda self: self._get_property("backup_type"),
        lambda self, value: self._set_property("backup_type", value),
        notify= NotifyPropertyChanged.property_changed
    )

    restore_path = Property(
        str,
        lambda self: self._get_property("restore_path"),
        lambda self, value: self._set_property("restore_path", value),
        notify= NotifyPropertyChanged.property_changed
    )

    overwrite_restore = Property(
        bool,
        lambda self: self._get_property("overwrite_restore"),
        lambda self, value: self._set_property("overwrite_restore", value),
        notify= NotifyPropertyChanged.property_changed
    )

    restore_target_name = Property(
        str,
        lambda self: self._get_property("restore_target_name"),
        lambda self, value: self._set_property("restore_target_name", value),
        notify= NotifyPropertyChanged.property_changed
    )
# ViewModel layer
# Data structure reprsentation
class EduItemStudentViewModel(NotifyPropertyChanged):
    
    ContentUpdated = Signal(bool, str)
    ContentRemoved = Signal(bool, str)
    
    def __init__(self, model:EduItems.EduItemStudentModel):
        
        super().__init__()
        
        self.model = model
        # Initialize properties
        self._properties['Id','content','response','feedback','score','max_score', 'activation_date',
                         'deadline', 'reply_date'] = 0, '', '', '', 0.0, 1.0, '', '', ''
    
    def set_data(self,Id,content,response,feedback, score, max_score, activation_date, deadline, reply_date):
        self.Id = Id
        self.content = content
        self.response = response
        self.feedback = feedback
        self.score = score
        self.max_score = max_score
        self.activation_date = activation_date
        self.deadline = deadline
        self.reply_date =reply_date

    def save(self):
        
        status, message = self.model.update_learning_item(self.Id, self.response, self.feedback, self.score, self.reply_date)
        
        self.ContentUpdated.emit(status, message)

    def remove(self):
        
        status, message = self.model.remove_learning_item(self.Id)
        
        self.ContentRemoved.emit(status, message)


    '''`Id`: Unique Id generated by database engine'''
    Id = Property(
        int,
        lambda self: self._get_property("Id"),
        lambda self, value: self._set_property("Id", value),
        notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    
    '''`content`: the content of learning item like question, quiz, problem or ... .<br>
    this varible accepts a string in html format.'''
    content = Property(
        str,
        lambda self: self._get_property("content"),
        lambda self, value: self._set_property("content", value),
        notify= NotifyPropertyChanged.property_changed 
    )
    
    response = Property(
        str,
        lambda self: self._get_property("response"),
        lambda self, value: self._set_property("response", value),
        notify= NotifyPropertyChanged.property_changed 
    )
    
    feedback = Property(
        str,
        lambda self: self._get_property("feedback"),
        lambda self, value: self._set_property("feedback", value),
        notify= NotifyPropertyChanged.property_changed 
    )
    
    score = Property(
        float,
        lambda self: self._get_property("score"),
        lambda self, value: self._set_property("score", value),
        notify= NotifyPropertyChanged.property_changed 
    )
    
    max_score = Property(
        float,
        lambda self: self._get_property("max_score"),
        lambda self, value: self._set_property("max_score", value),
        notify= NotifyPropertyChanged.property_changed 
    )
    
    activation_date = Property(
        str,
        lambda self: self._get_property("activation_date"),
        lambda self, value: self._set_property("activation_date", value),
        notify= NotifyPropertyChanged.property_changed 
    )
    
    deadline = Property(
        str,
        lambda self: self._get_property("deadline"),
        lambda self, value: self._set_property("deadline", value),
        notify= NotifyPropertyChanged.property_changed 
    )

    reply_date = Property(
        str,
        lambda self: self._get_property("reply_date"),
        lambda self, value: self._set_property("reply_date", value),
        notify= NotifyPropertyChanged.property_changed 
    )



class ClassroomGroupViewModel():
    
    def __init__(self):#, model:EduItems.ClassroomGroupModel=None):
        super().__init__()
        self._properties = {}  # Store property values
        self._bindings = {}    # Store UI widget bindings
        # Initialize properties correctly (no tuple assignment)
        self.model = EduItems.ClassroomGroupModel(TeacherAssistant.db_connection.cursor())
        self._properties["Id"] = 0
        self._properties["grade"] = ""
        self._properties["book"] = ""
        self._properties["title"] = ""
        self._properties["description"] = ""
        self.events = ""
        self.members = ""
        #def __init__(self):
        #super().__init__()
       

    def _get_property(self, name):
        """ Get the value of a property. """
        return self._properties.get(name)

    def _set_property(self, name, value):
        if self._properties.get(name) != value:
            self._properties[name] = value
            # Emit signal with THIS instance as the sender
            #self.property_changed.emit(self, name, value)  # 🔑 Include "self"
            #self._update_bound_widget(name, value)

    Id = Property(
        int,
        lambda self: self._get_property("Id"),
        lambda self, value: self._set_property("Id", value),
        #notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    grade = Property(
        str,
        lambda self: self._get_property("grade"),
        lambda self, value: self._set_property("grade", value),
        #notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )
    
    # Define a property for 'id'
    book = Property(
        str,
        lambda self: self._get_property("book"),
        lambda self, value: self._set_property("book", value),
        #notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    # Define a property for 'id'
    title = Property(
        str,
        lambda self: self._get_property("title"),
        lambda self, value: self._set_property("title", value),
        #notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )

    description = Property(
        str,
        lambda self: self._get_property("description"),
        lambda self, value: self._set_property("description", value),
        # notify= NotifyPropertyChanged.property_changed  # Reference the signal from the base class
    )


