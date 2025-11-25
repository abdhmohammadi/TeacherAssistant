# Teacher Assistant

A desktop application for teaching/workflow assistance built with Python and PySide (PySideAbdhUI). Provides utilities and UI components to support lesson preparation and classroom tasks.

## Key Features

- Cross-platform Qt-based desktop UI (Windows focused)
- Modular CLI and GUI entry points
- Easily packaged with PyInstaller and distributed with Inno Setup
- Simple project structure for extension and customization

## Requirements

- Python 3.10+ (project used with Python 3.14 in development notes)
- Windows recommended for installer steps
- Dependencies listed in `requirements.txt` (or install via editable wheel for PySideAbdhUI)

## Quickstart (Windows)

1. Clone the repository:
   - git clone <repo-url>

2. Create a virtual environment (recommended name: `env`):
   PowerShell:
   ```powershell
   python -m venv .\env
   .\env\Scripts\Activate.ps1
   ```
   cmd.exe:
   ```cmd
   python -m venv .\env
   .\env\Scripts\activate.bat
   ```

3. Install dependencies:
   - If using the local wheel for PySideAbdhUI (adjust path as needed):
     ```powershell
     pip install F:\Projects\Python\PySideAbdhUI\dist\PySideAbdhUI-1.0.4-py3-none-any.whl
     ```
   - Or editable install for development:
     ```powershell
     pip install -e F:\Projects\Python\PySideAbdhUI
     ```
   - Or install from GitHub:
     ```powershell
     pip install git+https://github.com/abdhmohammadi/PySideAbdhUI.git
     ```

4. Run the application:
   ```powershell
   python main.py
   ```

## Packaging & Distribution

1. Build with PyInstaller:
   - Generate executable using the provided spec:
     ```powershell
     pyinstaller TeacherAssistant.spec
     ```
   - If path issues occur:
     ```powershell
     C:\Users\<User>\AppData\Roaming\Python\Python3x\Scripts\pyinstaller TeacherAssistant.spec
     ```

2. Create an installer:
   - Use Inno Setup to wrap the generated executable into a Windows installer.

## Project Layout (high level)

- main.py — Application entry point
- TeacherAssistant/ — Package source
- requirements.txt — Pin dependencies for deployment
- TeacherAssistant.spec — PyInstaller spec file

## VS Code

- Select the interpreter from `. \env\Scripts\python.exe` via Command Palette: `Python: Select Interpreter`.
- Update workspace settings if needed:
  ```
  "python.defaultInterpreterPath": "F:\\Projects\\Python\\Teaching-assistant-project\\env\\Scripts\\python.exe"
  ```

## Troubleshooting

- If you manually renamed the virtual environment folder:
  - Update any scripts/docs referencing the old name (e.g., `abdh_env` → `env`).
  - Re-select interpreter in VS Code.
  - If activation or shebangs break, recreate the venv (`python -m venv .\env`) and reinstall packages:
    ```powershell
    .\old_env\Scripts\python -m pip freeze > requirements.txt
    python -m venv .\env
    .\env\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    ```

## Contributing

- Fork the repository, create a feature branch, and submit a pull request.
- Run unit tests and linters before submitting.

## License

- MIT License — see LICENSE file.

## Contact

- Project maintainer: see repository metadata or contact via project issue tracker.