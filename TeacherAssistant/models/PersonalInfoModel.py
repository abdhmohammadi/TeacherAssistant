from datetime import datetime
from psycopg2 import Error
from psycopg2.extensions import cursor
from dateutil.parser import parse

def parse_flexible_date(s: str):
    
    try:
        return parse(s)   # returns datetime
    except (ValueError, TypeError):
        return None
# Model (Data Layer)
class PersonalInfoModel:

    def __init__(self,db_cursor:cursor):
        
        self.__cursor = db_cursor
        #self.__table = 'personal_info'

    def delete(self,id):
        try:

            self.__cursor.execute(f'DELETE FROM personal_info WHERE id ={id};')

            return True, self.__cursor.rowcount
        
        except Error as e: return False, e

    def fetch(self,query):
        try:
            self.__cursor.execute(query=query)

            records = self.__cursor.fetchall()
            
            return True, records
        
        except Error as e: return False, f'Error: {e}.'

    def save(self, id:str, fname:str, lname:str, birth_date:str, gender:str, phone:str, address:str, parent:str,
                   parent_phone:str, additional_details:str, photo:bytes, old_id:str = None):
        # 1. Save personal data in personal_info table
        # 2. check id in the ungrouped record of groups
        #  1. if not exist in the group then add id to unrouped record
        #     this property is used to manage classroom groups
        #  2. if id exist in the ungrouped record is updated by new id(if needed)
        try:
            # Chack and parse birth_date
            if not isinstance(parse_flexible_date(birth_date), datetime):
                birth_date = str(datetime.now().strftime("%Y-%m-%d"))
            
            if old_id == '' or old_id == None:
                # Insert personal information into the table
                query  = 'INSERT INTO personal_info(id, fname_, lname_, parent_name_, phone_, parent_phone_, address_, '
                query += 'additional_details_, birth_date_, gender_, photo_) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
                
                params = (id, fname, lname, parent, phone, parent_phone, address, additional_details, birth_date, gender, photo)
            
            else:
            
                query = 'UPDATE personal_info SET id= %s, fname_=%s, lname_=%s, parent_name_=%s, phone_=%s, parent_phone_=%s, address_=%s, '
                query += 'additional_details_=%s, photo_=%s, birth_date_=%s, gender_=%s WHERE Id=%s;'
                
                params = (id, fname, lname, parent, phone, parent_phone, address, additional_details, photo, birth_date, gender, old_id)

            self.__cursor.execute(query, params)
            
            # 'ungrouped' record is recognized by grade_ = 0 currently(this is not strong condition)
            self.__cursor.execute('SELECT members_ FROM groups WHERE grade_ = 0;')
            members = self.__cursor.fetchone()[0]
            
            if members:
                i = str(members).find(id)
                if i < 0:
                    members = f'{members},{id}'
                    self.__cursor.execute('UPDATE groups SET members_ = %s WHERE grade_ = 0;',(members,))

            return True, self.__cursor.rowcount
        
        except Error as e: return False, f"Database Error: {e}"