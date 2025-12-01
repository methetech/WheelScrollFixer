## 1.4.0 (2025-12-01) - The Enterprise Update (Stability & Performance)

*   **Core Refactor (Thread Safety)**: Implemented "Atomic Snapshot" pattern in the mouse hook engine. This eliminates race conditions between the GUI and the background thread, preventing crashes when changing settings rapidly.
*   **Robustness Overhaul**:
    *   **Exception-Safe Hook**: The hook callback is now wrapped in a safety block. If an internal error occurs, it logs the critical failure but ensures the mouse input chain is NOT broken (no more frozen mouse).
    *   **Registry Safety**: "Start on Boot" logic now gracefully handles permission errors (e.g., Antivirus blocks), preventing application crashes.
*   **Calibration Logic 2.0**:
    *   Replaced naive min/max logic with **Statistical Percentiles**. The wizard now intelligently ignores outliers (accidental user errors or one-off glitches) to provide accurate recommendations.
*   **Configuration Modernization**:
    *   Migrated from `.ini` to `.json` for settings storage.
    *   **Auto-Migration**: Automatically converts old `.ini` files to the new format without data loss.
*   **Bug Fixes**:
    *   **Zombie App Fix**: Solved a race condition where the Watchdog process would restart the app after the user clicked "Exit". The app now explicitly waits for the watchdog to terminate.
    *   **Monkey Patch Removal**: Refactored the UI language update mechanism to use proper Qt Signals & Slots.
*   **Dev**: Added initial unit test suite (`tests/test_core.py`) for core logic verification.

## 1.3.1 (2025-11-30) - The Brain Update (Visual Polish)

*   **New Feature (Calibration Wizard 2.0)**: The calibration wizard has been completely overhauled with a visual-first approach.
    *   **Live Signal Visualizer**: A real-time oscilloscope-style graph shows your mouse's raw input signals (green for down, red for up) as you scroll, making it easy to spot glitches visually.
    *   **Animated Instructions**: Static text has been replaced with dynamic animations (falling arrows, flashing stop signs, speedometers) to guide you through each test phase.
    *   **Extended Testing**: The test phases (Flow, Sprint, Brake, Precision) have been lengthened to collect more statistically significant data.
    *   **Enhanced Analysis**: The recommendation engine now uses more robust math to calculate optimal settings based on the extended dataset.
*   **UI Improvement**: The settings dialog has been reverted to a cleaner, single-panel layout organized with GroupBoxes, replacing the tabbed interface for better usability.
*   **Fix**: Resolved layout initialization issues that caused crashes when opening the settings dialog.

## 1.3.0 (2025-11-30) - The Brain Update

*   **New Feature (Physics Check)**: Implemented an "Impossible Reversal" filter. Scroll events in the opposite direction occurring faster than humanly possible (e.g., <50ms) are immediately discarded as noise.
*   **New Feature (Smart Momentum)**: Dynamic threshold adjustment. The `Direction Change Threshold` is now automatically increased during fast scrolling.
*   **New Feature (Strict Mode)**: Blocks the very first scroll event of a new sequence to confirm user intent.
*   **New Feature (Restore Defaults Button)**: Added a button to instantly reset all main settings to their recommended default values.
*   **Refactor**: `MouseHook` now supports a calibration callback mechanism.

## 1.2.0 (2025-11-30)

*   **New Feature (Strict Mode)**: Introduced "Strict Mode".
*   **UX Improvement (Unsaved Changes)**: Added unsaved changes prompt.
*   **UI Improvement**: Replaced save popup with a status label.

## 1.0.3 (2025-11-22)

*   **BREAKING**: Renamed main script to `WheelScrollFixer.py`.
*   **Fixes**: Critical 64-bit compatibility, auto-elevation, hook error 126.

## 1.0.2 (2025-11-10)

*   Fixes: Atomic saving, watchdog, import errors.
*   Feat: Single executable packaging.

## 1.0.1 (2025-10-14)

*   Fix: --no-watchdog flag.

## 1.0.0 (2025-10-14)

*   Initial release.