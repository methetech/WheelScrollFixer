"""Settings dialog for the WheelScrollFixer application."""
import os
import sys
from utils import get_foreground_process_name
from PyQt5 import QtWidgets, QtGui, QtCore
from .app_profile_dialog import AppProfileDialog
from .help_dialog import HelpDialog
from .about_dialog import AboutDialog
from .calibration_wizard import CalibrationWizardDialog
from localization import translator

class ModernSettingsDialog(QtWidgets.QDialog):
    """The main settings dialog for the application, redesigned."""
    
    # Signal emitted when the language changes
    languageChanged = QtCore.pyqtSignal()

    def __init__(self, app_context, configure_startup):
        super().__init__()
        self.app_context = app_context
        self.settings = app_context.settings
        self.hook = app_context.hook
        self.update_tray_icon_callback = app_context.update_tray_icon_callback
        self.update_font_callback = app_context.update_font_callback
        self.tray = app_context.tray

        self.configure_startup = configure_startup
        
        self._init_ui()

    def _init_ui(self):
        """Initializes the user interface."""
        self.setWindowTitle('Scroll Lock Settings')
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "..", "mouse.ico")))
        
        # Load geometry or set default
        self.qt_settings = QtCore.QSettings("MetheTech", "WheelScrollFixer")
        if self.qt_settings.value("geometry"):
            self.restoreGeometry(self.qt_settings.value("geometry"))
        else:
            self.resize(1300, 750) # Default wide size

        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
            QLabel { color: #e0e0e0; }
            QGroupBox { border: 1px solid #3d3d3d; border-radius: 6px; margin-top: 24px; background-color: #252525; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; color: #3a7bd5; font-weight: bold; }
            
            /* Sidebar */
            QListWidget#sidebar { background-color: #2a2a2a; border: none; border-right: 1px solid #333; outline: none; font-size: 12pt; }
            QListWidget#sidebar::item { padding: 20px; color: #aaaaaa; border-left: 5px solid transparent; margin-bottom: 2px; }
            QListWidget#sidebar::item:selected { background-color: #333333; color: #ffffff; border-left: 5px solid #3a7bd5; }
            QListWidget#sidebar::item:hover { background-color: #2d2d2d; }

            /* Buttons */
            QPushButton { background-color: #3d3d3d; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; font-size: 10pt; }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton:pressed { background-color: #2d2d2d; }
            QPushButton#primary { background-color: #3a7bd5; }
            QPushButton#primary:hover { background-color: #3a60d5; }
            QPushButton#danger { background-color: #d32f2f; }
            
            /* Inputs */
            QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background-color: #333; border: 1px solid #444; border-radius: 4px; padding: 6px; color: #fff; font-size: 10pt; min-height: 20px; }
            QComboBox::drop-down { border: none; }
            
            /* Checkbox */
            QCheckBox { spacing: 8px; color: #eee; font-size: 10pt; }
            QCheckBox::indicator { width: 20px; height: 20px; border: 1px solid #555; border-radius: 3px; background: #333; }
            QCheckBox::indicator:checked { background-color: #3a7bd5; border-color: #3a7bd5; }
            
            /* Scrollbar */
            QScrollBar:vertical { border: none; background: #1e1e1e; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 5px; }
        """)

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QtWidgets.QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(450) # FIXED WIDE WIDTH
        self.sidebar.addItems([
            "   🎚️  " + translator.tr("tab_sensitivity"), 
            "   🚀  " + translator.tr("tab_apps"),
            "   ⚙️  " + translator.tr("tab_general")
        ])
        self.sidebar.currentRowChanged.connect(self.change_page)
        self.main_layout.addWidget(self.sidebar)

        # --- Content Area ---
        self.content_area = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        self.content_layout.setSpacing(20)
        
        # Header
        self.header_layout = QtWidgets.QHBoxLayout()
        self.page_title = QtWidgets.QLabel("")
        self.page_title.setStyleSheet("font-size: 22pt; font-weight: bold; color: #fff;")
        
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItem("English 🇺🇸", "en")
        self.lang_combo.addItem("Türkçe 🇹🇷", "tr")
        self.lang_combo.setFixedWidth(140)
        # Set current language
        idx = self.lang_combo.findData(self.settings.get_language())
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self.change_language)

        self.header_layout.addWidget(self.page_title)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.lang_combo)
        self.content_layout.addLayout(self.header_layout)
        
        # Divider
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setStyleSheet("background-color: #333;")
        self.content_layout.addWidget(line)

        # Stacked Pages
        self.pages = QtWidgets.QStackedWidget()
        self._create_widgets_and_pages()
        self.content_layout.addWidget(self.pages)

        # Footer
        self.footer_layout = QtWidgets.QHBoxLayout()
        
        self.defaults_btn = QtWidgets.QPushButton("")
        self.defaults_btn.clicked.connect(self.restore_defaults)
        self.defaults_btn.setMinimumHeight(40)
        
        self.save_btn = QtWidgets.QPushButton("")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(lambda: self.save(self.configure_startup))
        self.save_btn.setMinimumWidth(150)
        self.save_btn.setMinimumHeight(40)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")

        self.footer_layout.addWidget(self.defaults_btn)
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.status_label)
        self.footer_layout.addSpacing(15)
        self.footer_layout.addWidget(self.save_btn)
        
        self.content_layout.addLayout(self.footer_layout)
        self.main_layout.addWidget(self.content_area)

        # Select first page
        self.sidebar.setCurrentRow(0)
        
        # Initial Translation
        self.retranslate_ui()

    def _create_widgets_and_pages(self):
        # --- Page 1: Sensitivity ---
        page_sen = QtWidgets.QWidget()
        layout_sen = QtWidgets.QVBoxLayout(page_sen)
        layout_sen.setAlignment(QtCore.Qt.AlignTop)
        layout_sen.setSpacing(20)
        
        self.calib_btn = QtWidgets.QPushButton("")
        self.calib_btn.setObjectName("primary")
        self.calib_btn.setStyleSheet("font-size: 12pt; padding: 15px; background-color: #673AB7;")
        self.calib_btn.clicked.connect(self.run_calibration_wizard)
        
        grp_logic = QtWidgets.QGroupBox("")
        self.grp_logic = grp_logic
        form_logic = QtWidgets.QFormLayout()
        form_logic.setSpacing(15)
        form_logic.setContentsMargins(15, 25, 15, 15)
        
        self.interval_spin = QtWidgets.QDoubleSpinBox()
        self.interval_spin.setRange(0.05, 5.0)
        self.interval_spin.setValue(self.settings.get_interval())
        self.interval_lbl = QtWidgets.QLabel("")
        
        self.threshold_spin = QtWidgets.QSpinBox()
        self.threshold_spin.setRange(1, 10)
        self.threshold_spin.setValue(self.settings.get_direction_change_threshold())
        self.threshold_lbl = QtWidgets.QLabel("")
        
        self.reversal_spin = QtWidgets.QDoubleSpinBox()
        self.reversal_spin.setRange(0.01, 0.20)
        self.reversal_spin.setValue(self.settings.get_min_reversal_interval())
        self.reversal_lbl = QtWidgets.QLabel("")
        
        form_logic.addRow(self.interval_lbl, self.interval_spin)
        form_logic.addRow(self.threshold_lbl, self.threshold_spin)
        form_logic.addRow(self.reversal_lbl, self.reversal_spin)
        grp_logic.setLayout(form_logic)
        
        grp_adv = QtWidgets.QGroupBox("")
        self.grp_adv = grp_adv
        layout_adv = QtWidgets.QVBoxLayout()
        layout_adv.setContentsMargins(15, 25, 15, 15)
        layout_adv.setSpacing(10)
        self.strict_cb = QtWidgets.QCheckBox("")
        self.strict_cb.setChecked(self.settings.get_strict_mode())
        self.smart_cb = QtWidgets.QCheckBox("")
        self.smart_cb.setChecked(self.settings.get_smart_momentum())
        layout_adv.addWidget(self.strict_cb)
        layout_adv.addWidget(self.smart_cb)
        grp_adv.setLayout(layout_adv)

        layout_sen.addWidget(self.calib_btn)
        layout_sen.addWidget(grp_logic)
        layout_sen.addWidget(grp_adv)
        self.pages.addWidget(page_sen)

        # --- Page 2: Apps ---
        page_apps = QtWidgets.QWidget()
        layout_apps = QtWidgets.QVBoxLayout(page_apps)
        
        # Application Control Group
        grp_app = QtWidgets.QGroupBox("")
        self.grp_app = grp_app
        layout_grp_app = QtWidgets.QVBoxLayout()
        layout_grp_app.setContentsMargins(15, 25, 15, 15)

        # Blacklist
        self.lbl_bl = QtWidgets.QLabel("")
        self.bl_list = QtWidgets.QListWidget()
        self.bl_list.addItems(self.settings.get_blacklist())
        self.bl_list.setFixedHeight(120)
        
        bl_btns = QtWidgets.QHBoxLayout()
        self.btn_bl_add = QtWidgets.QPushButton("")
        self.btn_bl_add.clicked.connect(self.add_current_app_to_blacklist)
        self.btn_bl_rem = QtWidgets.QPushButton("")
        self.btn_bl_rem.clicked.connect(self.remove_selected_from_blacklist)
        self.btn_bl_clr = QtWidgets.QPushButton("")
        self.btn_bl_clr.clicked.connect(self.clear_blacklist)
        bl_btns.addWidget(self.btn_bl_add)
        bl_btns.addWidget(self.btn_bl_rem)
        bl_btns.addWidget(self.btn_bl_clr)
        
        # Profiles
        self.lbl_prof = QtWidgets.QLabel("")
        self.prof_list = QtWidgets.QListWidget()
        self.prof_list.setFixedHeight(120)
        self.refresh_app_profiles_list()
        
        prof_btns = QtWidgets.QHBoxLayout()
        self.btn_prof_add = QtWidgets.QPushButton("")
        self.btn_prof_add.clicked.connect(self.add_app_profile)
        self.btn_prof_edit = QtWidgets.QPushButton("")
        self.btn_prof_edit.clicked.connect(self.edit_app_profile)
        self.btn_prof_rem = QtWidgets.QPushButton("")
        self.btn_prof_rem.clicked.connect(self.remove_app_profile)
        prof_btns.addWidget(self.btn_prof_add)
        prof_btns.addWidget(self.btn_prof_edit)
        prof_btns.addWidget(self.btn_prof_rem)

        layout_grp_app.addWidget(self.lbl_bl)
        layout_grp_app.addWidget(self.bl_list)
        layout_grp_app.addLayout(bl_btns)
        layout_grp_app.addSpacing(20)
        layout_grp_app.addWidget(self.lbl_prof)
        layout_grp_app.addWidget(self.prof_list)
        layout_grp_app.addLayout(prof_btns)
        
        grp_app.setLayout(layout_grp_app)
        layout_apps.addWidget(grp_app)
        self.pages.addWidget(page_apps)

        # --- Page 3: General ---
        page_gen = QtWidgets.QWidget()
        layout_gen = QtWidgets.QVBoxLayout(page_gen)
        layout_gen.setAlignment(QtCore.Qt.AlignTop)
        
        grp_sys = QtWidgets.QGroupBox("")
        self.grp_sys = grp_sys
        form_gen = QtWidgets.QVBoxLayout()
        form_gen.setContentsMargins(15, 25, 15, 15)
        form_gen.setSpacing(15)
        
        self.enabled_cb = QtWidgets.QCheckBox('')
        self.enabled_cb.setChecked(self.settings.get_enabled())
        
        self.start_cb = QtWidgets.QCheckBox("")
        self.start_cb.setChecked(self.settings.get_startup())
        
        self.font_layout = QtWidgets.QHBoxLayout()
        self.font_lbl = QtWidgets.QLabel("")
        self.font_spin = QtWidgets.QDoubleSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setValue(self.settings.get_font_size())
        self.font_layout.addWidget(self.font_lbl)
        self.font_layout.addWidget(self.font_spin)
        self.font_layout.addStretch()

        form_gen.addWidget(self.enabled_cb)
        form_gen.addWidget(self.start_cb)
        form_gen.addLayout(self.font_layout)
        grp_sys.setLayout(form_gen)
        
        # Info / Links
        grp_info = QtWidgets.QGroupBox("")
        self.grp_info = grp_info
        layout_info = QtWidgets.QHBoxLayout()
        layout_info.setContentsMargins(15, 25, 15, 15)
        
        self.btn_web = QtWidgets.QPushButton("")
        self.btn_web.clicked.connect(self.open_website)
        self.btn_help = QtWidgets.QPushButton("")
        self.btn_help.clicked.connect(self.show_help_dialog)
        self.btn_about = QtWidgets.QPushButton("")
        self.btn_about.clicked.connect(self.show_about_dialog)
        layout_info.addWidget(self.btn_web)
        layout_info.addWidget(self.btn_help)
        layout_info.addWidget(self.btn_about)
        grp_info.setLayout(layout_info)

        layout_gen.addWidget(grp_sys)
        layout_gen.addSpacing(20)
        layout_gen.addWidget(grp_info)
        self.pages.addWidget(page_gen)

    def change_page(self, row):
        self.pages.setCurrentIndex(row)
        titles = [translator.tr("tab_sensitivity"), translator.tr("tab_apps"), translator.tr("tab_general")]
        if row < len(titles):
            self.page_title.setText(titles[row])

    def change_language(self):
        lang_code = self.lang_combo.currentData()
        translator.set_language(lang_code)
        self.settings.set_language(lang_code)
        self.retranslate_ui()
        # Emit signal so main app can update tray menu
        self.languageChanged.emit()

    def retranslate_ui(self):
        tr = translator.tr
        self.setWindowTitle(tr("window_title"))
        
        # Sidebar items
        self.sidebar.item(0).setText("   🎚️  " + tr("tab_sensitivity"))
        self.sidebar.item(1).setText("   🚀  " + tr("tab_apps"))
        self.sidebar.item(2).setText("   ⚙️  " + tr("tab_general"))
        
        # Page Title update
        current_titles = [tr("tab_sensitivity"), tr("tab_apps"), tr("tab_general")]
        self.page_title.setText(current_titles[self.pages.currentIndex()])

        # --- Page 1: Sensitivity ---
        self.calib_btn.setText("  " + tr("btn_calibration") + "  ")
        self.grp_logic.setTitle(tr("grp_blocking"))
        self.interval_lbl.setText(tr("lbl_interval"))
        self.interval_spin.setToolTip(tr("tip_interval"))
        self.threshold_lbl.setText(tr("lbl_threshold"))
        self.threshold_spin.setToolTip(tr("tip_threshold"))
        self.reversal_lbl.setText(tr("lbl_min_reversal"))
        self.reversal_spin.setToolTip(tr("tip_min_reversal"))
        self.grp_adv.setTitle(tr("grp_adv_features"))
        self.strict_cb.setText(tr("chk_strict"))
        self.strict_cb.setToolTip(tr("tip_strict"))
        self.smart_cb.setText(tr("chk_smart"))
        self.smart_cb.setToolTip(tr("tip_smart"))
        
        # --- Page 2: Apps ---
        self.grp_app.setTitle(tr("grp_app_control"))
        self.lbl_bl.setText(tr("lbl_blacklist"))
        self.btn_bl_add.setText(tr("btn_add_current"))
        self.btn_bl_rem.setText(tr("btn_remove_selected"))
        self.btn_bl_clr.setText(tr("btn_clear_all"))
        self.lbl_prof.setText(tr("lbl_profiles"))
        self.btn_prof_add.setText(tr("btn_add_profile"))
        self.btn_prof_edit.setText(tr("btn_edit_profile"))
        self.btn_prof_rem.setText(tr("btn_remove_profile"))

        # --- Page 3: General ---
        self.grp_sys.setTitle(tr("grp_system"))
        self.enabled_cb.setText(tr("chk_enable"))
        self.enabled_cb.setToolTip(tr("tip_enable"))
        self.start_cb.setText(tr("chk_start_boot"))
        self.start_cb.setToolTip(tr("tip_start_boot"))
        self.font_lbl.setText(tr("lbl_font_size"))
        self.grp_info.setTitle(tr("grp_info"))
        self.btn_web.setText(tr("btn_website"))
        self.btn_help.setText(tr("tray_help"))
        self.btn_about.setText(tr("tray_about"))
        
        # Footer
        self.defaults_btn.setText(tr("btn_defaults"))
        self.save_btn.setText(tr("btn_save"))

    # --- Logic Methods ---
    def save(self, configure_startup):
        self.settings.set_interval(self.interval_spin.value())
        bl = [self.bl_list.item(i).text() for i in range(self.bl_list.count())]
        self.settings.set_blacklist(bl)
        self.settings.set_startup(self.start_cb.isChecked())
        configure_startup(self.start_cb.isChecked())
        self.settings.set_enabled(self.enabled_cb.isChecked())
        self.settings.set_direction_change_threshold(self.threshold_spin.value())
        self.settings.set_strict_mode(self.strict_cb.isChecked())
        self.settings.set_min_reversal_interval(self.reversal_spin.value())
        self.settings.set_smart_momentum(self.smart_cb.isChecked())
        self.settings.set_font_size(self.font_spin.value())
        self.settings.sync()
        self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)
        self.apply_settings()
        self.status_label.setText(translator.tr("status_saved"))
        QtCore.QTimer.singleShot(3000, lambda: self.status_label.setText(""))

    def restore_defaults(self):
        reply = QtWidgets.QMessageBox.question(self, translator.tr("msg_reset_title"), translator.tr("msg_reset_text"), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.interval_spin.setValue(0.30)
            self.threshold_spin.setValue(2)
            self.strict_cb.setChecked(True)
            self.reversal_spin.setValue(0.05)
            self.smart_cb.setChecked(True)
            self.enabled_cb.setChecked(True)
            self.resize(1200, 700) # Reset size
            self.save_btn.click()
            self.status_label.setText(translator.tr("status_restored"))

    def refresh_app_profiles_list(self):
        self.prof_list.clear()
        for app_name, profile in self.settings.get_app_profiles().items():
            interval = profile.get('interval', self.settings.get_interval())
            threshold = profile.get('threshold', self.settings.get_direction_change_threshold())
            self.prof_list.addItem(f"{app_name}: Interval={interval:.2f}s, Threshold={threshold}")

    def add_app_profile(self):
        dialog = AppProfileDialog(parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            data = dialog.get_profile_data()
            app_name = data['app_name'].lower()
            if not app_name: return
            profiles = self.settings.get_app_profiles()
            profiles[app_name] = {'interval': data['interval'], 'threshold': data['threshold']}
            self.settings.set_app_profiles(profiles)
            self.refresh_app_profiles_list()
            self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)

    def edit_app_profile(self):
        sel = self.prof_list.selectedItems()
        if not sel: return
        item_text = sel[0].text()
        app_name_raw = item_text.split(':')[0].strip()
        app_name = app_name_raw.lower()
        profiles = self.settings.get_app_profiles()
        profile_data = profiles.get(app_name, {})
        dialog = AppProfileDialog(current_app_name=app_name_raw, current_interval=profile_data.get('interval', 0.3), current_threshold=profile_data.get('threshold', 2), parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            data = dialog.get_profile_data()
            new_app_name = data['app_name'].lower()
            if not new_app_name: return
            if new_app_name != app_name: del profiles[app_name]
            profiles[new_app_name] = {'interval': data['interval'], 'threshold': data['threshold']}
            self.settings.set_app_profiles(profiles)
            self.refresh_app_profiles_list()
            self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)

    def remove_app_profile(self):
        sel = self.prof_list.selectedItems()
        if not sel: return
        if QtWidgets.QMessageBox.question(self, translator.tr("msg_input_error"), translator.tr("msg_confirm_removal"), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            profiles = self.settings.get_app_profiles()
            for item in sel:
                app = item.text().split(':')[0].strip().lower()
                if app in profiles: del profiles[app]
            self.settings.set_app_profiles(profiles)
            self.refresh_app_profiles_list()
            self.hook.reload_settings(self.update_tray_icon_callback, self.update_font_callback)

    def add_current_app_to_blacklist(self):
        self.hide()
        QtCore.QTimer.singleShot(120, self._get_and_add_foreground_app)

    def _get_and_add_foreground_app(self):
        proc_name = get_foreground_process_name()
        existing = [self.bl_list.item(i).text() for i in range(self.bl_list.count())]
        if proc_name and proc_name not in existing: self.bl_list.addItem(proc_name)
        self.show()

    def remove_selected_from_blacklist(self):
        for item in self.bl_list.selectedItems(): self.bl_list.takeItem(self.bl_list.row(item))

    def clear_blacklist(self):
        self.bl_list.clear()

    def open_website(self): QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://en.MetheTech.com"))
    def show_help_dialog(self): HelpDialog(self).exec_()
    def show_about_dialog(self): AboutDialog(self).exec_()
    def apply_settings(self): self.update_font_callback()
    
    def run_calibration_wizard(self):
        wizard = CalibrationWizardDialog(self)
        self.hook.set_calibration_callback(wizard.process_scroll_event)
        result = wizard.exec_()
        self.hook.set_calibration_callback(None)
        if result == QtWidgets.QDialog.Accepted:
            results = wizard.get_results()
            if results:
                self.interval_spin.setValue(results['interval'])
                self.threshold_spin.setValue(results['threshold'])
                self.strict_cb.setChecked(results['strict'])
                self.reversal_spin.setValue(results['min_reversal'])
                self.smart_cb.setChecked(results['smart'])
                self.save_btn.click()
                QtWidgets.QMessageBox.information(self, translator.tr("msg_calib_complete"), translator.tr("msg_calib_text"))

    def minimize_to_tray(self): self.hide()
    def closeEvent(self, event): 
        self.qt_settings.setValue("geometry", self.saveGeometry())
        self.hide()
        event.ignore()

# Aliasing for compatibility
SettingsDialog = ModernSettingsDialog