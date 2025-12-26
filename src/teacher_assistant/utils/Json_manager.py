import json
from typing import Any, Dict, Tuple, Optional

class JSONManager:
    def __init__(self, file_path: str = None):
        self.file_path = file_path
    
    def set_path(self, path): self.file_path = path

    def read(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format.")
    
    def write(self, data: Dict[str, Any]) -> None:
        #Write data to the JSON file, preserving existing content.
        #Raises a ValueError if `data` is not a dictionary.
    
        if not isinstance(data, dict): raise ValueError("Data must be a dictionary.")
    
        existing_data = self.read()
        existing_data.update(data)  # Merge new data with existing data
        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(existing_data, file, indent=4)
    
    def _get_nested(self, keys: str, data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        keys_list = keys.split('.')
        for key in keys_list[:-1]:
            if key not in data:
                data[key] = {}
            elif not isinstance(data[key], dict):
                raise TypeError(f"Cannot set nested key inside non-dictionary value: {key} -> {data[key]}")
            data = data[key]
        return data, keys_list[-1]
    
    def update(self, key: str, value: Any) -> None:
        data = self.read()
        nested_data, last_key = self._get_nested(key, data)
        nested_data[last_key] = value
        self.write(data)
    
    def delete(self, key: str) -> None:
        data = self.read()
        nested_data, last_key = self._get_nested(key, data)
        if last_key in nested_data:
            del nested_data[last_key]
            self.write(data)
    
    def exists(self, key: str) -> bool:
        data = self.read()
        try:
            nested_data, last_key = self._get_nested(key, data)
            return last_key in nested_data
        except TypeError:
            return False
    
    def find_value(self, key: str) -> Optional[Any]:
        """
        Find and return the value associated with the given key (including nested keys).
        Returns None if the key does not exist.
        """
        data = self.read()
        try:
            nested_data, last_key = self._get_nested(key, data)
            
            return nested_data.get(last_key)
        except TypeError:
            return None

def run_test():
    json_file = "data.json"
    manager = JSONManager(json_file)
    
    while True:
        print("\nJSON Manager Options:")
        print("1. Read JSON file")
        print("2. Write JSON file")
        print("3. Update a key")
        print("4. Delete a key")
        print("5. Check if a key exists")
        print("6. Find a value by key")
        print("7. Exit")
        
        choice = input("Enter your choice: ")
        
        if choice == "1":
            print("Data:", manager.read())
        elif choice == "2":
            data = input("Enter JSON data (as a dictionary): ")
            try:
                manager.write(json.loads(data))
                print("Data written successfully.")
            except json.JSONDecodeError:
                print("Invalid JSON format.")
        elif choice == "3":
            key = input("Enter key (dot notation for nested): ")
            value = input("Enter value: ")
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # Keep value as string if it's not valid JSON
            try:
                manager.update(key, value)
                print("Key updated successfully.")
            except TypeError as e:
                print(f"Error: {e}")
        elif choice == "4":
            key = input("Enter key (dot notation for nested): ")
            manager.delete(key)
            print("Key deleted successfully.")
        elif choice == "5":
            key = input("Enter key (dot notation for nested): ")
            print("Exists:", manager.exists(key))
        elif choice == "6":
            key = input("Enter key (dot notation for nested): ")
            value = manager.find_value(key)
            if value is not None:
                print(f"Value for key '{key}': {value}")
            else:
                print(f"Key '{key}' not found.")
        elif choice == "7":
            confirm = input("Are you sure you want to exit? (y/n): ")
            if confirm.lower() == 'y':
                break
        else:
            print("Invalid choice. Please try again.")
