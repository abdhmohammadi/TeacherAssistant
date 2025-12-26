
from PySide6.QtWidgets import ( QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,QGroupBox, QLabel, QComboBox,
                                QCheckBox, QSpinBox, QLineEdit, QPushButton, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from pathlib import Path

from core.settings.settings_manager import SettingsManager
from core.settings.security import encrypt, decrypt
from core.settings.backup import backup_settings, restore_settings

class SettingsPage(QWidget):

    def __init__(self, profile="default"):
        super().__init__()

        self.profile = profile
        self.settings = SettingsManager(profile)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        lbl = QLabel("UNDER CONSTRACTION",alignment=Qt.AlignmentFlag.AlignCenter)
        lbl.setProperty('class','heading2')
        main_layout.addWidget(lbl)
        main_layout.addWidget(self._profile_section())
        main_layout.addWidget(self._general_section())
        main_layout.addWidget(self._appearance_section())
        main_layout.addWidget(self._database_section())
        main_layout.addWidget(self._backup_section())

    def _profile_section(self):
        
        box = QGroupBox("User Profile")
        layout = QHBoxLayout(box)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self._profiles())
        self.profile_combo.setCurrentText(self.profile)
        self.profile_combo.currentTextChanged.connect(self._switch_profile)

        layout.addWidget(QLabel("Active profile:"))
        layout.addWidget(self.profile_combo)
        return box

    def _profiles(self):
        profiles_dir = Path.home() / ".teacher_assistant" / "profiles"
        return [p.stem for p in profiles_dir.glob("*.ini")] or ["default"]

    def _switch_profile(self, profile):
        
        QMessageBox.information(self, "Restart Required", "Profile changed. Restart application to apply.")

    def _general_section(self):
        box = QGroupBox("General")
        form = QFormLayout(box)

        lang = QComboBox()
        lang.addItems(["fa", "en"])
        lang.setCurrentText(self.settings.get("general", "language"))
        lang.currentTextChanged.connect(
            lambda v: self.settings.set("general", "language", v)
        )

        autosave = QCheckBox("Enable autosave")
        
        autosave.setChecked(bool(self.settings.get("general", "autosave", True)))
        autosave.toggled.connect(
            lambda v: self.settings.set("general", "autosave", v)
        )

        form.addRow("Language:", lang)
        form.addRow("", autosave)
        return box

    def _appearance_section(self):
        box = QGroupBox("Appearance")
        form = QFormLayout(box)

        theme = QComboBox()
        theme.addItems(["dark", "light", "windows11"])
        theme.setCurrentText(self.settings.get("appearance", "theme"))
        theme.currentTextChanged.connect(
            lambda v: self.settings.set("appearance", "theme", v)
        )

        font = QSpinBox()
        font.setRange(8, 18)
        font.setValue(int(self.settings.get("appearance", "font_size", 10)))
        font.valueChanged.connect(
            lambda v: self.settings.set("appearance", "font_size", v)
        )

        form.addRow("Theme:", theme)
        form.addRow("Font size:", font)
        return box

    def _database_section(self):
        box = QGroupBox("Database")
        form = QFormLayout(box)

        self.db_host = QLineEdit(self.settings.get("database", "host"))

        self.db_pass = QLineEdit()
        self.db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_pass.setText(decrypt(self.settings.get("database", "password", "")))

        save_btn = QPushButton("Save Database Settings")
        save_btn.clicked.connect(self._save_db)

        form.addRow("Host:", self.db_host)
        form.addRow("Password:", self.db_pass)
        form.addRow("", save_btn)
        return box

    def _save_db(self):
        self.settings.set("database", "host", self.db_host.text())
        self.settings.set("database", "password", encrypt(self.db_pass.text()))
        QMessageBox.information(self, "Saved", "Database settings saved securely.")

    def _backup_section(self):
        box = QGroupBox("Backup & Restore")
        layout = QHBoxLayout(box)

        backup_btn = QPushButton("Backup")
        restore_btn = QPushButton("Restore")

        backup_btn.clicked.connect(self._backup)
        restore_btn.clicked.connect(self._restore)

        layout.addWidget(backup_btn)
        layout.addWidget(restore_btn)
        return box

    def _backup(self):
        file = backup_settings(self.settings.file)
        QMessageBox.information(self, "Backup Created", str(file))

    def _restore(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Restore Settings", "", "INI Files (*.ini)"
        )
        if file:
            restore_settings(Path(file), self.settings.file)
            QMessageBox.information(
                self, "Restored", "Restart application to apply."
            )

