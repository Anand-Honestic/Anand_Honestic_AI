"""
core/startup_screen.py — HONESTIC OS Animated Startup Experience

Displays:
HONESTIC OS
Created By Anand_Honestic
Loading ATHENA...

Features modern smooth animations and premium Windows 11 Copilot glow.
"""

from __future__ import annotations
import math
import time
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QRadialGradient, QLinearGradient, QPen, QBrush
)
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect

from core.os_identity import (
    PROJECT_NAME, OWNER_NAME, DEFAULT_AI_NAME,
    STARTUP_TITLE, STARTUP_SUBTITLE, STARTUP_LOADING
)
from core.theme_manager import ThemeManager


class StartupOverlay(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None, assistant_name: str = DEFAULT_AI_NAME):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._asst_name = assistant_name
        self._progress = 0.0
        self._phase = 0.0

        # Query live Brain Mode
        try:
            from core.brain_router import BrainRouter
            self._brain_mode = BrainRouter.get_instance().get_mode().capitalize()
        except Exception:
            self._brain_mode = "Hybrid"

        self._greeting = self._get_founder_greeting()
        self._status_text = f"{self._asst_name} is ready."

        self._theme_mgr = ThemeManager.get_instance()

        # Animation timer (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)

        # Start time
        self._start_time = time.monotonic()
        self._duration = 2.4  # seconds

    @staticmethod
    def _get_founder_greeting() -> str:
        hr = datetime.now().hour
        if 5 <= hr < 12:
            return "Good Morning Anand."
        elif 12 <= hr < 17:
            return "Good Afternoon Anand."
        else:
            return "Good Evening Anand."

    def _on_tick(self):
        elapsed = time.monotonic() - self._start_time
        self._phase += 0.05
        self._progress = min(1.0, elapsed / self._duration)

        if self._progress > 0.7:
            self._status_text = f"{self._asst_name} is ready."
        elif self._progress > 0.4:
            self._status_text = f"Calibrating {self._asst_name} Hybrid Brain..."
        else:
            self._status_text = f"Initializing HONESTIC OS..."

        self.update()

        if elapsed >= self._duration:
            self._timer.stop()
            self._fade_out()

    def _fade_out(self):
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.finished.connect(self._on_fade_finished)
        self._anim.start()

    def _on_fade_finished(self):
        self.hide()
        self.finished.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        td = self._theme_mgr.get_theme_data()
        pri = QColor(td.get("accent", "#00d4ff"))

        # Deep ambient backdrop
        p.fillRect(0, 0, w, h, QColor(2, 6, 14, 252))

        # Ambient central aura glow
        rad = min(w, h) * 0.45
        grad = QRadialGradient(cx, cy - 40, rad)
        c_glow = QColor(pri)
        c_glow.setAlpha(int(38 + 18 * math.sin(self._phase)))
        grad.setColorAt(0.0, c_glow)
        grad.setColorAt(0.7, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(cx - rad, cy - 40 - rad, rad * 2, rad * 2))

        # Rotating orbital rings
        ring_r = 74.0
        p.save()
        p.translate(cx, cy - 60)

        # Outer ring
        p.save()
        p.rotate(self._phase * 25)
        pen_outer = QPen(QColor(pri.red(), pri.green(), pri.blue(), 120), 1.5)
        pen_outer.setDashPattern([6, 8])
        p.setPen(pen_outer)
        p.drawEllipse(QRectF(-ring_r, -ring_r, ring_r * 2, ring_r * 2))
        p.restore()

        # Inner counter-rotating ring
        p.save()
        p.rotate(-self._phase * 35)
        pen_inner = QPen(QColor(pri.red(), pri.green(), pri.blue(), 180), 2.0)
        pen_inner.setDashPattern([14, 12])
        p.setPen(pen_inner)
        p.drawEllipse(QRectF(-ring_r * 0.75, -ring_r * 0.75, ring_r * 1.5, ring_r * 1.5))
        p.restore()

        # Center core emblem
        core_r = 16.0 + 3.0 * math.sin(self._phase * 2)
        c_core = QColor(pri)
        c_core.setAlpha(220)
        p.setBrush(QBrush(c_core))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-core_r, -core_r, core_r * 2, core_r * 2))

        p.restore()

        # Founder Greeting: Good Morning Anand.
        p.setPen(QColor(255, 255, 255, 250))
        p.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        greet_rect = QRectF(0, cy + 25, w, 34)
        p.drawText(greet_rect, Qt.AlignmentFlag.AlignCenter, self._greeting)

        # Subtitle: ATHENA is ready.
        p.setPen(QColor(pri))
        p.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        asst_rect = QRectF(0, cy + 62, w, 24)
        p.drawText(asst_rect, Qt.AlignmentFlag.AlignCenter, f"✨ {self._asst_name} is ready.")

        # Founder Telemetry Glass Box
        card_w = min(480.0, w - 40.0)
        card_h = 44.0
        card_x = cx - card_w / 2.0
        card_y = cy + 96

        p.setPen(QPen(QColor(pri.red(), pri.green(), pri.blue(), 60), 1))
        p.setBrush(QBrush(QColor(15, 23, 42, 180)))
        p.drawRoundedRect(QRectF(card_x, card_y, card_w, card_h), 8, 8)

        p.setPen(QColor(203, 213, 225, 230))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        t1 = f"Project: HONESTIC OS   •   Brain: {self._brain_mode}   •   Memory: Healthy   •   Status: Operational"
        p.drawText(QRectF(card_x, card_y, card_w, card_h), Qt.AlignmentFlag.AlignCenter, t1)

        # Loading / Status Text
        p.setPen(QColor(148, 163, 184, 180))
        p.setFont(QFont("Segoe UI", 8))
        status_rect = QRectF(0, cy + 150, w, 20)
        p.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, self._status_text)

        # Smooth Progress Bar
        bar_w = 260.0
        bar_h = 3.0
        bx = cx - bar_w / 2.0
        by = cy + 175

        # Bar background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 20)))
        p.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), 2, 2)

        # Bar fill
        fill_w = bar_w * self._progress
        p.setBrush(QBrush(pri))
        p.drawRoundedRect(QRectF(bx, by, fill_w, bar_h), 2, 2)
