# settings_manager.py (INI + Profiles)

from PySide6.QtCore import QSettings
from pathlib import Path
from .defaults import DEFAULT_SETTINGS


class SettingsManager:
    def __init__(self, profile="default"):
        self.profile = profile

        self.base_dir = Path.home() / ".teacher_assistant" / "profiles"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.file = self.base_dir / f"{profile}.ini"
        self.settings = QSettings(str(self.file), QSettings.IniFormat)

        self._load_defaults()

    def _load_defaults(self):
        for group, values in DEFAULT_SETTINGS.items():
            self.settings.beginGroup(group)
            for key, value in values.items():
                if self.settings.value(key) is None:
                    self.settings.setValue(key, value)
            self.settings.endGroup()

    def get(self, group, key, default=None):
        self.settings.beginGroup(group)
        value = self.settings.value(key, default)
        self.settings.endGroup()
        return value

    def set(self, group, key, value):
        self.settings.beginGroup(group)
        self.settings.setValue(key, value)
        self.settings.endGroup()

    def reset(self):
        self.settings.clear()
        self._load_defaults()
