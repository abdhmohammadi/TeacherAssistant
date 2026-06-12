# Auromatied qrc resource compiler:
#
# HOW TO COMPILE QRC RESOURCES MANUALLY:
# Run below command: 
# F:\Projects\Python\Teaching-assistant-project\TeacherAssistant\env\Lib\site-packages\PySide6\rcc.exe --generator python F:\Projects\Python\Teaching-assistant-project\TeacherAssistant\src\teacher_assistant\resources\resources.qrc -o F:\Projects\Python\Teaching-assistant-project\TeacherAssistant\src\teacher_assistant\resources\resources_rc.py
#
import subprocess
from pathlib import Path

# Paths
rcc_path = Path(
    r"F:\Projects\Python\Teaching-assistant-project\TeacherAssistant\env\Lib\site-packages\PySide6\rcc.exe"
)

qrc_file = Path(
    r"F:\Projects\Python\Teaching-assistant-project\TeacherAssistant\src\teacher_assistant\resources\resources.qrc"
)

output_py = Path(
    r"F:\Projects\Python\Teaching-assistant-project\TeacherAssistant\src\teacher_assistant\resources\resources_rc.py"
)

# Build command
command = [
    str(rcc_path),
    "--generator", "python",
    str(qrc_file),
    "-o", str(output_py),
]

# Run
result = subprocess.run(
    command,
    capture_output=True,
    text=True
)

# Debug output
if result.returncode == 0:
    print("QRC compiled successfully!")
else:
    print("QRC compilation failed!")
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
 