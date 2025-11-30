# wheel_scroll_fixer.py
# Complete application with low-level mouse-wheel blocking, settings UI,
# tray menu, watchdog, single-instance guard, and
# an About dialog where en.MetheTech.com is a clickable link.
import sys
import winreg
import os
import subprocess
import logging
import configparser
import ctypes
import ast
import threading
import time
import tempfile
import atexit
import platform
from ctypes import wintypes

import psutil
import win32gui
import win32process
import win32con
from PyQt5 import QtWidgets, QtGui, QtCore
from app_context import AppContext
from gui import SettingsDialog, HelpDialog, AboutDialog
from utils import get_foreground_process_name

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.LPARAM),
    ]

# =========================
# Custom INI Settings Class
# =========================
class IniSettings:
    """A custom INI file settings manager."""
    def __init__(self, org_name, app_name):
        """Initializes the settings, loading from the INI file."""
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", f"{app_name}.ini")
        self.config = configparser.ConfigParser()
        self._load_settings()

    def _load_settings(self):
        """Loads settings from the INI file if it exists."""
        if os.path.exists(self.file_path):
            self.config.read(self.file_path)

    def value(self, key, default=None, type=None):
        """Retrieves a value from the settings."""
        section, option = self._parse_key(key)
        if self.config.has_option(section, option):
            val = self.config.get(section, option)
            if type == int:
                return int(val)
            elif type == float:
                return float(val)
            elif type == bool:
                return val.lower() == 'true'
            elif type == list:
                return ast.literal_eval(val) if val else [] # Safely evaluate list string
            elif type == dict:
                return ast.literal_eval(val) if val else {}
            return val
        return default

    def set_value(self, key, value):
        """Sets a value in the settings."""
        section, option = self._parse_key(key)
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        if isinstance(value, (list, dict)):
            self.config.set(section, option, repr(value))
        else:
            self.config.set(section, option, str(value))

    def _parse_key(self, key):
        """Parses a key into a section and option."""
        if '/' in key:
            parts = key.split('/')
            return parts[0], parts[1]
        return 'General', key

    def sync(self):
        """Saves the settings to the INI file atomically."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        temp_file_path = self.file_path + '.tmp'
        try:
            with open(temp_file_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            os.replace(temp_file_path, self.file_path)
        except Exception as e:
            print(f"Error saving settings: {e}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

# gui/single_instance.py
def bring_window_to_front(window_title):
    """Finds a window by its title and brings it to the foreground."""
    try:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        print(f"Error bringing window to front: {e}")
    return False

class SingleInstance:
    """
    Ensures only a single instance of the application is running using a named mutex.
    """
    def __init__(self, app_name, window_title):
        self.mutex = None
        self.mutex_name = r"Global\{app_name}_Mutex"
        self.window_title = window_title

    def acquire_lock(self):
        """
        Attempts to acquire the mutex. If it fails, another instance is running.
        """
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, True, self.mutex_name)
        if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
            print("Another instance is already running. Bringing it to the front.")
            bring_window_to_front(self.window_title)
            return False
        return True

    def release_lock(self):
        """Releases the mutex."""
        if self.mutex:
            ctypes.windll.kernel32.CloseHandle(self.mutex)
            self.mutex = None

    def __del__(self):
        self.release_lock()

# ===============
# App Settings
# ===============
class Settings(IniSettings):
    """Manages application-specific settings."""
    def __init__(self):
        super().__init__("ScrollLockApp", "Settings")

    def get_interval(self) -> float:
        return self.value("block_interval", 0.3, type=float)

    def set_interval(self, v: float):
        self.set_value("block_interval", v)

    def get_direction_change_threshold(self) -> int:
        return self.value("direction_change_threshold", 2, type=int)

    def set_direction_change_threshold(self, v: int):
        self.set_value("direction_change_threshold", v)

    def get_blacklist(self):
        return self.value("blacklist", [], type=list)

    def set_blacklist(self, v):
        self.set_value("blacklist", v)

    def get_startup(self) -> bool:
        return self.value("start_on_boot", False, type=bool)

    def set_startup(self, v: bool):
        self.set_value("start_on_boot", v)

    def get_enabled(self) -> bool:
        return self.value("enabled", True, type=bool)

    def set_enabled(self, v: bool):
        self.set_value("enabled", v)

    def get_font_size(self) -> float:
        return self.value("font_size", 10.0, type=float)

    def set_font_size(self, v: float):
        self.set_value("font_size", v)

    def get_strict_mode(self) -> bool:
        return self.value("strict_mode", True, type=bool)

    def set_strict_mode(self, v: bool):
        self.set_value("strict_mode", v)

    def get_app_profiles(self) -> dict:
        return self.value("app_profiles", {}, type=dict)

    def set_app_profiles(self, v: dict):
        self.set_value("app_profiles", v)

# ===========================
# Windows Startup Management
# ===========================
def configure_startup(enable: bool):
    """Create or remove HKCU Run entry for this script."""
    run_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    name = "ScrollLockApp"
    path = f'"{os.path.abspath(sys.executable)}" "{os.path.abspath(__file__)}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_WRITE) as key:
        if enable:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, path)
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass

# =======================
# Low-Level Mouse Hooker
# =======================
from utils import get_foreground_process_name

class MouseHook:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.block_interval = self.settings.get_interval()
        self.blacklist = self.settings.get_blacklist()
        self.app_profiles = self.settings.get_app_profiles()
        self.enabled = self.settings.get_enabled()
        self.direction_change_threshold = self.settings.get_direction_change_threshold()
        self.strict_mode = self.settings.get_strict_mode()
        self.pending_start_dir = None
        self.last_dir = None
        self.last_time = 0.0
        self._consecutive_opposite_events = 0
        self.blocked_up = 0
        self.blocked_down = 0
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.hook_id = None
        self.hook_cb = None
        self.thread_id = None

    def reload_settings(self, update_tray_icon_callback=None, update_font_callback=None):
        self.block_interval = self.settings.get_interval()
        self.blacklist = self.settings.get_blacklist()
        self.app_profiles = self.settings.get_app_profiles()
        self.enabled = self.settings.get_enabled()
        self.direction_change_threshold = self.settings.get_direction_change_threshold()
        self.strict_mode = self.settings.get_strict_mode()
        self._consecutive_opposite_events = 0
        if update_tray_icon_callback:
            update_tray_icon_callback()
        if update_font_callback:
            update_font_callback()

    def _get_current_app_settings(self):
        app_name = get_foreground_process_name()
        if app_name and app_name in self.app_profiles:
            profile = self.app_profiles[app_name]
            return profile.get('interval', self.block_interval), \
                   profile.get('threshold', self.direction_change_threshold)
        return self.block_interval, self.direction_change_threshold

    def is_blacklisted(self) -> bool:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid).name()
            return proc.lower() in (p.lower() for p in self.blacklist)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def start(self):
        self.thread_id = self.kernel32.GetCurrentThreadId()
        
        # Define LRESULT for 64-bit compatibility
        LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
        
        CMPFUNC = ctypes.WINFUNCTYPE(
            LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        )

        def hook_proc(nCode, wParam, lParam):
            if nCode == 0 and wParam == win32con.WM_MOUSEWHEEL:
                # logging.debug(f"HOOK: Event received. Enabled={self.enabled}")
                if not self.enabled:
                    return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

                if self.is_blacklisted():
                    # logging.debug("HOOK: Blacklisted app.")
                    return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

                ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                delta_short = ctypes.c_short((ms.mouseData >> 16) & 0xFFFF).value
                current_dir = 1 if delta_short > 0 else -1
                now = time.time()
                current_block_interval, current_direction_change_threshold = self._get_current_app_settings()
                
                logging.debug(f"HOOK: Delta={delta_short}, Dir={current_dir}, LastDir={self.last_dir}, TimeDiff={now - self.last_time:.4f}")

                # Check if the current session (blocking interval) has expired
                if (self.last_dir is not None) and (now - self.last_time >= current_block_interval):
                    self.last_dir = None
                    self.pending_start_dir = None
                    self._consecutive_opposite_events = 0

                if self.last_dir is None:
                    # Starting a new sequence
                    if self.strict_mode:
                        if self.pending_start_dir is None:
                            # First tick: Block and wait for confirmation
                            self.pending_start_dir = current_dir
                            self.last_time = now
                            logging.debug("HOOK: BLOCK (Strict: First Tick)")
                            return 1
                        else:
                            # Second tick: Check confirmation
                            if current_dir == self.pending_start_dir:
                                # Confirmed
                                self.last_dir = current_dir
                                self.last_time = now
                                self.pending_start_dir = None
                                logging.debug("HOOK: PASS (Strict: Confirmed)")
                                return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)
                            else:
                                # Mismatch (Glitch detected or user erratic)
                                # Treat this as a NEW First Tick
                                self.pending_start_dir = current_dir
                                self.last_time = now
                                logging.debug("HOOK: BLOCK (Strict: Mismatch Reset)")
                                return 1
                    else:
                        # Standard Mode: Allow immediately
                        self.last_dir = current_dir
                        self.last_time = now
                        self._consecutive_opposite_events = 0
                        logging.debug("HOOK: PASS (Time/First)")
                        return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

                # If we are here, last_dir is set (Active Session)
                if current_dir == self.last_dir:
                    self.last_time = now
                    self._consecutive_opposite_events = 0
                    self.pending_start_dir = None
                    logging.debug("HOOK: PASS (Same Dir)")
                    return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)
                else:
                    self._consecutive_opposite_events += 1
                    logging.debug(f"HOOK: CHECK (Opposite Dir) Count={self._consecutive_opposite_events}/{current_direction_change_threshold}")
                    if self._consecutive_opposite_events >= current_direction_change_threshold:
                        self.last_dir = current_dir
                        self.last_time = now
                        self._consecutive_opposite_events = 0
                        self.pending_start_dir = None
                        logging.debug("HOOK: PASS (Threshold Met)")
                        return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)
                    else:
                        if current_dir > 0:
                            self.blocked_up += 1
                        else:
                            self.blocked_down += 1
                        logging.debug("HOOK: BLOCK")
                        return 1

            return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        self.hook_cb = CMPFUNC(hook_proc)
        
        # Set return type for CallNextHookEx to match LRESULT
        self.user32.CallNextHookEx.restype = LRESULT
        self.user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.SetWindowsHookExA.restype = ctypes.c_void_p # HHOOK

        # For WH_MOUSE_LL, hMod should be NULL (0) if the hook proc is in the same process/thread context
        # or if we are using a low-level hook which doesn't require injection.
        # Error 126 (ERROR_MOD_NOT_FOUND) happens when we pass a module handle that isn't valid for the hook type.
        self.hook_id = self.user32.SetWindowsHookExA(
            win32con.WH_MOUSE_LL,
            self.hook_cb,
            0, # hMod must be NULL for WH_MOUSE_LL in Python usually
            0,
        )
        
        if not self.hook_id:
            error_code = self.kernel32.GetLastError()
            logging.error(f"CRITICAL ERROR: Failed to install mouse hook. Error Code: {error_code}")
        else:
            logging.info(f"SUCCESS: Mouse hook installed. Hook ID: {self.hook_id}")

        msg = wintypes.MSG()
        while True:
            b = self.user32.GetMessageA(ctypes.byref(msg), None, 0, 0)
            if b == 0:
                break
            self.user32.TranslateMessage(ctypes.byref(msg))
            self.user32.DispatchMessageA(ctypes.byref(msg))

    def stop(self):
        if self.hook_id:
            self.user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
        if self.thread_id:
            self.user32.PostThreadMessageW(self.thread_id, win32con.WM_QUIT, 0, 0)

def run_watchdog(parent_pid_str):
    """Monitors the parent process and restarts it if it crashes."""
    parent_pid = int(parent_pid_str)
    logging.basicConfig(level=logging.INFO, filename=os.path.join(tempfile.gettempdir(), 'scroll_lock_watchdog.log'), filemode='w')
    logging.info(f"Watchdog started for PID: {parent_pid}")
    time.sleep(5)
    while True:
        if not psutil.pid_exists(parent_pid):
            logging.warning(f"Parent PID {parent_pid} not found. Relaunching application.")
            subprocess.Popen(
                [sys.executable, os.path.abspath(__file__), "--no-watchdog"],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            break
        time.sleep(2)
    logging.info("Watchdog exiting.")
    sys.exit(0)

if __name__ == "__main__":
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if not is_admin():
        # Re-run the program with admin rights
        print("Requesting administrative privileges...")
        try:
            # Prepare arguments
            script = os.path.abspath(__file__)
            params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
            
            # If running as a script, we need to pass the script path to the executable (python.exe)
            # If frozen (exe), sys.executable is the program itself
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                arguments = params
            else:
                executable = sys.executable
                arguments = f'"{script}" {params}'

            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, arguments, None, 1)
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate: {e}")
            # Fallback to normal execution, though it might fail
    
    if len(sys.argv) > 2 and sys.argv[1] == "--watchdog":
        run_watchdog(sys.argv[2])
    else:
        # Configure logging to both file and console with DEBUG level
        log_file = os.path.join(tempfile.gettempdir(), 'scroll_lock_main.log')
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, mode='w'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.info(f"Logging initialized. Log file: {log_file}")
        
        app_name = "WheelScrollFixer"
        window_title = "Scroll Lock Settings"
        single_instance = SingleInstance(app_name, window_title)
        if not single_instance.acquire_lock():
            sys.exit(0)

        logging.info('Creating QApplication')
        app = QtWidgets.QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        settings = Settings()
        logging.info('Settings loaded')

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)
        icon_path = os.path.join(base_path, "mouse.ico")
        app_icon = QtGui.QIcon(icon_path)
        app.setWindowIcon(app_icon)

        def apply_global_font():
            font = QtGui.QFont()
            font.setPointSize(int(settings.get_font_size()))
            app.setFont(font)
        apply_global_font()
        logging.info('Font applied')

        app.setStyleSheet(r"""
            QWidget { font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 10pt; }
            QPushButton { background-color: #0078D7; color: white; border: 1px solid #0078D7; border-radius: 4px; padding: 6px 18px; min-width: 80px; }
            QPushButton:hover { background-color: #0056B3; border-color: #0056B3; }
            QPushButton:pressed { background-color: #003f80; border-color: #003f80; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QGroupBox { font-weight: bold; margin-top: 20px; border: 1px solid #D0D0D0; border-radius: 6px; padding-top: 25px; padding-bottom: 10px; padding-left: 10px; padding-right: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; margin-left: 2px; color: #333333; background-color: transparent; }
            QSpinBox, QDoubleSpinBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 3px; background-color: #FFFFFF; selection-background-color: #0078D7; selection-color: white; }
            QListWidget { border: 1px solid #D0D0D0; border-radius: 4px; background-color: #FFFFFF; selection-background-color: #0078D7; selection-color: white; padding: 2px; }
            QMenuBar { background-color: #f0f0f0; border-bottom: 1px solid #ccc; }
            QMenuBar::item { padding: 5px 10px; background-color: transparent; }
            QMenuBar::item:selected { background-color: #e0e0e0; }
            QMenu { background-color: #f0f0f0; border: 1px solid #ccc; }
            QMenu::item { padding: 5px 20px 5px 10px; }
            QMenu::item:selected { background-color: #0078D7; color: white; }
        """)
        logging.info('Stylesheet applied')

        if settings.get_startup() and "--no-watchdog" not in sys.argv:
            try:
                subprocess.Popen(
                    [sys.executable, os.path.abspath(__file__), "--watchdog", str(os.getpid())],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
                logging.info('Watchdog process spawned')
            except Exception as e:
                logging.error(f'Watchdog spawn failed: {e}')
                print(f"[Main] Watchdog spawn failed: {e}")

        hook = MouseHook(settings)
        logging.info('Mouse hook created')

        t = threading.Thread(target=hook.start, daemon=True)
        t.start()
        logging.info('Hook thread started')

        tray_icon = app_icon
        logging.info('Tray icon loaded')
        tray = QtWidgets.QSystemTrayIcon(tray_icon, parent=app)

        def update_tray_icon():
            tray.setIcon(tray_icon)
        update_tray_icon()
        logging.info('Tray icon updated')

        menu = QtWidgets.QMenu()
        act_settings = menu.addAction("Settings")
        act_toggle_enabled = menu.addAction("Toggle Scroll Blocking")
        act_help = menu.addAction("Help")
        act_about = menu.addAction("About")
        menu.addSeparator()
        act_exit = menu.addAction("Exit")
        tray.setContextMenu(menu)
        tray.setToolTip("WheelScrollFixer")
        tray.show()
        logging.info('Tray icon shown')

        app_context = AppContext(settings, hook, update_tray_icon, apply_global_font, tray, tray_icon)
        dlg = SettingsDialog(app_context, configure_startup)
        act_settings.triggered.connect(dlg.show)
        logging.info('Settings dialog created')

        act_settings.setWhatsThis("Open the Settings window to configure blocking and UI options.")
        act_toggle_enabled.setWhatsThis("Enable/disable scroll blocking globally.")
        act_help.setWhatsThis("Open the Help dialog.")
        act_about.setWhatsThis("Open the About dialog.")
        act_exit.setWhatsThis("Quit the application.")

        def toggle_enabled_from_tray():
            current_state = settings.get_enabled()
            settings.set_enabled(not current_state)
            hook.reload_settings(update_tray_icon, apply_global_font)
            update_tray_icon()
            QtWidgets.QMessageBox.information(
                None, "Scroll Blocking", f"Scroll blocking is now: {'Enabled' if not current_state else 'Disabled'}.",
            )
        act_toggle_enabled.triggered.connect(toggle_enabled_from_tray)

        def show_help_dialog():
            HelpDialog(dlg).exec_()
        def show_about_dialog():
            AboutDialog(dlg).exec_()
        def exit_app():
            hook.stop()
            app.quit()

        act_help.triggered.connect(show_help_dialog)
        act_about.triggered.connect(show_about_dialog)
        act_exit.triggered.connect(exit_app)

        dlg.show()
        logging.info('Settings dialog shown')

        def restore_window(reason):
            if reason == QtWidgets.QSystemTrayIcon.Trigger:
                dlg.showNormal()
                dlg.activateWindow()
        tray.activated.connect(restore_window)

        def on_about_to_quit():
            logging.info('Application quitting')
            settings.sync()
        app.aboutToQuit.connect(on_about_to_quit)

        logging.info('Starting event loop')
        sys.exit(app.exec_())