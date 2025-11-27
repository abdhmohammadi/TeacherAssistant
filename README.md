# Teacher Assistant
pre-alpha version

A modern, user-friendly teacher assistance application built with PySide6 (Qt for Python).
This application helps educational resources managment and student information with a beautiful, customizable interface.
This project is currently in its early stages...

## Features

- 🎨 **Customizable UI**
  - Multiple theme support
  - Customizable fonts
  - RTL/LTR layout support
  - Modern, clean interface

- 📚 **Educational Resource Management**
  - View and manage educational resources
  - Resource editor for creating and modifying content
  - Support PDF, Image, HTML and LaTeX in resource editor
  - Organized educational contents 
  - Producing tests in two formats: classroom quizzes and formal exams
  - Ability to distribute tests in PDF and HTML format
  - Snipping tool to import image resources

- 👥 **Student Management**
  - Student list management
  - Personal information tracking
  - Easy navigation between student records
  - Tracking student's behavioral events in order to achieve educational 

- 🌐 **Multilingual Support** (in progress)
  - English and Persian language support
  - RTL/LTR text direction handling
  - Localized interface elements

- ⚙️ **Customizable Settings** 
  - Font selection
  - Theme customization
  - Layout direction preferences
  - LaTeX document settings (in progress)

- ## Next phase of the project
  - Organizing student groups
  - Assigning tests to students in groups and individually
  - Getting answers back from students in image and PDF format for assigned tests

<--
## Installation

1. Clone the repository:
```bash
git clone https://github.com/abdhmohammadi/MyJobAssistant.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python MyJobAssistant/main.py
```

## Building Executable

To create a standalone executable:

```bash
pyinstaller pyinstaller/spec/MyJobAssistant.spec
```

For Windows installer creation, use InnoSetup with the provided script. --!>

## Project Structure

```
MyJobAssistant/
├── main.py                 # Main application entry point
├── resources/              # Application resources
│   ├── icons/              # Application icons
│   ├── fonts/              # Custom fonts
│   └── styles/             # QSS style sheets
├── views/                  # UI views and forms
├── utils/                  # Utility functions
└── PySideAbdhUI/           # Custom UI components
```

## Dependencies

- PySide6
- PostgreSQL (for database)
- Other dependencies listed in requirements.txt

## Configuration

The application stores settings in the user's LOCALAPPDATA directory:
- `%LOCALAPPDATA%/MyJobAssistant/settings.json`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

- Abdh Mohammadi
- GitHub: [abdhmohammadi](https://github.com/abdhmohammadi)

## Acknowledgments

- Built with PySide6 (Qt for Python)
- Uses custom UI components from PySideAbdhUI
- Icons and resources are custom-designed