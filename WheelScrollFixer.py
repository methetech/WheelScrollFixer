# wheel_scroll_fixer.py
# Complete application with low-level mouse-wheel blocking, settings UI,
# tray menu, watchdog, single-instance guard, and
# an About dialog where en.MetheTech.com is a clickable link.
import sys
import winreg
import os
import subprocess
import logging
import json
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
from localization import translator

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.LPARAM),
    ]

# =========================
# Modern JSON Settings Class
# =========================
class JsonSettings:
    """A modern JSON file settings manager with INI migration support."""
    def __init__(self, app_name):
        """Initializes the settings, loading from JSON (or migrating from INI)."""
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        self.config_dir = os.path.join(base_path, "config")
        self.json_path = os.path.join(self.config_dir, f"{app_name}.json")
        self.ini_path = os.path.join(self.config_dir, f"{app_name}.ini")
        
        self.data = {}
        self._load_settings()

    def _load_settings(self):
        """Loads settings from JSON. Migrates from INI if JSON is missing."""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load JSON settings: {e}")
                self.data = {}
        elif os.path.exists(self.ini_path):
            logging.info("Migrating legacy INI settings to JSON...")
            self._migrate_from_ini()

    def _migrate_from_ini(self):
        """Migrates data from the legacy INI file to the new JSON format."""
        try:
            config = configparser.ConfigParser()
            config.read(self.ini_path)
            
            new_data = {}
            for section in config.sections():
                new_data[section] = {}
                for key, val in config.items(section):
                    # Attempt to convert types using ast.literal_eval
                    try:
                        # Only eval if it looks like a structure or number
                        if val.lower() in ['true', 'false']:
                            val_conv = (val.lower() == 'true')
                        else:
                            try:
                                val_conv = ast.literal_eval(val)
                            except (ValueError, SyntaxError):
                                val_conv = val
                        new_data[section][key] = val_conv
                    except Exception:
                        new_data[section][key] = val
            
            self.data = new_data
            self.sync() # Save as JSON
            
            # Rename old INI to .bak
            try:
                os.rename(self.ini_path, self.ini_path + ".bak")
                logging.info("Migration successful. Legacy INI renamed to .bak.")
            except OSError:
                pass
        except Exception as e:
            logging.error(f"Migration failed: {e}")

    def value(self, key, default=None, type=None):
        """Retrieves a value from the settings."""
        section, option = self._parse_key(key)
        val = self.data.get(section, {}).get(option, default)
        
        # JSON usually preserves types, but we ensure basic consistency if requested
        if val is None:
            return default
            
        if type == int:
            return int(val)
        elif type == float:
            return float(val)
        elif type == bool:
            if isinstance(val, str):
                return val.lower() == 'true'
            return bool(val)
        elif type == list:
            return val if isinstance(val, list) else []
        elif type == dict:
            return val if isinstance(val, dict) else {}
            
        return val

    def set_value(self, key, value):
        """Sets a value in the settings."""
        section, option = self._parse_key(key)
        if section not in self.data:
            self.data[section] = {}
        self.data[section][option] = value

    def _parse_key(self, key):
        """Parses a key into a section and option."""
        if '/' in key:
            parts = key.split('/')
            return parts[0], parts[1]
        return 'General', key

    def sync(self):
        """Saves the settings to the JSON file atomically."""
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        temp_file_path = self.json_path + '.tmp'
        try:
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
            os.replace(temp_file_path, self.json_path)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
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
class Settings(JsonSettings):
    """Manages application-specific settings using JSON backend."""
    def __init__(self):
        super().__init__("WheelScrollFixer")

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

    def get_min_reversal_interval(self) -> float:
        return self.value("min_reversal_interval", 0.05, type=float)

    def set_min_reversal_interval(self, v: float):
        self.set_value("min_reversal_interval", v)

    def get_smart_momentum(self) -> bool:
        return self.value("smart_momentum", True, type=bool)

    def set_smart_momentum(self, v: bool):
        self.set_value("smart_momentum", v)

    def get_app_profiles(self) -> dict:
        return self.value("app_profiles", {}, type=dict)

    def set_app_profiles(self, v: dict):
        self.set_value("app_profiles", v)
        
    def get_language(self) -> str:
        return self.value("language", "en", type=str)

    def set_language(self, v: str):
        self.set_value("language", v)

# ===========================
# Windows Startup Management
# ===========================
def configure_startup(enable: bool):
    """
    Create or remove HKCU Run entry for this script.
    Returns True if successful, False if failed (e.g. permission denied).
    """
    run_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    name = "ScrollLockApp"
    
    if getattr(sys, 'frozen', False):
        # If frozen (exe), point to the executable itself
        path = f'"{os.path.abspath(sys.executable)}"'
    else:
        # If script, point to python interpreter + script
        path = f'"{os.path.abspath(sys.executable)}" "{os.path.abspath(__file__)}"'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_WRITE) as key:
            if enable:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, path)
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
        return True
    except OSError as e:
        logging.error(f"Failed to configure startup (Permission/AV block?): {e}")
        return False

# =======================
# Low-Level Mouse Hooker
# =======================
from utils import get_foreground_process_name

class MouseHook:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.hook_id = None
        self.hook_cb = None
        self.thread_id = None
        self.calibration_callback = None
        
        # Caching for process name
        self.last_hwnd = None
        self.last_app_name = None

        # Logic State
        self.pending_start_dir = None
        self.last_dir = None
        self.last_time = 0.0
        self._consecutive_opposite_events = 0
        self.blocked_up = 0
        self.blocked_down = 0

        # Thread-Safe Config Snapshot (Atomic Swap)
        self.config_snapshot = {}
        self.reload_settings()

    def set_calibration_callback(self, callback):
        """Sets a callback function to receive raw scroll events for calibration."""
        self.calibration_callback = callback

    def reload_settings(self, update_tray_icon_callback=None, update_font_callback=None):
        """
        Loads all settings into a dictionary and atomically swaps the reference.
        This ensures the hook thread always sees a consistent state without locks.
        """
        new_config = {
            'interval': self.settings.get_interval(),
            'blacklist': [x.lower() for x in self.settings.get_blacklist()],
            'app_profiles': self.settings.get_app_profiles(),
            'enabled': self.settings.get_enabled(),
            'threshold': self.settings.get_direction_change_threshold(),
            'strict': self.settings.get_strict_mode(),
            'min_reversal': self.settings.get_min_reversal_interval(),
            'smart': self.settings.get_smart_momentum(),
        }
        
        # Atomic assignment in Python (GIL ensures this is safe for single ref swap)
        self.config_snapshot = new_config
        
        self._consecutive_opposite_events = 0
        
        if update_tray_icon_callback:
            update_tray_icon_callback()
        if update_font_callback:
            update_font_callback()

    def _get_foreground_app_name(self):
        """Efficiently retrieves the foreground app name using caching."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd != self.last_hwnd:
                self.last_hwnd = hwnd
                # Only fetch from psutil if the window handle changed
                self.last_app_name = get_foreground_process_name()
            return self.last_app_name
        except Exception:
            return None

    def _get_current_app_settings(self, app_name, cfg):
        """Resolves settings for the specific app from the config snapshot."""
        if app_name and app_name in cfg['app_profiles']:
            profile = cfg['app_profiles'][app_name]
            return profile.get('interval', cfg['interval']), \
                   profile.get('threshold', cfg['threshold'])
        return cfg['interval'], cfg['threshold']

    def is_blacklisted(self, app_name, cfg) -> bool:
        if not app_name:
            return False
        # Blacklist is already lowercased in reload_settings
        return app_name.lower() in cfg['blacklist']

    def start(self):
        self.thread_id = self.kernel32.GetCurrentThreadId()
        
        # Define LRESULT for 64-bit compatibility
        LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
        
        CMPFUNC = ctypes.WINFUNCTYPE(
            LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        )

        def hook_proc(nCode, wParam, lParam):
            try:
                if nCode == 0 and wParam == win32con.WM_MOUSEWHEEL:
                    # 1. ATOMIC SNAPSHOT: Grab reference to current config
                    cfg = self.config_snapshot

                    ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    delta_short = ctypes.c_short((ms.mouseData >> 16) & 0xFFFF).value
                    current_dir = 1 if delta_short > 0 else -1
                    now = time.time()

                    # --- CALIBRATION MODE ---
                    if self.calibration_callback:
                        self.calibration_callback(now, current_dir)
                        return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

                    if not cfg['enabled']:
                        return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

                    # --- PERFORMANCE OPTIMIZATION ---
                    current_app_name = self._get_foreground_app_name()

                    if self.is_blacklisted(current_app_name, cfg):
                        return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

                    current_block_interval, current_direction_change_threshold = self._get_current_app_settings(current_app_name, cfg)
                    
                    time_diff = now - self.last_time
                    
                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                        logging.debug(f"HOOK: Delta={delta_short}, Dir={current_dir}, LastDir={self.last_dir}, TimeDiff={time_diff:.4f}")

                    # --- PHYSICS CHECK (The "Impossible Speed" Filter) ---
                    if (self.last_dir is not None) and (current_dir != self.last_dir) and (time_diff < cfg['min_reversal']):
                        if logging.getLogger().isEnabledFor(logging.DEBUG):
                            logging.debug(f"HOOK: PHYSICS BLOCK (Impossible Reversal: {time_diff:.4f}s < {cfg['min_reversal']}s)")
                        return 1

                    # Check if the current session (blocking interval) has expired
                    if (self.last_dir is not None) and (time_diff >= current_block_interval):
                        self.last_dir = None
                        self.pending_start_dir = None
                        self._consecutive_opposite_events = 0

                    if self.last_dir is None:
                        # Starting a new sequence
                        if cfg['strict']:
                            if self.pending_start_dir is None:
                                # First tick: Block and wait for confirmation
                                self.pending_start_dir = current_dir
                                self.last_time = now
                                if logging.getLogger().isEnabledFor(logging.DEBUG):
                                    logging.debug("HOOK: BLOCK (Strict: First Tick)")
                                return 1
                            else:
                                # Second tick: Check confirmation
                                if current_dir == self.pending_start_dir:
                                    # Confirmed
                                    self.last_dir = current_dir
                                    self.last_time = now
                                    self.pending_start_dir = None
                                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                                        logging.debug("HOOK: PASS (Strict: Confirmed)")
                                    return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)
                                else:
                                    # Mismatch (Glitch detected or user erratic)
                                    # Treat this as a NEW First Tick
                                    self.pending_start_dir = current_dir
                                    self.last_time = now
                                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                                        logging.debug("HOOK: BLOCK (Strict: Mismatch Reset)")
                                    return 1
                        else:
                            # Standard Mode: Allow immediately
                            self.last_dir = current_dir
                            self.last_time = now
                            self._consecutive_opposite_events = 0
                            if logging.getLogger().isEnabledFor(logging.DEBUG):
                                logging.debug("HOOK: PASS (Time/First)")
                            return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

                    # If we are here, last_dir is set (Active Session)
                    if current_dir == self.last_dir:
                        self.last_time = now
                        self._consecutive_opposite_events = 0
                        self.pending_start_dir = None
                        if logging.getLogger().isEnabledFor(logging.DEBUG):
                            logging.debug("HOOK: PASS (Same Dir)")
                        return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)
                    else:
                        self._consecutive_opposite_events += 1
                        
                        # --- MOMENTUM CHECK (Smart Threshold) ---
                        dynamic_threshold = current_direction_change_threshold
                        
                        if cfg['smart']:
                            if time_diff < 0.10: # Very Fast (< 100ms)
                                dynamic_threshold += 2
                            elif time_diff < 0.20: # Fast (< 200ms)
                                dynamic_threshold += 1

                        if logging.getLogger().isEnabledFor(logging.DEBUG):
                            logging.debug(f"HOOK: CHECK (Opposite Dir) dt={time_diff:.4f}s | Count={self._consecutive_opposite_events}/{dynamic_threshold}")

                        if self._consecutive_opposite_events >= dynamic_threshold:
                            self.last_dir = current_dir
                            self.last_time = now
                            self._consecutive_opposite_events = 0
                            self.pending_start_dir = None
                            if logging.getLogger().isEnabledFor(logging.DEBUG):
                                logging.debug("HOOK: PASS (Threshold Met)")
                            return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)
                        else:
                            if current_dir > 0:
                                self.blocked_up += 1
                            else:
                                self.blocked_down += 1
                            if logging.getLogger().isEnabledFor(logging.DEBUG):
                                logging.debug("HOOK: BLOCK")
                            return 1
            except Exception as e:
                logging.critical(f"HOOK EXCEPTION: {e}", exc_info=True)
                # Fallback to standard behavior to not freeze mouse
                return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

            return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        self.hook_cb = CMPFUNC(hook_proc)
        
        # Set return type for CallNextHookEx to match LRESULT
        self.user32.CallNextHookEx.restype = LRESULT
        self.user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.SetWindowsHookExA.restype = ctypes.c_void_p # HHOOK

        # For WH_MOUSE_LL, hMod should be NULL (0) if the hook proc is in the same process/thread context
        self.hook_id = self.user32.SetWindowsHookExA(
            win32con.WH_MOUSE_LL,
            self.hook_cb,
            0, 
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
            # Fallback to normal execution
    
    if len(sys.argv) > 2 and sys.argv[1] == "--watchdog":
        run_watchdog(sys.argv[2])
    else:
        # Configure logging to both file and console with INFO level
        log_file = os.path.join(tempfile.gettempdir(), 'scroll_lock_main.log')
        logging.basicConfig(
            level=logging.INFO,
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

        # Load Language
        translator.set_language(settings.get_language())

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

        watchdog_process = None
        if settings.get_startup() and "--no-watchdog" not in sys.argv:
            try:
                watchdog_process = subprocess.Popen(
                    [sys.executable, os.path.abspath(__file__), "--watchdog", str(os.getpid())],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
                logging.info('Watchdog process spawned')
            except Exception as e:
                logging.error(f'Watchdog spawn failed: {e}')
                print(f"[Main] Watchdog spawn failed: {e}")

        hook = MouseHook(settings)
        logging.info('Mouse hook created')

        # Register cleanup to run on exit
        atexit.register(hook.stop)

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
        act_settings = menu.addAction(translator.tr("tray_settings"))
        act_toggle_enabled = menu.addAction(translator.tr("tray_toggle"))
        act_help = menu.addAction(translator.tr("tray_help"))
        act_about = menu.addAction(translator.tr("tray_about"))
        menu.addSeparator()
        act_exit = menu.addAction(translator.tr("tray_exit"))
        tray.setContextMenu(menu)
        tray.setToolTip("WheelScrollFixer")
        tray.show()
        logging.info('Tray icon shown')

        app_context = AppContext(settings, hook, update_tray_icon, apply_global_font, tray, tray_icon)
        dlg = SettingsDialog(app_context, configure_startup)
        act_settings.triggered.connect(dlg.show)
        logging.info('Settings dialog created')

        def refresh_tray_menu_text():
             act_settings.setText(translator.tr("tray_settings"))
             act_toggle_enabled.setText(translator.tr("tray_toggle"))
             act_help.setText(translator.tr("tray_help"))
             act_about.setText(translator.tr("tray_about"))
             act_exit.setText(translator.tr("tray_exit"))

        # Connect signal instead of monkey-patching
        dlg.languageChanged.connect(refresh_tray_menu_text)


        def toggle_enabled_from_tray():
            current_state = settings.get_enabled()
            settings.set_enabled(not current_state)
            hook.reload_settings(update_tray_icon, apply_global_font)
            update_tray_icon()
            
            status_text = translator.tr("tray_enabled") if not current_state else translator.tr("tray_disabled")
            QtWidgets.QMessageBox.information(
                None, translator.tr("tray_msg_title"), f"{translator.tr('tray_msg_title')}: {status_text}",
            )
        act_toggle_enabled.triggered.connect(toggle_enabled_from_tray)

        def show_help_dialog():
            HelpDialog(dlg).exec_()
        def show_about_dialog():
            AboutDialog(dlg).exec_()
        def exit_app():
            if watchdog_process:
                try:
                    logging.info("Killing watchdog process before exit.")
                    watchdog_process.terminate()
                    try:
                        # Wait for it to actually die to prevent race condition (Zombie App)
                        watchdog_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        logging.warning("Watchdog did not terminate gracefully. Force killing.")
                        watchdog_process.kill()
                except Exception as e:
                    logging.error(f"Failed to kill watchdog: {e}")
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
