#meormeow

import sys
import cv2
import numpy as np
import tensorflow as tf
from PyQt5.QtWidgets import QGraphicsOpacityEffect

from PyQt5.QtCore import (
    Qt, QTimer, QDateTime, QRectF,
    QPropertyAnimation, QEasingCurve, pyqtProperty, QEvent
)
from PyQt5.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QFont
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFrame, QSizePolicy
)

# PiCamera2
from picamera2 import Picamera2

# === AI CONFIG (add near your constants section) ===
MODEL_PATH = "Desktop/Copra_AI/Copra_Test_UpdateV2.tflite"
CLASS_NAMES = ['G1', 'G2', 'G3', 'REJ']
IMAGE_SIZE = (224, 224)

# ====== PREVIEW SIZE (camera stream size) ======
PREVIEW_W = 350
PREVIEW_H = 400
CAM_FPS_MS = 30  

# ====== AI READ INTERVAL (2 minutes) ======
AI_READ_INTERVAL_MS = 10_000
AI_FIRST_READ_DELAY_MS = 600


class ConfidenceGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._value = 0.0  # 0..100
        self._segments = 24
        self._gap_deg = 4.0
        self._start_deg = 120.0
        self._span_deg = 300.0

        self._seg_on = QColor(192, 92, 34)
        self._seg_off = QColor(238, 222, 205)
        self._title_color = QColor(155, 125, 105)
        self._value_color = QColor(140, 105, 85)

        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.setFixedSize(130, 130)

    def stop_animation(self):
        if self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()

    def set_target(self, percent: float):
        percent = max(0.0, min(100.0, float(percent)))
        self.stop_animation()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(percent)
        self._anim.start()

    def get_value(self) -> float:
        return float(self._value)

    def set_value(self, v: float):
        self._value = max(0.0, min(100.0, float(v)))
        self.update()

    value = pyqtProperty(float, fget=get_value, fset=set_value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        side = min(self.width(), self.height())
        pad = int(side * 0.12)
        ring_th = max(10, int(side * 0.10))

        rect = QRectF(
            (self.width() - side) / 2 + pad,
            (self.height() - side) / 10 + pad,
            side - 2 * pad,
            side - 2 * pad
        )

        seg_span = self._span_deg / self._segments
        on_segments = int(round((self._value / 100.0) * self._segments))

        pen_off = QPen(self._seg_off)
        pen_off.setWidth(ring_th)
        pen_off.setCapStyle(Qt.FlatCap)

        pen_on = QPen(self._seg_on)
        pen_on.setWidth(ring_th)
        pen_on.setCapStyle(Qt.FlatCap)

        for i in range(self._segments):
            start = self._start_deg + i * seg_span
            span = seg_span - self._gap_deg
            p.setPen(pen_on if i < on_segments else pen_off)
            p.drawArc(rect, int(start * 16), int(-span * 16))

        p.setPen(self._title_color)
        f1 = QFont("Arial", max(9, int(side * 0.10)))
        f1.setBold(True)
        p.setFont(f1)
        top_rect = QRectF(0, int(side * 0.00), self.width(), int(side * 0.20))
        p.drawText(top_rect, Qt.AlignHCenter | Qt.AlignTop, "Confidence")

        p.setPen(self._value_color)
        f2 = QFont("Arial", max(14, int(side * 0.15)))
        f2.setBold(True)
        p.setFont(f2)
        val_rect = self.rect().adjusted(0, int(side * 0.06), 0, 0)
        p.drawText(val_rect, Qt.AlignHCenter | Qt.AlignVCenter, f"{self._value:.1f}%")


class Card(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFrameShape(QFrame.NoFrame)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(14, 12, 14, 12)
        self.root.setSpacing(10)

        if title:
            t = QLabel(title)
            t.setObjectName("CardTitle")
            self.root.addWidget(t)


class OverlayPage(QFrame):
    """Full-screen overlay that hovers above the main UI."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("OverlayPage")
        self.setVisible(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.dialog = QFrame(self)
        self.dialog.setObjectName("OverlayDialog")
        dialogLay = QVBoxLayout(self.dialog)
        dialogLay.setContentsMargins(18, 16, 18, 16)
        dialogLay.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)

        self.titleLabel = QLabel(title)
        self.titleLabel.setObjectName("OverlayTitle")

        self.closeBtn = QPushButton("✕")
        self.closeBtn.setObjectName("OverlayClose")
        self.closeBtn.setFixedSize(38, 38)

        header.addWidget(self.titleLabel, 1)
        header.addWidget(self.closeBtn, 0, Qt.AlignRight)

        self.body = QLabel("Content goes here…")
        self.body.setObjectName("OverlayBody")
        self.body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.body.setWordWrap(True)

        dialogLay.addLayout(header)
        dialogLay.addWidget(self.body, 1)

        root.addStretch(1)
        root.addWidget(self.dialog, 0, Qt.AlignHCenter)
        root.addStretch(1)

    def show_overlay(self):
        self.setVisible(True)
        self.raise_()

    def hide_overlay(self):
        self.setVisible(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.last_label = None
        self.stable_counter = 0
        self.STABLE_REQUIRED = 3          # how many consecutive reads required
        self.MIN_CONFIDENCE = 0.80        # 80% minimum confidence
        self.capture_cooldown = False     # prevents repeated auto-captures

        # === LOAD TFLITE MODEL (inside MainWindow.__init__ AFTER camera init) ===
        self.interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Kiosk look (no window bar)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle("Copra Quality Analysis System (PiCamera2)")

        # ===== Press & Hold EXIT (top-right) =====
        self.exit_corner_size = 120
        self.exit_hold_ms = 2000
        self._exit_hold_armed = False
        self._exit_timer = QTimer(self)
        self._exit_timer.setSingleShot(True)
        self._exit_timer.timeout.connect(self.close)

        # Capture press/hold anywhere (even on child widgets)
        QApplication.instance().installEventFilter(self)

        # ===== PiCamera2 =====
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={
                "size": self.picam2.sensor_resolution,
                "format": "RGB888"
            }
        )
        self.picam2.configure(config)
        self.picam2.start()

        # ===== Preview timer =====
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_frame)

        self.is_running = False
        self.last_frame = None

        # ===== AI timer (2 min) =====
        self.ai_timer = QTimer(self)
        self.ai_timer.setInterval(AI_READ_INTERVAL_MS)
        self.ai_timer.timeout.connect(self.do_ai_read)

        # ===== Central =====
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(12)

        # ===== Top bar =====
        top = QHBoxLayout()
        self.titleLabel = QLabel("COPRA QUALITY ANALYSIS SYSTEM")
        self.titleLabel.setObjectName("HeaderTitle")
        self.titleLabel.setAlignment(Qt.AlignCenter)

        self.dateLabel = QLabel("")
        self.dateLabel.setObjectName("HeaderMeta")
        self.timeLabel = QLabel("")
        self.timeLabel.setObjectName("HeaderMeta")

        top.addWidget(self.titleLabel, 1)
        top.addWidget(self.dateLabel, 0, Qt.AlignRight)
        top.addSpacing(8)
        top.addWidget(self.timeLabel, 0, Qt.AlignRight)
        outer.addLayout(top)

        # ===== Main content row (3 columns) =====
        content = QHBoxLayout()
        content.setSpacing(12)

        # LEFT: Preview
        leftCard = Card("", self)
        self.previewLabel = QLabel("Tap START to show camera")
        self.previewLabel.setObjectName("Preview")
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setFixedSize(PREVIEW_W, PREVIEW_H)
        self.previewLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.previewLabel.setScaledContents(False)
        leftCard.root.addWidget(self.previewLabel, 0, Qt.AlignCenter)
        leftCard.root.addStretch(1)

        # CENTER: Final result
        centerCard = Card("FINAL RESULT", self)

        gradeBox = QFrame()
        gradeBox.setObjectName("GradeBox")
        gradeLayout = QVBoxLayout(gradeBox)
        gradeLayout.setContentsMargins(14, 14, 14, 14)
        gradeLayout.setSpacing(6)

        self.gradeTitle = QLabel("GRADE")
        self.gradeTitle.setObjectName("MiniTitle")
        self.gradeValue = QLabel("Grade 1")
        self.gradeValue.setObjectName("GradeValue")
        self.acceptedValue = QLabel("Accepted")
        self.acceptedValue.setObjectName("AcceptedValue")

        gradeLayout.addWidget(self.gradeTitle, 0, Qt.AlignHCenter)
        gradeLayout.addWidget(self.gradeValue, 0, Qt.AlignHCenter)
        gradeLayout.addWidget(self.acceptedValue, 0, Qt.AlignHCenter)

        confBox = QFrame()
        confBox.setObjectName("ConfidenceBox")
        confLayout = QVBoxLayout(confBox)
        confLayout.setContentsMargins(14, 14, 14, 14)
        confLayout.setSpacing(4)

        self.confGauge = ConfidenceGauge(self)
        confLayout.addWidget(self.confGauge, 0, Qt.AlignHCenter)

        legend = QLabel(
            "Quality Status\n"
            "• Grade 1  Excellent\n"
            "• Grade 2  Good\n"
            "• Grade 3  Fair\n"
            "• Reject   Poor"
        )
        legend.setObjectName("Legend")

        centerCard.root.addWidget(gradeBox)
        centerCard.root.addWidget(confBox)
        centerCard.root.addWidget(legend)

        # RIGHT: Batch + Sensor + Recommendation
        rightCol = QVBoxLayout()
        rightCol.setSpacing(12)

        batchCards = Card("BATCH COUNT", self)
        self.batchLabel = QLabel("Batch 1: 56")
        self.batchLabel.setObjectName("LineItem")
        batchCards.root.addWidget(self.batchLabel)

        sensorCards = Card("SENSOR READING", self)
        self.m1 = QLabel("Moisture Content 1: 12.4%")
        self.m2 = QLabel("Moisture Content 2: 8.4%")
        for w in (self.m1, self.m2):
            w.setObjectName("LineItem")
            sensorCards.root.addWidget(w)

        recoCard = Card("RECOMMENDATION", self)
        self.cookTime = QLabel("Cooking Time: 45-50 Minutes")
        self.cookTime.setObjectName("BigPill")
        self.status = QLabel("Status: Optimal")
        self.status.setObjectName("LineItem")
        self.env = QLabel("Temp: 45*C   |   Humidity: 65%")
        self.env.setObjectName("MutedItem")
        recoCard.root.addWidget(self.cookTime)
        recoCard.root.addWidget(self.status)
        recoCard.root.addWidget(self.env)

        rightCol.addWidget(batchCards)
        rightCol.addWidget(sensorCards)
        rightCol.addWidget(recoCard)


        content.addWidget(leftCard, 3)
        content.addWidget(centerCard, 2)
        content.addLayout(rightCol, 2)
        outer.addLayout(content, 1)

        # ===== Bottom bar =====
        bottom = QFrame()
        bottom.setObjectName("BottomBar")
        bottomLayout = QGridLayout(bottom)
        bottomLayout.setContentsMargins(10, 10, 10, 10)
        bottomLayout.setHorizontalSpacing(10)
        bottomLayout.setVerticalSpacing(0)

        self.historyBtn = QPushButton(" HISTORY")
        self.historyBtn.setObjectName("NavBtn")

        self.mainBtn = QPushButton("START")
        self.mainBtn.setObjectName("PrimaryBtn")
        self.mainBtn.setMinimumHeight(60)

        self.reportBtn = QPushButton(" REPORT")
        self.reportBtn.setObjectName("NavBtn")

        bottomLayout.addWidget(self.historyBtn, 0, 0)
        bottomLayout.addWidget(self.mainBtn, 0, 1)
        bottomLayout.addWidget(self.reportBtn, 0, 2)

        bottomLayout.setColumnStretch(0, 1)
        bottomLayout.setColumnStretch(1, 2)
        bottomLayout.setColumnStretch(2, 1)

        outer.addWidget(bottom, 0)

        # ===== Signals =====
        self.mainBtn.clicked.connect(self.toggle_system)

        # Clock updater
        self.clock = QTimer(self)
        self.clock.timeout.connect(self.update_datetime)
        self.clock.start(500)
        self.update_datetime()

        self.apply_styles()

        # ===== Overlays (History / Report) =====
        self.historyOverlay = OverlayPage("  HISTORY", central)
        self.historyOverlay.body.setText(
            "• Show past batches here\n"
            "• Example: Date, Grade, Confidence, Moisture values\n"
            "• You can later replace this with a table/list"
        )
        self.reportOverlay = OverlayPage("  REPORT", central)
        self.reportOverlay.body.setText(
            "• Generate/preview reports here\n"
            "• Example: Export PDF, print, summary per batch"
        )

        self.historyOverlay.closeBtn.clicked.connect(self.historyOverlay.hide_overlay)
        self.reportOverlay.closeBtn.clicked.connect(self.reportOverlay.hide_overlay)

        self.historyBtn.clicked.connect(self.open_history)
        self.reportBtn.clicked.connect(self.open_report)

        self._resize_overlays()

        # Flash overlay
        self.flash = QFrame(self.centralWidget())
        self.flash.setStyleSheet("background:white;")
        self.flash.setGeometry(self.centralWidget().rect())
        self.flash.raise_()
        self.flash.hide()

        self.flash_effect = QGraphicsOpacityEffect(self.flash)
        self.flash.setGraphicsEffect(self.flash_effect)
        self.flash_effect.setOpacity(0)

        self.flash_anim = QPropertyAnimation(self.flash_effect, b"opacity")
        self.flash_anim.setDuration(250)
        self.flash_anim.setStartValue(0.0)
        self.flash_anim.setKeyValueAt(0.5, 1.0)
        self.flash_anim.setEndValue(0.0)

    def classify_frame(self, frame):
        # Ensure RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Resize to model input
        resized = cv2.resize(frame_rgb, IMAGE_SIZE)
        
        # Proper MobileNetV2 preprocessing
        img_array = resized.astype(np.float32)
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        img_array = np.expand_dims(img_array, axis=0)

        self.interpreter.set_tensor(self.input_details[0]['index'], img_array)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])

        idx = int(np.argmax(output))
        confidence = float(output[0][idx])
        return CLASS_NAMES[idx], confidence

    # ===== Press & Hold Exit via eventFilter =====
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            gp = event.globalPos()
            p = self.mapFromGlobal(gp)

            if p.x() > self.width() - self.exit_corner_size and p.y() < self.exit_corner_size:
                self._exit_hold_armed = True
                self._exit_timer.start(self.exit_hold_ms)

        # Cancel hold on release (anywhere)
        elif event.type() == QEvent.MouseButtonRelease:
            if self._exit_hold_armed:
                self._exit_timer.stop()
                self._exit_hold_armed = False

        return super().eventFilter(obj, event)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: #f6f1ea; color:#4b2f1e; font-family: Arial; }
            #HeaderTitle { font-size: 22px; font-weight: 800; letter-spacing: 1px; }
            #HeaderMeta { font-size: 14px; padding: 6px 10px; background:#efe5db; border-radius: 8px; }

            #Card {
                background:#ffffff;
                border: 1px solid #e5d7ca;
                border-radius: 16px;
            }
            #CardTitle {
                font-size: 14px;
                font-weight: 800;
                color:#6a3b20;
                letter-spacing: 1px;
            }

            #Preview {
                background:#f2ece6;
                border: 2px solid #d9c7b6;
                border-radius: 14px;
            }

            #GradeBox, #ConfidenceBox {
                background:#fbf7f2;
                border: 1px solid #eadbce;
                border-radius: 14px;
            }
            #MiniTitle { font-size: 12px; font-weight: 800; color:#7a4b2a; }
            #GradeValue { font-size: 30px; font-weight: 900; color:#ffffff; background:#8a4c2a; padding: 10px 18px; border-radius: 12px; }
            #AcceptedValue { font-size: 16px; font-weight: 900; color:#2e6b3a; }

            #Legend { font-size: 12px; color:#7a4b2a; padding: 4px; }

            #LineItem { font-size: 15px; padding: 6px 2px; }
            #MutedItem { font-size: 13px; color:#8b7766; padding-top: 6px; }

            #BigPill {
                font-size: 18px; font-weight: 900;
                color:#ffffff;
                background:#8a4c2a;
                padding: 10px 14px;
                border-radius: 14px;
            }

            QPushButton {
                border-radius: 12px;
                padding: 12px;
                font-size: 14px;
                font-weight: 800;
            }
            #PrimaryBtn { background:#8a4c2a; color:#fff; border:none; }
            #PrimaryBtn:pressed { background:#6f3b20; }

            #DangerBtn { background:#c14b3d; color:#fff; border:none; }
            #DangerBtn:pressed { background:#9f3b30; }

            #NavBtn { background:#efe5db; color:#6a3b20; border:none; }
            #NavBtn:pressed { background:#e4d5c6; }

            #BottomBar {
                background:#ffffff;
                border: 1px solid #e5d7ca;
                border-radius: 16px;
            }

            #OverlayPage {
                background: rgba(0, 0, 0, 110);
            }
            #OverlayDialog {
                background: #ffffff;
                border: 1px solid #e5d7ca;
                border-radius: 18px;
                min-width: 520px;
                max-width: 900px;
                min-height: 380px;
            }
            #OverlayTitle {
                font-size: 18px;
                font-weight: 900;
                color: #6a3b20;
                letter-spacing: 1px;
            }
            #OverlayClose {
                background: #efe5db;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 900;
                color: #6a3b20;
            }
            #OverlayClose:pressed { background:#e4d5c6; }
            #OverlayBody {
                font-size: 14px;
                color: #4b2f1e;
            }
        """)

    def _resize_overlays(self):
        c = self.centralWidget()
        if c:
            r = c.rect()
            self.historyOverlay.setGeometry(r)
            self.reportOverlay.setGeometry(r)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_overlays()
        if hasattr(self, "flash"):
            self.flash.setGeometry(self.centralWidget().rect()) 

    def trigger_flash(self):
        self.flash.show()
        self.flash_anim.start()
        self.flash_anim.finished.connect(self.flash.hide)

    def open_history(self):
        self.reportOverlay.hide_overlay()
        self.historyOverlay.show_overlay()

    def open_report(self):
        self.historyOverlay.hide_overlay()
        self.reportOverlay.show_overlay()

    def update_datetime(self):
        now = QDateTime.currentDateTime()
        self.dateLabel.setText(now.toString("yyyy-MM-dd"))
        self.timeLabel.setText(now.toString("hh:mm:ss AP"))

    def toggle_system(self):
        if not self.is_running:
            self.is_running = True
            self.mainBtn.setText("STOP")
            self.mainBtn.setObjectName("DangerBtn")
            self._repolish(self.mainBtn)

            self.preview_timer.start(CAM_FPS_MS)

            self.ai_timer.stop()
            QTimer.singleShot(AI_FIRST_READ_DELAY_MS, self.do_ai_read)
            self.ai_timer.start()

        else:
            self.is_running = False
            self.mainBtn.setText("START")
            self.mainBtn.setObjectName("PrimaryBtn")
            self._repolish(self.mainBtn)

            self.preview_timer.stop()
            self.ai_timer.stop()
            self.confGauge.stop_animation()

            if self.last_frame is None:
                self.previewLabel.setText("Stopped.\nTap START to show camera.")
                self.previewLabel.setAlignment(Qt.AlignCenter)
            else:
                self._set_preview_from_rgb(self.last_frame)

    # === REPLACE YOUR EXISTING do_ai_read() WITH THIS ===
    def do_ai_read(self):
        if not self.is_running:
            return

        if self.last_frame is None:
            return

        # Ensure RGB format for model
        frame_rgb = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)

        label, confidence = self.classify_frame(frame_rgb)

        # Convert model output to UI format
        confidence_percent = confidence * 100.0
        self.confGauge.set_target(confidence_percent)

        # Grade mapping
        grade_map = {
            'G1': 'Grade 1',
            'G2': 'Grade 2',
            'G3': 'Grade 3',
            'REJ': 'Reject'
        }

        display_grade = grade_map.get(label, 'Unknown')
        self.gradeValue.setText(display_grade)

        # Accepted / Rejected logic
        if label == 'REJ':
            self.acceptedValue.setText('Rejected')
            self.acceptedValue.setStyleSheet("color:#b02a2a; font-weight:900;")
        else:
            self.acceptedValue.setText('Accepted')
            self.acceptedValue.setStyleSheet("color:#2e6b3a; font-weight:900;")

            # --- Stability Check ---
        if confidence >= self.MIN_CONFIDENCE:
            if label == self.last_label:
                self.stable_counter += 1
            else:
                self.stable_counter = 1
                self.last_label = label
        else:
            self.stable_counter = 0
            self.last_label = None

        # --- Trigger Auto Capture ---
        if (
            self.stable_counter >= self.STABLE_REQUIRED
            and not self.capture_cooldown
        ):
            self.auto_capture(label, confidence)
            self.capture_cooldown = True
            self.trigger_flash()


    def _repolish(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_preview_from_rgb(self, frame):
        if frame is None:
            return

        frame = cv2.resize(frame, (PREVIEW_W, PREVIEW_H), interpolation=cv2.INTER_AREA)

        h, w, ch = frame.shape
        bytes_per_line = ch * w

        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self.previewLabel.setPixmap(QPixmap.fromImage(qt_image))
        self.previewLabel.setAlignment(Qt.AlignCenter)

    def update_frame(self):
        if not self.is_running:
            return
        frame = self.picam2.capture_array("main")
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame = cv2.resize(frame, (PREVIEW_W, PREVIEW_H), interpolation=cv2.INTER_AREA)
        
        self.last_frame = frame
        self._set_preview_from_rgb(frame)  # name doesn't matter, data does

    def closeEvent(self, event):
        try:
            self.preview_timer.stop()
        except Exception:
            pass
        try:
            self.ai_timer.stop()
        except Exception:
            pass
        try:
            self.confGauge.stop_animation()
        except Exception:
            pass
        try:
            if hasattr(self, "picam2") and self.picam2 is not None:
                self.picam2.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def auto_capture(self, label, confidence):
        """Save frame automatically when stable detection confirmed"""

        if self.last_frame is None:
            return

        import os
        from datetime import datetime

        save_dir = "captured_batches"
        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{label}_{int(confidence*100)}_{timestamp}.jpg"
        filepath = os.path.join(save_dir, filename)

        cv2.imwrite(filepath, self.last_frame)

        print(f"[AUTO-CAPTURE] Saved: {filepath}")

        # Optional: increment batch counter visually
        current_text = self.batchLabel.text()
        try:
            num = int(current_text.split(':')[1].strip())
            num += 1
            self.batchLabel.setText(f"Batch 1: {num}")
        except Exception:
            pass

        # Reset after short delay to allow next detection
        QTimer.singleShot(5000, self.reset_capture_state)


    def reset_capture_state(self):
        self.capture_cooldown = False
        self.stable_counter = 0
        self.last_label = None



def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()