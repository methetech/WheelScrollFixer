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
    pyinstaller --onefile --noconsole --icon=mouse.ico --name=WheelScrollFixer WheelScrollFixer.py
    ```
    The final executable will be located in the `dist` folder.

## The Problem: Annoying Mouse Wheel Jitter

Have you ever been scrolling through a long document or webpage, only to have the page "jump" back up slightly when you stop?

This often happens with sensitive or free-spinning mouse wheels. When the wheel comes to a halt, it can physically "bounce" or "jitter," sending one or more scroll events in the opposite direction. This tiny, accidental input is enough to make your view jump, which can be distracting and frustrating.

## How It Works: The Solution (v1.3.0 Brain Update!)

WheelScrollFixer solves this by intelligently monitoring mouse wheel activity and blocking these accidental "jitter" events.

It works through a sophisticated, multi-layered approach:

1.  **Low-Level Mouse Hook**: The application registers a `WH_MOUSE_LL` hook, a feature in Windows that allows it to monitor all low-level mouse events system-wide, specifically looking for `WM_MOUSEWHEEL` messages.

2.  **The "Physics Check" (NEW in v1.3.0)**: This is the first line of defense. If a scroll event occurs in the *opposite direction* faster than a human can physically react (e.g., <50ms), it's immediately identified as electrical noise or mechanical bounce and **discarded without affecting the logic state**. This prevents the system from getting confused by "impossible" signals.

3.  **"Strict Mode" (NEW in v1.2.0)**: If enabled (default), when a new scroll sequence begins after a period of inactivity, the very first scroll event is held back. The system then waits for a second event in the *same direction* to confirm your true intent. This completely eliminates issues where a faulty mouse sends a single random signal right at the start of a scroll, preventing it from locking the wrong direction.

4.  **Establishing a Direction & Blocking Jitter**: Once a direction is confirmed (or immediately if Strict Mode is off), the application notes the direction (up or down) and starts a short timer (the `Block Interval`).
    *   If you continue scrolling in the **same direction**, the timer resets, and scrolling proceeds normally.
    *   If an event in the **opposite direction** occurs within the `Block Interval`, the system initially assumes it's an accidental jitter and **blocks it**.

5.  **"Smart Momentum" (NEW in v1.3.0)**: This feature dynamically adjusts the tolerance for direction changes. If you are scrolling very fast, the system understands you have high "momentum" and temporarily **increases the `Direction Change Threshold`**. This makes it much harder for a single, accidental opposite flick to change your scroll direction during rapid movement, while still keeping the system responsive during slower, deliberate scrolling.

6.  **Allowing Deliberate Changes**: What if you *meant* to change direction quickly? That's what the base **Direction Change Threshold** is for. This setting defines how many consecutive opposite-direction events are needed to override the block. If you scroll aggressively enough in the new direction, the application recognizes it as a deliberate change, establishes a new scrolling direction, and lets the events pass through.

This multi-layered approach ensures the smoothest, most predictable, and intelligent scroll experience possible, even with the most problematic mouse wheels.

## Features

*   **Calibration Wizard (NEW in v1.3.0)**: A comprehensive, interactive diagnostics tool that analyzes your mouse's unique behavior and automatically suggests optimized settings for all parameters. No more guesswork!
*   **Physics Check (NEW in v1.3.0)**: Intelligent filtering for physically impossible scroll reversals.
*   **Smart Momentum (NEW in v1.3.0)**: Dynamically adjusts blocking sensitivity based on your scrolling speed.
*   **Strict Mode (v1.2.0)**: Advanced logic that verifies scroll intent before allowing movement, eliminating start-of-scroll glitches.
*   **Customizable Blocking Logic**: Fine-tune the `Block Interval` and `Direction Change Threshold` to match your mouse's sensitivity and your personal preference.
*   **Restore Defaults (NEW in v1.3.0)**: Instantly revert all settings to the recommended optimal defaults.
*   **Application Blacklist**: Disable scroll blocking for specific applications (e.g., games, design software) where you need raw, unfiltered mouse input.
*   **Per-Application Profiles**: Define unique `Interval` and `Threshold` settings for different applications.
*   **Start on Boot**: Set the application to launch automatically with Windows. When enabled, a watchdog process ensures the app remains running.
*   **System Tray Control**: The application runs quietly in the system tray. Right-click the icon to access settings, toggle blocking, or exit.
*   **Clean & Modern UI**: A user-friendly, single-panel interface organized with clear sections.

## Command-line Arguments

*   `--no-watchdog`: Run the application without the watchdog process. This is useful for development and debugging, as it prevents the application from automatically restarting.

---

## Contributing

We welcome contributions! Please see the `CONTRIBUTING.md` file for guidelines.
