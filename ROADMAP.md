# Project Roadmap

This document outlines the future direction and potential features for WheelScrollFixer. It's a living document intended to guide development and inspire contributions. If you're looking for a way to contribute, picking up an item from this list is a great place to start!

## Next Up

*   **Automatic Update Checker**: Implement a feature that periodically checks the GitHub Releases page for a new version and notifies the user.

---

## Long-Term & Ambitious Goals (Major New Functionality)

These are transformative features that would significantly expand the scope of the application, potentially turning it into an open-source competitor to commercial power-user tools.

*   [ ] **Mouse Button Remapping**:
    *   Allow users to re-assign the function of any mouse button (e.g., make a side button act as a middle-click).
    *   This would be configurable on a per-profile basis.
*   [ ] **Simple Macro Support**:
    *   Allow a mouse button to trigger a keyboard shortcut (e.g., `Ctrl+W` to close a tab) or a short sequence of key presses.
*   [ ] **Mouse Gestures**:
    *   Implement a system to detect gestures, such as holding a button while moving the mouse or scrolling the wheel.
    *   *Example*: Hold Right-Click + Scroll to adjust system volume.
    *   *Example*: Hold Side Button + Move Mouse Left/Right to switch virtual desktops.
*   [ ] **Plugin Architecture**:
    *   This is the ultimate goal for extensibility. Refactor the core application to allow new functionality (like gestures or macros) to be added via plugins. This would create a powerful framework for community contributions.

---

## v2.0 Goal: Continuous Learning & Self-Optimization

This is the ultimate goal for making WheelScrollFixer truly "smart."

*   [ ] **Adaptive Settings**: The application continuously monitors your actual mouse usage and blocked events in the background.
*   [ ] **Confidence Score**: Display a "Confidence Score" for the current settings, indicating how well they are suppressing jitters without interfering with intentional scrolling.
*   [ ] **Contextual Learning**: Distinguish between accidental glitches during normal usage and deliberate actions.
*   [ ] **Proactive Optimization**: Based on long-term data, the application will periodically suggest (or automatically apply with user consent) further fine-tuned adjustments to `Interval`, `Threshold`, `Strict Mode`, `Physics Check`, and `Smart Momentum` settings.
*   [ ] **"Learning Mode" Toggle**: A user-facing option to enable/disable background data collection for privacy and performance.

---

## Completed Milestones

### v1.4.0 Enterprise Update (Stability)
*   **Thread Safety**: Implemented Atomic Snapshots to prevent race conditions.
*   **Robustness**: Exception-safe hooks and registry handling.
*   **Math Overhaul**: Percentile-based calibration logic.
*   **Modern Config**: JSON settings with auto-migration.
*   **Zombie Fix**: Proper Watchdog termination.

### v1.3.0 The Brain Update
*   **Calibration Wizard**: A comprehensive, interactive diagnostics tool that analyzes your mouse's unique scroll behavior (glitches, speed, bounce) via global input monitoring and recommends optimized settings automatically.
*   **Physics Check**: Implemented an "Impossible Reversal" filter. Scroll events in the opposite direction occurring faster than humanly possible (e.g., <50ms) are immediately discarded as noise, without affecting the blocking logic state.
*   **Smart Momentum**: Dynamic threshold adjustment. The `Direction Change Threshold` is now automatically increased during fast scrolling, making it harder for accidental reversals to register when you have high scroll momentum.