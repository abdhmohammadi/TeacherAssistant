
import  re

class ThemeManager:
    _theme_data = None

    @classmethod
    def _load_theme(cls,file_path:str):
        cls.__theme_file = file_path
        """Load the theme file and parse its content."""
        with open(cls.__theme_file, "r") as file:
            cls._theme_data = file.read()

    @classmethod
    def _save_theme(cls):
        """Save the updated theme data back to the file."""
        with open(cls.__theme_file, "w") as file:
            file.write(cls._theme_data)

    @classmethod
    def _parse_color_definitions(cls):
        """Parse the color definitions from the theme data."""
        # Updated regex to handle color names with spaces, hyphens, etc.
        color_pattern = re.compile(r"([\w\s-]+):\s*(#[0-9a-fA-F]+)\s*;.*")
        return dict(color_pattern.findall(cls._theme_data))

    @classmethod
    def get_color(cls, color_name):
        """Get the value of a specific color by its name."""
        #cls._load_theme()
        colors = cls._parse_color_definitions()
        return colors.get(color_name)

    @classmethod
    def add_color(cls, color_name, color_value):
        """Add or update a color definition in the theme."""
        #cls._load_theme()
        color_pattern = re.compile(rf"({re.escape(color_name)}):\s*(#[0-9a-fA-F]+)\s*;.*")
        new_color_definition = f"{color_name}: {color_value};"

        if color_pattern.search(cls._theme_data):
            # Update existing color
            cls._theme_data = color_pattern.sub(new_color_definition, cls._theme_data)
        else:
            # Add new color
            cls._theme_data += f"\n{new_color_definition}"

        cls._save_theme()
        cls._load_theme(cls.__theme_file)

    @classmethod
    def remove_color(cls, color_name):
        """Remove a color definition from the theme."""
        #cls._load_theme()
        color_pattern = re.compile(rf"({re.escape(color_name)}):\s*(#[0-9a-fA-F]+)\s*;.*\n?")
        cls._theme_data = color_pattern.sub("", cls._theme_data)
        cls._save_theme()
        cls._load_theme(cls.__theme_file)


    @classmethod
    def find_color(cls, color_value):
        """Find the name of a color by its value."""
        #cls._load_theme()
        colors = cls._parse_color_definitions()
        for name, value in colors.items():
            if value.lower() == color_value.lower():
                return name
        return None

    @classmethod
    def get_all_colors(cls):
        """Return all color definitions as a dictionary."""
        return cls._parse_color_definitions()
  