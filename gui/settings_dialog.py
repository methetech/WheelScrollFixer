"""Settings dialog for the WheelScrollFixer application."""
import os
import sys
from utils import get_foreground_process_name
from PyQt5 import QtWidgets, QtGui, QtCore
from .app_profile_dialog import AppProfileDialog
from .help_dialog import HelpDialog
from .about_dialog import AboutDialog
from .calibration_wizard import CalibrationWizardDialog

class SettingsDialog(QtWidgets.QDialog):
    """The main settings dialog for the application."""
    def __init__(self, app_context, configure_startup):
        super().__init__()
        self.app_context = app_context
        self.settings = app_context.settings
        self.hook = app_context.hook
        self.update_tray_icon_callback = app_context.update_tray_icon_callback
        self.update_font_callback = app_context.update_font_callback
        self.tray = app_context.tray
        

        self._init_ui(configure_startup)

    def _init_ui(self, configure_startup):
        """Initializes the user interface."""
        self.setWindowTitle('Scroll Lock Settings')
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "..", "mouse.ico")))

        self._create_widgets()
        self._create_layouts()
        self._create_main_layout() # Explicit call
        self._connect_signals(configure_startup)

    def _create_widgets(self):
        """Creates the widgets for the dialog."""
        # --- Menu Bar ---
        self.menu_bar = QtWidgets.QMenuBar(self)
        help_menu = self.menu_bar.addMenu("&Help")
        act_about = help_menu.addAction("&About")
        act_documentation = help_menu.addAction("&Website")
        act_help_content = help_menu.addAction("Help &Content")
        act_whats_this = help_menu.addAction("What's &This?")
        act_whats_this.setShortcut(QtGui.QKeySequence("Shift+F1"))
        act_whats_this.triggered.connect(QtWidgets.QWhatsThis.enterWhatsThisMode)

        act_about.triggered.connect(self.show_about_dialog)
        act_documentation.triggered.connect(self.open_website)
        act_help_content.triggered.connect(self.show_help_dialog)
        
        # --- Tab 1: General ---
        self.start_cb = QtWidgets.QCheckBox("Start on boot")
        self.start_cb.setChecked(self.settings.get_startup())
        self.start_cb.setToolTip('If checked, the application will start automatically when Windows boots.')
        
        self.enabled_cb = QtWidgets.QCheckBox('Enable Scroll Blocking')
        self.enabled_cb.setChecked(self.settings.get_enabled())
        self.enabled_cb.setToolTip('Master switch to enable or disable the scroll blocking functionality.')

        self.font_size_spin = QtWidgets.QDoubleSpinBox()
        self.font_size_spin.setRange(8.0, 24.0)
        self.font_size_spin.setSingleStep(0.5)
        self.font_size_spin.setValue(self.settings.get_font_size())
        self.font_size_spin.setToolTip('Adjust the global font size for the application UI.')

        # --- Tab 2: Sensitivity (Blocking Logic) ---
        self.interval_spin = QtWidgets.QDoubleSpinBox()
        self.interval_spin.setRange(0.05, 5.0)
        self.interval_spin.setSingleStep(0.05)
        self.interval_spin.setValue(self.settings.get_interval())
        self.interval_spin.setToolTip('The time interval (in seconds) during which rapid scroll direction changes will be blocked.')

        self.direction_change_threshold_spin = QtWidgets.QSpinBox()
        self.direction_change_threshold_spin.setRange(1, 10)
        self.direction_change_threshold_spin.setValue(self.settings.get_direction_change_threshold())
        self.direction_change_threshold_spin.setToolTip('Number of opposite scroll events required to change direction.')

        self.strict_mode_cb = QtWidgets.QCheckBox("Strict Mode (Ignores first tick)")
        self.strict_mode_cb.setChecked(self.settings.get_strict_mode())
        self.strict_mode_cb.setToolTip('Require two consecutive scrolls in the same direction to start scrolling.')

        self.min_reversal_spin = QtWidgets.QDoubleSpinBox()
        self.min_reversal_spin.setRange(0.01, 0.20)
        self.min_reversal_spin.setSingleStep(0.01)
        self.min_reversal_spin.setValue(self.settings.get_min_reversal_interval())
        self.min_reversal_spin.setToolTip('Minimum time (in seconds) required between opposite scroll events (Physics Check).')

        self.smart_momentum_cb = QtWidgets.QCheckBox("Smart Momentum (Dynamic Threshold)")
        self.smart_momentum_cb.setChecked(self.settings.get_smart_momentum())
        self.smart_momentum_cb.setToolTip('Automatically increase threshold when scrolling fast.')

        # --- Tab 3: Apps (Blacklist & Profiles) ---
        self.bl_list = QtWidgets.QListWidget()
        self.bl_list.addItems(self.settings.get_blacklist())
        
        self.bl_add_current_btn = QtWidgets.QPushButton('Add Current App')
        self.bl_remove_btn = QtWidgets.QPushButton("Remove Selected")
        self.bl_clear_btn = QtWidgets.QPushButton("Clear All")

        self.app_profiles_list = QtWidgets.QListWidget()
        self.add_profile_btn = QtWidgets.QPushButton('Add Profile')
        self.edit_profile_btn = QtWidgets.QPushButton('Edit Profile')
        self.remove_profile_btn = QtWidgets.QPushButton('Remove Profile')

        # --- Actions (Bottom) ---
        self.save_btn = QtWidgets.QPushButton('Save')
        self.save_btn.setToolTip("Save all settings.")
        
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #2e7d32; font-weight: bold; margin-top: 5px;")

    def _create_layouts(self):
        """Creates the layouts for the dialog."""
        # --- Blocking Logic Group ---
        blocking_group = QtWidgets.QGroupBox("Blocking Logic & Sensitivity")
        blocking_layout = QtWidgets.QFormLayout()
        blocking_layout.addRow("Block interval (s):", self.interval_spin)
        blocking_layout.addRow("Direction threshold:", self.direction_change_threshold_spin)
        blocking_layout.addRow("Min Reversal Time (s):", self.min_reversal_spin)
        blocking_layout.addRow(self.strict_mode_cb)
        blocking_layout.addRow(self.smart_momentum_cb)
        blocking_group.setLayout(blocking_layout)
        self.blocking_group = blocking_group

        # --- Application Control Group ---
        app_control_group = QtWidgets.QGroupBox("Application Control")
        app_control_layout = QtWidgets.QVBoxLayout()
        
        # Blacklist
        bl_layout = QtWidgets.QHBoxLayout()
        bl_layout.addWidget(QtWidgets.QLabel("Blacklist:"))
        bl_layout.addWidget(self.bl_add_current_btn)
        bl_layout.addWidget(self.bl_remove_btn)
        bl_layout.addWidget(self.bl_clear_btn)
        app_control_layout.addLayout(bl_layout)
        app_control_layout.addWidget(self.bl_list)
        
        # Profiles
        prof_layout = QtWidgets.QHBoxLayout()
        prof_layout.addWidget(QtWidgets.QLabel("Profiles:"))
        prof_layout.addWidget(self.add_profile_btn)
        prof_layout.addWidget(self.edit_profile_btn)
        prof_layout.addWidget(self.remove_profile_btn)
        app_control_layout.addLayout(prof_layout)
        app_control_layout.addWidget(self.app_profiles_list)
        
        app_control_group.setLayout(app_control_layout)
        self.app_control_group = app_control_group

        # --- General Settings Group ---
        general_group = QtWidgets.QGroupBox("General")
        general_layout = QtWidgets.QHBoxLayout()
        general_layout.addWidget(self.enabled_cb)
        general_layout.addWidget(self.start_cb)
        
        font_layout = QtWidgets.QHBoxLayout()
        font_layout.addWidget(QtWidgets.QLabel("Font Size:"))
        font_layout.addWidget(self.font_size_spin)
        
        general_layout.addLayout(font_layout)
        general_group.setLayout(general_layout)
        self.general_settings_group = general_group

    def _create_main_layout(self):
        """Creates the main layout for the dialog."""
        form = QtWidgets.QVBoxLayout(self)
        form.setMenuBar(self.menu_bar)
        
        # Layout Order
        form.addWidget(self.blocking_group)
        form.addWidget(self.app_control_group)
        form.addWidget(self.general_settings_group)
        
        # Bottom Action Area
        bottom_layout = QtWidgets.QHBoxLayout()
        
        # Add Calibration Wizard Button
        self.calibration_btn = QtWidgets.QPushButton("Calibration Wizard")
        self.calibration_btn.setStyleSheet("background-color: #673AB7; color: white;") # Purple accent
        bottom_layout.addWidget(self.calibration_btn)

        # Add Restore Defaults Button
        self.defaults_btn = QtWidgets.QPushButton("Restore Defaults")
        self.defaults_btn.setToolTip("Reset all settings to the recommended defaults.")
        bottom_layout.addWidget(self.defaults_btn)
        
        bottom_layout.addStretch() # Spacer
        bottom_layout.addWidget(self.save_btn)
        
        form.addLayout(bottom_layout)
        form.addWidget(self.status_label)

    def _connect_signals(self, configure_startup):
        """Connects the signals for the dialog."""
        self.save_btn.clicked.connect(lambda: self.save(configure_startup))
        self.bl_add_current_btn.clicked.connect(self.add_current_app_to_blacklist)
        self.bl_remove_btn.clicked.connect(self.remove_selected_from_blacklist)
        self.bl_clear_btn.clicked.connect(self.clear_blacklist)

        # Initialize app profiles list
        self.refresh_app_profiles_list()

        # Connect app profile buttons
        self.add_profile_btn.clicked.connect(self.add_app_profile)
        self.edit_profile_btn.clicked.connect(self.edit_app_profile)
        self.remove_profile_btn.clicked.connect(self.remove_app_profile)
        self.calibration_btn.clicked.connect(self.run_calibration_wizard)
        self.defaults_btn.clicked.connect(self.restore_defaults)

    def minimize_to_tray(self):
        self.hide()
        # Show a message from the tray icon
        self.tray.showMessage(
            "WheelScrollFixer",
            "Application minimized to tray. Click the icon to restore.",
            self.app_context.icon,
            2000 # 2 seconds
        )

    def closeEvent(self, event):
        # Check if settings have changed but not saved
        current_settings = {
            'interval': self.interval_spin.value(),
            'threshold': self.direction_change_threshold_spin.value(),
            'strict_mode': self.strict_mode_cb.isChecked(),
            'min_reversal': self.min_reversal_spin.value(),
            'smart_momentum': self.smart_momentum_cb.isChecked(),
            'blacklist': [self.bl_list.item(i).text() for i in range(self.bl_list.count())],
            'startup': self.start_cb.isChecked(),
            'enabled': self.enabled_cb.isChecked(),
            'font_size': self.font_size_spin.value()
        }

        saved_settings = {
            'interval': self.settings.get_interval(),
            'threshold': self.settings.get_direction_change_threshold(),
            'strict_mode': self.settings.get_strict_mode(),
            'min_reversal': self.settings.get_min_reversal_interval(),
            'smart_momentum': self.settings.get_smart_momentum(),
            'blacklist': self.settings.get_blacklist(),
            'startup': self.settings.get_startup(),
            'enabled': self.settings.get_enabled(),
            'font_size': self.settings.get_font_size()
        }

        if current_settings != saved_settings:
            reply = QtWidgets.QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before closing?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Yes
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.save_btn.click()
                self.hide()
                event.ignore()
            elif reply == QtWidgets.QMessageBox.No:
                # Revert changes in UI to match saved settings next time it opens
                self.interval_spin.setValue(saved_settings['interval'])
                self.direction_change_threshold_spin.setValue(saved_settings['threshold'])
                self.strict_mode_cb.setChecked(saved_settings['strict_mode'])
                self.min_reversal_spin.setValue(saved_settings['min_reversal'])
                self.smart_momentum_cb.setChecked(saved_settings['smart_momentum'])
                self.bl_list.clear()
                self.bl_list.addItems(saved_settings['blacklist'])
                self.start_cb.setChecked(saved_settings['startup'])
                self.enabled_cb.setChecked(saved_settings['enabled'])
                self.font_size_spin.setValue(saved_settings['font_size'])
                self.hide()
                event.ignore()
            else:
                event.ignore()
        else:
            self.hide()
            event.ignore()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.isMinimized():
                # Let the window minimize to the taskbar normally
                pass
        super().changeEvent(event)

    def refresh_app_profiles_list(self):
        self.app_profiles_list.clear()
        for app_name, profile in self.settings.get_app_profiles().items():
            interval = profile.get('interval', self.settings.get_interval())
            threshold = profile.get('threshold', self.settings.get_direction_change_threshold())
            self.app_profiles_list.addItem(
                f"{app_name}: Interval={interval:.2f}s, Threshold={threshold}"
            )

    def add_app_profile(self):
        dialog = AppProfileDialog(parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            data = dialog.get_profile_data()
            app_name = data['app_name'].lower()
            if not app_name:
                QtWidgets.QMessageBox.warning(self, "Input Error", "Application name cannot be empty.")
                return

            profiles = self.settings.get_app_profiles()
            profiles[app_name] = {
                'interval': data['interval'],
                'threshold': data['threshold']
            }
            self.settings.set_app_profiles(profiles)
            self.refresh_app_profiles_list()
            self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)

    def edit_app_profile(self):
        selected_items = self.app_profiles_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Selection Error", "Please select a profile to edit.")
            return

        selected_item = selected_items[0]
        item_text = selected_item.text()
        app_name_raw = item_text.split(':')[0].strip()
        app_name = app_name_raw.lower()

        profiles = self.settings.get_app_profiles()
        profile_data = profiles.get(app_name, {})

        dialog = AppProfileDialog(
            current_app_name=app_name_raw,
            current_interval=profile_data.get('interval', self.settings.get_interval()),
            current_threshold=profile_data.get(
                'threshold', self.settings.get_direction_change_threshold()
            ),
            parent=self
        )

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            data = dialog.get_profile_data()
            new_app_name = data['app_name'].lower()
            if not new_app_name:
                QtWidgets.QMessageBox.warning(self, "Input Error", "Application name cannot be empty.")
                return

            # If app name changed, remove old entry
            if new_app_name != app_name:
                del profiles[app_name]

            profiles[new_app_name] = {
                'interval': data['interval'],
                'threshold': data['threshold']
            }
            self.settings.set_app_profiles(profiles)
            self.refresh_app_profiles_list()
            self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)

    def remove_app_profile(self):
        selected_items = self.app_profiles_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Selection Error", "Please select a profile to remove.")
            return

        reply = QtWidgets.QMessageBox.question(
            self, "Confirm Removal", "Are you sure you want to remove the selected profile(s)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            profiles = self.settings.get_app_profiles()
            for item in selected_items:
                app_name = item.text().split(':')[0].strip().lower()
                if app_name in profiles:
                    del profiles[app_name]
            self.settings.set_app_profiles(profiles)
            self.refresh_app_profiles_list()
            self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)



    def show_help_dialog(self):
        HelpDialog(self).exec_()

    def show_about_dialog(self):
        AboutDialog(self).exec_()

    def open_website(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://en.MetheTech.com"))

    def add_current_app_to_blacklist(self):
        # Hide briefly so the dialog isn't the foreground window
        self.hide()
        QtCore.QTimer.singleShot(120, self._get_and_add_foreground_app)

    def _get_and_add_foreground_app(self):
        proc_name = get_foreground_process_name()
        existing = [self.bl_list.item(i).text() for i in range(self.bl_list.count())]
        if proc_name and proc_name not in existing:
            self.bl_list.addItem(proc_name)
        self.show()

    def remove_selected_from_blacklist(self):
        for item in self.bl_list.selectedItems():
            self.bl_list.takeItem(self.bl_list.row(item))

    def clear_blacklist(self):
        self.bl_list.clear()

    def apply_settings(self):
        """Applies the settings to the application."""
        self.update_font_callback()

    def run_calibration_wizard(self):
        wizard = CalibrationWizardDialog(self)
        
        # Connect global hook to wizard
        self.hook.set_calibration_callback(wizard.process_scroll_event)
        
        result = wizard.exec_()
        
        # Disconnect hook
        self.hook.set_calibration_callback(None)

        if result == QtWidgets.QDialog.Accepted:
            results = wizard.get_results()
            if results:
                # Apply settings to UI
                self.interval_spin.setValue(results['interval'])
                self.direction_change_threshold_spin.setValue(results['threshold'])
                self.strict_mode_cb.setChecked(results['strict'])
                self.min_reversal_spin.setValue(results['min_reversal'])
                self.smart_momentum_cb.setChecked(results['smart'])
                
                # Auto-save applied settings
                self.save_btn.click()
                
                QtWidgets.QMessageBox.information(
                    self, "Calibration Complete", 
                    "Settings have been optimized for your mouse!"
                )

    def restore_defaults(self):
        """Restores settings to the 'Golden Default' values."""
        reply = QtWidgets.QMessageBox.question(
            self, "Confirm Reset", 
            "Are you sure you want to restore the default settings?\n"
            "(Threshold: 2, Interval: 0.30s, Strict Mode: ON, Physics: 0.05s, Smart Momentum: ON)",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.interval_spin.setValue(0.30)
            self.direction_change_threshold_spin.setValue(2)
            self.strict_mode_cb.setChecked(True)
            self.min_reversal_spin.setValue(0.05)
            self.smart_momentum_cb.setChecked(True)
            self.enabled_cb.setChecked(True)
            
            # Auto-save
            self.save_btn.click()
            self.status_label.setText("Restored to defaults successfully.")

    def save(self, configure_startup):
        """Saves all settings and applies them live."""
        self.settings.set_interval(self.interval_spin.value())
        bl = [self.bl_list.item(i).text() for i in range(self.bl_list.count())]
        self.settings.set_blacklist(bl)
        self.settings.set_startup(self.start_cb.isChecked())
        configure_startup(self.start_cb.isChecked())
        
        self.settings.set_enabled(self.enabled_cb.isChecked())
        self.settings.set_direction_change_threshold(self.direction_change_threshold_spin.value())
        self.settings.set_strict_mode(self.strict_mode_cb.isChecked())
        self.settings.set_min_reversal_interval(self.min_reversal_spin.value())
        self.settings.set_smart_momentum(self.smart_momentum_cb.isChecked())
        self.settings.set_font_size(self.font_size_spin.value())


        # Explicitly sync settings to INI file
        self.settings.sync()

        # Apply settings live
        self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)
        self.apply_settings()
        
        self.status_label.setText("Settings saved successfully.")
        QtCore.QTimer.singleShot(3000, lambda: self.status_label.setText(""))
