import shutil
from datetime import datetime
from pathlib import Path


def backup_settings(settings_file: Path) -> Path:
    backup_dir = settings_file.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{settings_file.stem}_{timestamp}.ini"

    shutil.copy(settings_file, backup_file)
    return backup_file


def restore_settings(backup_file: Path, target_file: Path):
    shutil.copy(backup_file, target_file)
