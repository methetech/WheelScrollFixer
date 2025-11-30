import time
import statistics
import math
import random
from PyQt5 import QtWidgets, QtCore, QtGui

class LiveSignalWidget(QtWidgets.QWidget):
    """
    A custom widget that visualizes scroll signals like an oscilloscope.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setStyleSheet("background-color: #212121; border-radius: 10px;")
        self.signals = [] # List of (time, value)
        self.start_time = time.time()
        self.scan_speed = 5.0 # Seconds to show on screen
        self.running = True
        
        # Timer for animation
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30) # ~30 FPS

    def add_signal(self, value):
        # Value: -1 (Down), 1 (Up)
        t = time.time() - self.start_time
        self.signals.append((t, value))
        # Trim old signals
        self.signals = [s for s in self.signals if s[0] > t - self.scan_speed]

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, QtGui.QColor("#212121"))
        
        # Grid lines
        painter.setPen(QtGui.QPen(QtGui.QColor("#424242"), 1, QtCore.Qt.DotLine))
        painter.drawLine(0, h//2, w, h//2) # Center line
        
        if not self.signals:
            return

        current_time = time.time() - self.start_time
        
        # Draw signals
        path = QtGui.QPainterPath()
        # Start form right side
        
        has_started = False
        
        for t, val in self.signals:
            # Map time to x (right is current_time, left is current_time - scan_speed)
            # x = w - ((current_time - t) / self.scan_speed) * w
            rel_t = current_time - t
            x = w - (rel_t / self.scan_speed * w)
            
            # Map value to y (1 -> top, -1 -> bottom)
            # Center is h/2. Scale is h/4.
            y = h/2 - (val * (h/3))
            
            # Draw a vertical bar for discrete scroll event
            color = QtGui.QColor("#00E676") if val < 0 else QtGui.QColor("#FF1744") # Green for Down, Red for Up
            painter.setPen(QtGui.QPen(color, 3))
            painter.drawLine(int(x), int(h//2), int(x), int(y))
            
            # Draw head circle
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(x, y), 4, 4)

class CalibrationWizardDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ultimate Calibration Suite")
        self.setFixedSize(700, 600)
        self.setWindowIcon(QtGui.QIcon("mouse.ico"))
        
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        # Data Storage
        self.session_data = {
            'flow_down': [],
            'sprint_down': [],
            'brake_tests': [], # List of lists
            'precision_up': []
        }
        
        self.current_stage_idx = 0
        self.sub_stage_idx = 0 # For multi-step stages like Brake Test
        self.is_active = False
        
        self._init_ui()
        self._init_stages()
        
        # Show intro
        self.show_intro()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # -- Header --
        self.header_lbl = QtWidgets.QLabel("CALIBRATION MODE")
        self.header_lbl.setStyleSheet("font-size: 24pt; font-weight: 900; color: #333;")
        self.header_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_lbl)
        
        # -- Visualizer --
        self.visualizer = LiveSignalWidget()
        layout.addWidget(self.visualizer)
        
        # -- Main Instruction --
        self.instruction_lbl = QtWidgets.QLabel("Initializing...")
        self.instruction_lbl.setStyleSheet("font-size: 16pt; color: #555; padding: 10px;")
        self.instruction_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.instruction_lbl.setWordWrap(True)
        layout.addWidget(self.instruction_lbl)
        
        # -- Big Icon / Feedback --
        self.icon_lbl = QtWidgets.QLabel("🖱️")
        self.icon_lbl.setStyleSheet("font-size: 64pt;")
        self.icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        # -- Progress --
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #ddd; border-radius: 5px; text-align: center; height: 25px; }
            QProgressBar::chunk { background-color: #673AB7; width: 10px; margin: 0.5px; }
        """)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        # -- Controls --
        btn_layout = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton("Abort")
        self.cancel_btn.setFixedSize(100, 40)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.action_btn = QtWidgets.QPushButton("Start Calibration")
        self.action_btn.setFixedSize(200, 50)
        self.action_btn.setStyleSheet("""
            QPushButton { 
                background-color: #673AB7; color: white; 
                font-weight: bold; font-size: 12pt; border-radius: 5px; 
            }
            QPushButton:hover { background-color: #5E35B1; }
        """)
        self.action_btn.clicked.connect(self.next_step)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.action_btn)
        layout.addLayout(btn_layout)

    def _init_stages(self):
        self.stages = [
            # (Title, Instruction, Icon, TargetCount/Time, Type)
            ("Phase 1: The Flow", "Scroll <b>DOWN</b> smoothly and continuously.<br>Find a comfortable rhythm.", "⬇️", 40, "flow"),
            ("Phase 2: The Sprint", "Scroll <b>DOWN</b> as FAST as you can!<br>Go crazy for 5 seconds.", "🔥", 5, "time"),
            ("Phase 3: The Brake", "Scroll <b>DOWN</b> fast... then <b>STOP</b> immediately when you see the STOP sign.", "🛑", 5, "brake"),
            ("Phase 4: Precision", "Scroll <b>UP</b> slowly.<br>One notch at a time. Click... click... click.", "⬆️", 20, "precision"),
            ("Analysis", "Processing data...", "🧠", 0, "analysis")
        ]

    def show_intro(self):
        self.header_lbl.setText("CALIBRATION SUITE")
        self.instruction_lbl.setText(
            "We will run a series of tests to profile your mouse.<br>"
            "Follow the instructions on screen precisely."
        )
        self.icon_lbl.setText("🖱️")
        self.progress_bar.hide()
        self.action_btn.setText("Start")
        self.action_btn.show()

    def next_step(self):
        # If analysis phase
        if self.current_stage_idx >= len(self.stages) - 1:
            self.perform_analysis()
            return

        stage_info = self.stages[self.current_stage_idx]
        st_type = stage_info[4]
        
        # Start the stage
        self.start_stage(self.current_stage_idx)
        self.current_stage_idx += 1

    def start_stage(self, idx):
        title, instr, icon, target, st_type = self.stages[idx]
        
        self.header_lbl.setText(title)
        self.instruction_lbl.setText(instr)
        self.icon_lbl.setText(icon)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.action_btn.hide()
        
        self.is_active = True
        self.current_target = target
        self.current_count = 0
        self.current_type = st_type
        self.stage_buffer = []
        
        # Special handling for Time based stages
        if st_type == "time":
            self.progress_bar.setRange(0, 100)
            self.timer_start = time.time()
            self.timer_duration = target
            self.stage_timer = QtCore.QTimer(self)
            self.stage_timer.timeout.connect(self.update_time_stage)
            self.stage_timer.start(50)
            
        # Special handling for Brake test
        elif st_type == "brake":
            self.progress_bar.setRange(0, target)
            self.brake_sub_state = "go" # go -> stop -> wait
            self.brake_attempts = 0
            self.instruction_lbl.setText("Scroll <b>DOWN</b> fast! Wait for the signal...")
            self.icon_lbl.setText("⬇️")
            self.brake_timer = QtCore.QTimer(self)
            self.brake_timer.setSingleShot(True)
            self.brake_timer.timeout.connect(self.trigger_stop_signal)
            # Start random timer for stop signal
            self.brake_timer.start(random.randint(1500, 3000))
            
        else:
            self.progress_bar.setRange(0, target)

    def process_scroll_event(self, timestamp, direction):
        """Called by the global hook."""
        # Ensure GUI updates happen on the main thread
        QtCore.QMetaObject.invokeMethod(self, "_process_safe", 
                                        QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(float, timestamp),
                                        QtCore.Q_ARG(int, direction))

    @QtCore.pyqtSlot(float, int)
    def _process_safe(self, timestamp, direction):
        # Visualize everything
        self.visualizer.add_signal(direction * -1 if direction == -1 else 1) # Flip down for visual (-1 down)
        
        if not self.is_active:
            return

        self.stage_buffer.append((timestamp, direction))
        
        if self.current_type in ["flow", "precision"]:
            # Simple counting
            target_dir = -1 if self.current_type == "flow" else 1
            if direction == target_dir:
                self.current_count += 1
                self.progress_bar.setValue(self.current_count)
                
                if self.current_count >= self.current_target:
                    self.finish_current_stage()
            else:
                # Wrong direction! Flash red?
                pass

        elif self.current_type == "brake":
            if self.brake_sub_state == "go":
                # User should be scrolling down
                if direction == -1:
                    # Good, they are scrolling
                    pass
            elif self.brake_sub_state == "stop":
                # User should have stopped!
                # Any event here is a potential jitter/bounce
                # We just record it in buffer.
                pass

    def update_time_stage(self):
        elapsed = time.time() - self.timer_start
        progress = (elapsed / self.timer_duration) * 100
        self.progress_bar.setValue(int(progress))
        
        if elapsed >= self.timer_duration:
            self.stage_timer.stop()
            self.finish_current_stage()

    def trigger_stop_signal(self):
        self.brake_sub_state = "stop"
        self.instruction_lbl.setText("STOP!!! Hands off!")
        self.header_lbl.setStyleSheet("font-size: 24pt; font-weight: 900; color: #D32F2F;") # Red
        self.icon_lbl.setText("🛑")
        self.stop_timestamp = time.time()
        
        # Wait 1.5s for jitters, then next attempt
        QtCore.QTimer.singleShot(1500, self.next_brake_attempt)

    def next_brake_attempt(self):
        # Save buffer for this attempt
        self.session_data['brake_tests'].append({
            'stop_time': getattr(self, 'stop_timestamp', 0),
            'events': list(self.stage_buffer)
        })
        self.stage_buffer.clear()
        
        self.brake_attempts += 1
        self.progress_bar.setValue(self.brake_attempts)
        
        if self.brake_attempts >= self.current_target:
            self.finish_current_stage()
        else:
            # Reset for next attempt
            self.brake_sub_state = "go"
            self.header_lbl.setStyleSheet("font-size: 24pt; font-weight: 900; color: #333;")
            self.instruction_lbl.setText("Scroll <b>DOWN</b> fast again...")
            self.icon_lbl.setText("⬇️")
            # Random delay
            self.brake_timer.start(random.randint(1500, 2500))

    def finish_current_stage(self):
        self.is_active = False
        
        # Save Data
        st_type = self.current_type
        if st_type == "flow": self.session_data['flow_down'] = list(self.stage_buffer)
        elif st_type == "time": self.session_data['sprint_down'] = list(self.stage_buffer)
        elif st_type == "precision": self.session_data['precision_up'] = list(self.stage_buffer)
        
        # Show intermission
        if self.current_stage_idx < len(self.stages) - 1:
            self.header_lbl.setStyleSheet("font-size: 24pt; font-weight: 900; color: #333;")
            self.header_lbl.setText("Stage Complete")
            self.instruction_lbl.setText("Take a breath. Click Next when ready.")
            self.icon_lbl.setText("✅")
            self.action_btn.setText("Next Stage ->")
            self.action_btn.show()
        else:
            self.perform_analysis()

    def perform_analysis(self):
        self.header_lbl.setText("Analysis Report")
        self.icon_lbl.setText("📊")
        self.progress_bar.hide()
        self.visualizer.hide()
        self.action_btn.setText("Apply Settings")
        self.action_btn.show()
        
        rec = self.run_maths()
        
        report = (
            f"<b>Diagnosis:</b><br>{rec['diagnosis']}<br><br>"
            f"<b>Optimized Configuration:</b><br>"
            f"<table cellspacing='5'>"
            f"<tr><td>Block Interval:</td><td><b>{rec['interval']}s</b></td></tr>"
            f"<tr><td>Threshold:</td><td><b>{rec['threshold']}</b></td></tr>"
            f"<tr><td>Strict Mode:</td><td><b>{'ON' if rec['strict'] else 'OFF'}</b></td></tr>"
            f"<tr><td>Physics Check:</td><td><b>{rec['min_reversal']}s</b></td></tr>"
            f"<tr><td>Smart Momentum:</td><td><b>{'ON' if rec['smart'] else 'OFF'}</b></td></tr>"
            f"</table>"
        )
        
        self.instruction_lbl.setText(report)
        self.final_recommendations = rec
        self.action_btn.clicked.disconnect()
        self.action_btn.clicked.connect(self.accept)

    def run_maths(self):
        rec = {'interval': 0.3, 'threshold': 2, 'strict': True, 'min_reversal': 0.05, 'smart': True, 'diagnosis': ""}
        diag_lines = []
        
        # 1. Physics / Glitch Analysis (Flow Data)
        flow_data = self.session_data['flow_down']
        intervals = []
        glitch_intervals = []
        
        for i in range(1, len(flow_data)):
            t, d = flow_data[i]
            prev_t, prev_d = flow_data[i-1]
            dt = t - prev_t
            intervals.append(dt)
            
            if d == 1: # UP (Glitch while flowing down)
                glitch_intervals.append(dt)
        
        if glitch_intervals:
            min_glitch = min(glitch_intervals)
            # If glitch is super fast, it's bounce noise
            rec['min_reversal'] = max(0.02, float(f"{min_glitch + 0.01:.3f}"))
            diag_lines.append(f"Detected micro-jitters (fastest: {min_glitch*1000:.0f}ms).")
        else:
            rec['min_reversal'] = 0.04
            diag_lines.append("Signal is clean.")

        # 2. Speed Analysis (Sprint Data)
        sprint_data = self.session_data['sprint_down']
        if len(sprint_data) > 10:
            # Calculate average tick interval
            ts = [x[0] for x in sprint_data]
            avg_gap = (ts[-1] - ts[0]) / len(ts)
            
            if avg_gap < 0.05: # Less than 50ms per tick = SUPER FAST
                rec['smart'] = True
                rec['threshold'] = 2 # Keep base low, let smart momentum handle high speed
                diag_lines.append("High-velocity scroller.")
            else:
                rec['smart'] = True
                rec['threshold'] = 2
        
        # 3. Brake Analysis (Stop Bounce)
        # Analyze tail events after stop signal
        bounces = []
        for attempt in self.session_data['brake_tests']:
            stop_t = attempt['stop_time']
            events = attempt['events']
            # Filter events happening AFTER stop_t
            post_stop = [e for e in events if e[0] > stop_t]
            
            # Look for Reversals in post_stop
            if post_stop:
                # If first event after stop is UP, it's a bounce
                first_event = post_stop[0]
                if first_event[1] == 1: # Up
                    bounces.append(first_event[0] - stop_t)
        
        if bounces:
            worst_bounce = max(bounces)
            rec['interval'] = max(0.25, float(f"{worst_bounce + 0.15:.2f}"))
            rec['strict'] = True
            diag_lines.append(f"Stop bounce detected (worst: {worst_bounce*1000:.0f}ms).")
        else:
            rec['interval'] = 0.30
            diag_lines.append("Brakes are solid.")

        rec['diagnosis'] = "<br>".join([f"• {d}" for d in diag_lines])
        return rec

    def get_results(self):
        return getattr(self, 'final_recommendations', None)