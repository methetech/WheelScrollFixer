## 1.0.3 (2025-11-22)

*   **BREAKING**: Renamed main script from `wheel.py` to `WheelScrollFixer.py` for consistency.
*   **Fix**: Fixed critical 64-bit compatibility issues with ctypes definitions (LRESULT, WPARAM, LPARAM).
*   **Fix**: Implemented auto-elevation to Administrator privileges for proper low-level hook functionality.
*   **Fix**: Resolved SetWindowsHookEx Error 126 by correctly setting hMod parameter to NULL for WH_MOUSE_LL.
*   **Fix**: Fixed OverflowError in CallNextHookEx by explicitly defining argtypes for 64-bit pointers.
*   **Fix**: Implemented missing get_foreground_process_name function for per-app profiles.
*   **Improvement**: Replaced debug print statements with proper logging for cleaner production operation.
*   **Docs**: Updated all documentation to reflect new filename (WheelScrollFixer.py/exe).

## 1.0.2 (2025-11-10)

*   Fix: Implemented atomic saving for settings to prevent data corruption and race conditions.
*   Fix: Re-implemented watchdog process for robust application monitoring and automatic restarts.
*   Fix: Resolved ImportError by correctly configuring the 'gui' package with __init__.py.
*   Fix: Corrected SyntaxError in stylesheet and invalid escape sequence in mutex name.
*   Fix: Added missing apply_settings method to SettingsDialog class.
*   Feat: Packaged application into a single executable (wheel.exe) using PyInstaller.

# Changelog

## 1.0.1 (2025-10-14)

*   Fix: Add --no-watchdog flag to prevent the app from restarting automatically.
*   Chore: Move Settings.ini to config/ directory.

## 1.0.0 (2025-10-14)

*   Initial release of WheelScrollFixer.