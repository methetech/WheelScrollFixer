# WheelScrollFixer

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/methetech/WheelScrollFixer?style=for-the-badge)](https://github.com/methetech/WheelScrollFixer/releases)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE.md)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg?style=for-the-badge)](https://www.microsoft.com/windows)

A lightweight but powerful Windows utility to prevent accidental mouse wheel scrolling and "jitter."

<img src="WheelScrollFixer.jpg" alt="WheelScrollFixer Settings UI" width="400"/>

**Important Notes:**
- **Administrator Privileges**: This application requires Administrator privileges to install low-level mouse hooks. You will see a UAC prompt when starting the application.
- **Antivirus Warning**: Because the application uses low-level mouse hooks, some antivirus software may flag it as a potential threat. This is a false positive. Please allow the executable to run or add an exclusion for it in your antivirus settings.

---

## Getting Started

### For Users

1.  Go to the project's **Releases Page**.
2.  Download the `WheelScrollFixer.exe` file from the latest release.
3.  Run `WheelScrollFixer.exe` (it will prompt for Administrator privileges).

### For Developers

If you want to run or build from source:

1.  **Clone the repository** and navigate into the directory:
    ```bash
    git clone https://github.com/methetech/WheelScrollFixer.git
    cd WheelScrollFixer
    ```

2.  **Install dependencies** (using a virtual environment is recommended):
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run from source** (requires Administrator privileges):
    ```bash
    python WheelScrollFixer.py
    ```

4.  **Build the executable**:
    To create the standalone `WheelScrollFixer.exe` file, run the following command:
    ```bash
    pyinstaller --onefile --noconsole --icon=mouse.ico --name=WheelScrollFixer --add-data "mouse.ico;." WheelScrollFixer.py
    ```
    The final executable will be located in the `dist` folder.

## The Problem: Annoying Mouse Wheel Jitter

Have you ever been scrolling through a long document or webpage, only to have the page "jump" back up slightly when you stop? This is "scroll bounce," caused by sensitive or faulty mouse encoders.

## How It Works: The Solution

WheelScrollFixer acts as a smart filter between your mouse and Windows.

1.  **Physics Check**: Filters out physically impossible reversals (<50ms) instantly.
2.  **Strict Mode**: Verifies the start of every scroll sequence to prevent initial glitches.
3.  **Smart Momentum**: Dynamically adjusts sensitivity based on your scroll speed.
4.  **Thread-Safe Core**: Uses atomic snapshots to ensure zero race conditions or crashes.
5.  **Robust Error Handling**: Silent recovery from hook errors and registry blocks.

## Features

*   **Enterprise-Grade Stability**: Re-engineered core with proper thread safety and exception handling.
*   **Calibration Wizard 2.0**: An interactive "Mouse Lab" with:
    *   **Live Signal Visualizer**: See your mouse signals in real-time (oscilloscope style).
    *   **Animated Guide**: Follow visual cues for Flow, Sprint, and Brake tests.
    *   **Robust Analysis**: Uses statistical percentiles to ignore outliers and random glitches.
*   **Smart JSON Config**: Modern, auto-migrating configuration system that preserves your settings.
*   **Restore Defaults**: One-click reset to the recommended optimal settings.
*   **Application Blacklist**: Disable blocking for specific games or apps.
*   **Per-Application Profiles**: Custom settings for different apps.
*   **Start on Boot**: Auto-start with Windows (now with antivirus-safe error handling).
*   **System Tray Control**: Quiet operation in the background.

## Command-line Arguments

*   `--no-watchdog`: Run the application without the watchdog process. This is useful for development and debugging, as it prevents the application from automatically restarting.

---

## Contributing

We welcome contributions! Please see the `CONTRIBUTING.md` file for guidelines.