# gui/app_profile_dialog.py
"""The application profile dialog for the application."""
import psutil
import win32gui
import win32process
from PyQt5 import QtWidgets, QtGui
import os

class AppProfileDialog(QtWidgets.QDialog):
    """The application profile dialog."""
    def __init__(self, parent=None, current_app_name=None, current_interval=0.3, current_threshold=2):
        super().__init__(parent)
        self.setWindowTitle("Application Profile")
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "..", "mouse.ico")))
        self.setFixedSize(400, 250)
        
        self.current_app_name = current_app_name
        self.current_interval = current_interval
        self.current_threshold = current_threshold
        
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        form_layout = QtWidgets.QFormLayout()
        
        self.app_name_input = QtWidgets.QLineEdit()
        self.app_name_input.setPlaceholderText("e.g., chrome.exe")
        if self.current_app_name:
            self.app_name_input.setText(self.current_app_name)
            # If editing, maybe don't allow changing name? Or allow rename.
            # Let's allow rename for now.
        
        self.interval_spin = QtWidgets.QDoubleSpinBox()
        self.interval_spin.setRange(0.05, 5.0)
        self.interval_spin.setSingleStep(0.05)
        self.interval_spin.setValue(self.current_interval)
        
        self.threshold_spin = QtWidgets.QSpinBox()
        self.threshold_spin.setRange(1, 10)
        self.threshold_spin.setValue(self.current_threshold)
        
        form_layout.addRow("Application Name:", self.app_name_input)
        form_layout.addRow("Block Interval (s):", self.interval_spin)
        form_layout.addRow("Direction Threshold:", self.threshold_spin)
        
        layout.addLayout(form_layout)
        
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        layout.addWidget(self.button_box)
        
        # Input Validation
        self.ok_btn = self.button_box.button(QtWidgets.QDialogButtonBox.Ok)
        self.app_name_input.textChanged.connect(self._validate_input)
        self._validate_input() # Initial check

    def _validate_input(self):
        """Disables the OK button if the app name is empty."""
        is_valid = bool(self.app_name_input.text().strip())
        self.ok_btn.setEnabled(is_valid)

    def _get_current_app(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = psutil.Process(pid).name()
            self.app_name_input.setText(proc_name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            QtWidgets.QMessageBox.warning(self, "Error", "Could not get foreground application name.")

    def get_profile_data(self):
        """Gets the profile data from the dialog."""
        return {
            "app_name": self.app_name_input.text(),
            "interval": self.interval_spin.value(),
            "threshold": self.threshold_spin.value()
        }
