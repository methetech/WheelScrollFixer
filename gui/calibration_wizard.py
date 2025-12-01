import time
import statistics
import math
import random
from PyQt5 import QtWidgets, QtCore, QtGui
from localization import translator

class LiveSignalWidget(QtWidgets.QWidget):
    """
    Visualizes scroll signals like an oscilloscope.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setStyleSheet("background-color: #111; border-radius: 5px; border: 1px solid #333;")
        self.signals = [] 
        self.start_time = time.time()
        self.scan_speed = 4.0 
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30)

    def add_signal(self, value):
        t = time.time() - self.start_time
        self.signals.append((t, value))
        self.signals = [s for s in self.signals if s[0] > t - self.scan_speed]

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        # Grid
        painter.setPen(QtGui.QPen(QtGui.QColor("#333"), 1))
        painter.drawLine(0, h//2, w, h//2)
        
        if not self.signals: return

        current_time = time.time() - self.start_time
        
        for t, val in self.signals:
            rel_t = current_time - t
            x = w - (rel_t / self.scan_speed * w)
            y = h/2 - (val * (h/3))
            
            color = QtGui.QColor("#00E676") if val < 0 else QtGui.QColor("#FF1744")
            painter.setPen(QtGui.QPen(color, 2))
            painter.drawLine(int(x), int(h//2), int(x), int(y))
            
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(x, y), 3, 3)

class AnimationWidget(QtWidgets.QWidget):
    """
    Visual instruction widget that draws animated guides.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.mode = "idle" # idle, down, up, sprint, brake_go, brake_stop
        self.frame = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(20) # 50 FPS

    def set_mode(self, mode):
        self.mode = mode
        self.frame = 0
        self.update()

    def animate(self):
        self.frame += 1
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        if self.mode == "idle":
            painter.setPen(QtGui.QColor("#555"))
            painter.setFont(QtGui.QFont("Segoe UI", 12))
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, translator.tr("calib_phase_processing"))
            
        elif self.mode == "down":
            # Draw falling arrows
            speed = 2
            offset = (self.frame * speed) % 40
            painter.setPen(QtGui.QPen(QtGui.QColor("#673AB7"), 3))
            for i in range(-1, 4):
                y = (i * 40) + offset
                if 0 < y < h:
                    self.draw_arrow(painter, cx, y, 20, 1) # 1 = down

        elif self.mode == "up":
            # Draw rising arrows
            speed = 1 # Slower
            offset = (self.frame * speed) % 40
            painter.setPen(QtGui.QPen(QtGui.QColor("#009688"), 3))
            for i in range(0, 5):
                y = h - ((i * 40) + offset)
                if 0 < y < h:
                    self.draw_arrow(painter, cx, y, 20, -1) # -1 = up

        elif self.mode == "sprint":
            # Fast falling arrows with blur effect
            speed = 8
            offset = (self.frame * speed) % 60
            painter.setPen(QtGui.QPen(QtGui.QColor("#FF5722"), 4))
            for i in range(-1, 4):
                y = (i * 60) + offset
                if 0 < y < h:
                    self.draw_arrow(painter, cx, y, 25, 1)

        elif self.mode == "brake_go":
            # Green arrows
            speed = 5
            offset = (self.frame * speed) % 50
            painter.setPen(QtGui.QPen(QtGui.QColor("#4CAF50"), 4))
            for i in range(-1, 4):
                y = (i * 50) + offset
                if 0 < y < h:
                    self.draw_arrow(painter, cx, y, 25, 1)

        elif self.mode == "brake_stop":
            # Flashing Stop Sign
            if (self.frame // 10) % 2 == 0:
                color = QtGui.QColor("#D32F2F") # Red
            else:
                color = QtGui.QColor("#B71C1C") # Dark Red
            
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            size = 100
            painter.drawEllipse(cx - size//2, cy - size//2, size, size)
            
            painter.setPen(QtGui.QColor("white"))
            painter.setFont(QtGui.QFont("Arial", 24, QtGui.QFont.Bold))
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "STOP")

    def draw_arrow(self, painter, x, y, size, direction):
        # direction: 1 for down, -1 for up
        path = QtGui.QPainterPath()
        path.moveTo(x - size, y - (size * direction))
        path.lineTo(x, y)
        path.lineTo(x + size, y - (size * direction))
        painter.drawPath(path)


class CalibrationWizardDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(750, 650)
        self.setWindowIcon(QtGui.QIcon("mouse.ico"))
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.session_data = {
            'flow_down': [],
            'sprint_down': [],
            'brake_tests': [],
            'precision_up': []
        }
        
        self.current_stage_idx = 0
        self.is_active = False
        
        self._init_ui()
        self._init_stages()
        self.retranslate_ui() # Initial translation
        self.show_intro()

    def _init_ui(self):
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.header_lbl = QtWidgets.QLabel("")
        self.header_lbl.setStyleSheet("font-size: 22pt; font-weight: 900; color: #3a7bd5;")
        self.header_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_lbl)
        
        # Visualizer (Top)
        self.visualizer = LiveSignalWidget()
        layout.addWidget(self.visualizer)
        
        # Animation Area (Center)
        anim_container = QtWidgets.QWidget()
        anim_layout = QtWidgets.QHBoxLayout(anim_container)
        self.anim_widget = AnimationWidget()
        anim_layout.addStretch()
        anim_layout.addWidget(self.anim_widget)
        anim_layout.addStretch()
        layout.addWidget(anim_container, 1)
        
        # Instruction Text
        self.instruction_lbl = QtWidgets.QLabel("")
        self.instruction_lbl.setStyleSheet("font-size: 14pt; color: #eeeeee; padding: 5px;")
        self.instruction_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.instruction_lbl.setWordWrap(True)
        layout.addWidget(self.instruction_lbl)
        
        # Progress
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 4px; height: 20px; background: #333; text-align: center; color: #fff; }
            QProgressBar::chunk { background-color: #3a7bd5; }
        """)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Controls
        btn_layout = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton("")
        self.cancel_btn.setStyleSheet("background-color: #333; color: #fff; border: 1px solid #555; padding: 8px;")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.action_btn = QtWidgets.QPushButton("")
        self.action_btn.setFixedSize(200, 45)
        self.action_btn.setStyleSheet("""
            QPushButton { background-color: #3a7bd5; color: white; font-weight: bold; font-size: 11pt; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #3a60d5; }
        """)
        self.action_btn.clicked.connect(self.next_step)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.action_btn)
        layout.addLayout(btn_layout)

    def _init_stages(self):
        # More rigorous targets
        # Stage data now directly uses translator.tr for text
        self.stages = [
            ("calib_phase1_title", "calib_phase1_instr", "down", 80, "flow"),
            ("calib_phase2_title", "calib_phase2_instr", "sprint", 10, "time"),
            ("calib_phase3_title", "calib_phase3_instr", "brake_go", 8, "brake"),
            ("calib_phase4_title", "calib_phase4_instr", "up", 40, "precision"),
            ("calib_phase_analysis", "calib_phase_processing", "idle", 0, "analysis")
        ]

    def retranslate_ui(self):
        tr = translator.tr
        self.setWindowTitle(tr("calib_window_title"))
        # Header, instruction and button texts are updated by show_intro and start_stage
        # so they will fetch the current translation when those methods are called.
        # Ensure buttons have text even when not in a stage
        self.cancel_btn.setText(tr("calib_btn_abort"))
        self.action_btn.setText(tr("calib_btn_start"))


    def show_intro(self):
        tr = translator.tr
        self.header_lbl.setText(tr("calib_suite_header"))
        self.instruction_lbl.setText(tr("calib_intro_instr"))
        self.anim_widget.set_mode("idle")
        self.progress_bar.hide()
        self.action_btn.setText(tr("calib_btn_start"))
        self.action_btn.show()

    def next_step(self):
        if self.current_stage_idx >= len(self.stages) - 1:
            self.perform_analysis()
            return

        self.start_stage(self.current_stage_idx)
        self.current_stage_idx += 1

    def start_stage(self, idx):
        tr = translator.tr
        title_key, instr_key, anim, target, st_type = self.stages[idx]
        
        self.header_lbl.setText(tr(title_key))
        self.instruction_lbl.setText(tr(instr_key))
        self.anim_widget.set_mode(anim)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.action_btn.hide()
        
        self.is_active = True
        self.current_target = target
        self.current_count = 0
        self.current_type = st_type
        self.stage_buffer = []
        
        if st_type == "time":
            self.progress_bar.setRange(0, 100)
            self.timer_start = time.time()
            self.timer_duration = target
            self.stage_timer = QtCore.QTimer(self)
            self.stage_timer.timeout.connect(self.update_time_stage)
            self.stage_timer.start(50)
            
        elif st_type == "brake":
            self.progress_bar.setRange(0, target)
            self.brake_sub_state = "go"
            self.brake_attempts = 0
            self.brake_timer = QtCore.QTimer(self)
            self.brake_timer.setSingleShot(True)
            self.brake_timer.timeout.connect(self.trigger_stop_signal)
            self.brake_timer.start(random.randint(2000, 4000)) # Longer random delay
            
        else:
            self.progress_bar.setRange(0, target)

    def process_scroll_event(self, timestamp, direction):
        QtCore.QMetaObject.invokeMethod(self, "_process_safe", 
                                        QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(float, timestamp),
                                        QtCore.Q_ARG(int, direction))

    @QtCore.pyqtSlot(float, int)
    def _process_safe(self, timestamp, direction):
        # -1 is Down, 1 is Up. Visualizer expects same.
        self.visualizer.add_signal(direction * -1 if direction == -1 else 1)
        
        if not self.is_active: return

        self.stage_buffer.append((timestamp, direction))
        
        if self.current_type in ["flow", "precision"]:
            target_dir = -1 if self.current_type == "flow" else 1
            if direction == target_dir:
                self.current_count += 1
                self.progress_bar.setValue(self.current_count)
                if self.current_count >= self.current_target:
                    self.finish_current_stage()

        elif self.current_type == "brake":
            # In 'go' state, we just record. In 'stop' state, we look for jitters.
            pass

    def update_time_stage(self):
        elapsed = time.time() - self.timer_start
        progress = (elapsed / self.timer_duration) * 100
        self.progress_bar.setValue(int(progress))
        if elapsed >= self.timer_duration:
            self.stage_timer.stop()
            self.finish_current_stage()

    def trigger_stop_signal(self):
        tr = translator.tr
        self.brake_sub_state = "stop"
        self.anim_widget.set_mode("brake_stop") # FLASHING STOP
        self.instruction_lbl.setText(tr("calib_stop_signal"))
        self.stop_timestamp = time.time()
        QtCore.QTimer.singleShot(2000, self.next_brake_attempt) # 2s wait for bounce

    def next_brake_attempt(self):
        tr = translator.tr
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
            self.brake_sub_state = "go"
            self.anim_widget.set_mode("brake_go")
            self.instruction_lbl.setText(tr("calib_scroll_down_again"))
            self.brake_timer.start(random.randint(1500, 3000))

    def finish_current_stage(self):
        tr = translator.tr
        self.is_active = False
        st_type = self.current_type
        if st_type == "flow": self.session_data['flow_down'] = list(self.stage_buffer)
        elif st_type == "time": self.session_data['sprint_down'] = list(self.stage_buffer)
        elif st_type == "precision": self.session_data['precision_up'] = list(self.stage_buffer)
        
        if self.current_stage_idx < len(self.stages) - 1:
            self.header_lbl.setText(tr("calib_stage_complete"))
            self.instruction_lbl.setText(tr("calib_prepare_next"))
            self.anim_widget.set_mode("idle")
            self.action_btn.setText(tr("calib_btn_next_phase"))
            self.action_btn.show()
        else:
            self.perform_analysis()

    def perform_analysis(self):
        tr = translator.tr
        self.header_lbl.setText(tr("calib_analysis_report"))
        self.anim_widget.set_mode("idle")
        self.progress_bar.hide()
        self.visualizer.hide()
        
        rec = self.run_maths()
        
        report = (
            f"<span style='color:#ffffff;'><b>{tr('calib_diag_header')}</b><br>{rec['diagnosis']}<br><br>"
            f"<table cellspacing='8' cellpadding='5' style='font-size:11pt; color:#ffffff;'>"
            f"<tr><td>{tr('calib_table_interval')}</td><td><b>{rec['interval']}s</b></td></tr>"
            f"<tr><td>{tr('calib_table_threshold')}</td><td><b>{rec['threshold']}</b></td></tr>"
            f"<tr><td>{tr('calib_table_strict')}</td><td><b>{'ON' if rec['strict'] else 'OFF'}</b></td></tr>"
            f"<tr><td>{tr('calib_table_physics')}</td><td><b>{rec['min_reversal']}s</b></td></tr>"
            f"<tr><td>{tr('calib_table_smart')}</td><td><b>{'ON' if rec['smart'] else 'OFF'}</b></td></tr>"
            f"</table></span>"
        )
        
        self.instruction_lbl.setText(report)
        self.final_recommendations = rec
        self.action_btn.setText(tr("calib_btn_apply_settings"))
        self.action_btn.show()
        self.action_btn.clicked.disconnect()
        self.action_btn.clicked.connect(self.accept)

    def run_maths(self):
        tr = translator.tr
        # Data Analysis Logic (Robust / Percentile Based)
        rec = {'interval': 0.3, 'threshold': 2, 'strict': True, 'min_reversal': 0.05, 'smart': True, 'diagnosis': ""}
        diag_lines = []
        
        def _get_percentile(data, p):
            if not data: return 0.0
            data.sort()
            k = (len(data) - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c: return data[int(k)]
            return data[int(f)] * (c - k) + data[int(c)] * (k - f)

        # 1. Physics / Glitch (Flow Phase)
        flow = self.session_data['flow_down']
        jitters = []
        for i in range(1, len(flow)):
            t, d = flow[i]
            prev_t, prev_d = flow[i-1]
            if d == 1: # UP glitch (Opposite to flow)
                jitters.append(t - prev_t)
        
        if jitters:
            # Use 5th percentile to ignore ultra-rare random glitches, focus on mechanical faults
            # If mechanics are bad, glitches happen often.
            p_low = _get_percentile(jitters, 5)
            # Add small buffer
            rec['min_reversal'] = max(0.02, float(f"{p_low + 0.015:.3f}"))
            diag_lines.append(tr("calib_diag_fast_reversals", count=len(jitters), min_ms=int(p_low*1000)))
        else:
            rec['min_reversal'] = 0.04
            diag_lines.append(tr("calib_diag_signal_high_consistency"))

        # 2. Speed (Sprint Phase)
        sprint = self.session_data['sprint_down']
        if len(sprint) > 10:
            # Calculate gaps
            gaps = []
            for i in range(1, len(sprint)):
                gaps.append(sprint[i][0] - sprint[i-1][0])
            
            # Use Median to ignore pauses
            median_gap = _get_percentile(gaps, 50)
            
            if median_gap < 0.05: # < 50ms average gap is fast
                rec['smart'] = True
                rec['threshold'] = 3 # Increase threshold for very fast scrollers
                diag_lines.append(tr("calib_diag_high_scroll_velocity"))
            else:
                rec['smart'] = True
                rec['threshold'] = 2
        
        # 3. Brake (Bounce Phase)
        bounces = []
        for test in self.session_data['brake_tests']:
            stop_t = test['stop_time']
            after = [e for e in test['events'] if e[0] > stop_t]
            if after:
                first = after[0]
                if first[1] == 1: # UP (Bounce)
                    bounces.append(first[0] - stop_t)
        
        if bounces:
            # Use 90th percentile (cover almost all bounces, ignore one crazy long delay)
            p_high = _get_percentile(bounces, 90)
            rec['interval'] = max(0.25, float(f"{p_high + 0.15:.2f}"))
            rec['strict'] = True
            diag_lines.append(tr("calib_diag_stop_bounce", worst_ms=int(p_high*1000)))
        else:
            rec['interval'] = 0.28
            if not jitters:
                rec['strict'] = True 
                diag_lines.append(tr("calib_diag_no_bounce"))
            else:
                rec['strict'] = True

        rec['diagnosis'] = "<br>".join([f"• {d}" for d in diag_lines])
        return rec

    def get_results(self):
        return getattr(self, 'final_recommendations', None)