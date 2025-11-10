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