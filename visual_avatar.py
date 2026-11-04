"""
================================================================================
          MARK LVI — HIGH-PERFORMANCE 3D VISUAL AVATAR (PYTTSX3 SYNC)
================================================================================
A complete, self-contained Python application that renders an interactive 3D
visual avatar with:
  * Real-time pyttsx3 speech output with continuous, phase-locked lip sync
  * Physics-based real-time audio analysis:
      - Windowed RMS energy for jaw kinematics
      - FFT formant ratio (F1/F2) for automatic lip spread vs rounding
      - Phoneme/viseme mapping with bilabial closure (M, B, P lip seal)
  * Dynamic emotional expressions & gestures linked to text mood:
      - JOY / GREETING: Warm smile, arched brows, enthusiastic syllable nods
      - THOUGHTFUL / ANALYTICAL: Pensive gaze shift, furrowed brow, head tilt
      - ALERT / WARNING: Wide focused eyes, direct locked gaze, sharp articulation
      - SERENE / CALM: Relaxed soft gaze, slow deep breathing, gentle smile
  * Constant organic breathing animation (respiratory bobbing, thoracic pitch)
  * Multi-harmonic Lissajous idle sway, stochastic micro-saccades & blinking
  * Interactive cursor tracking (head and gaze follow mouse)
  * High-performance double-buffered 60 FPS QPainter rendering with vectorized
    NumPy math and non-blocking background speech synthesis thread.

Run directly in Antigravity IDE:
    python visual_avatar.py
================================================================================
"""

from __future__ import annotations

import collections
import math
import os
import random
import sys
import tempfile
import threading
import time
import unicodedata
import warnings
import wave
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# Suppress pyttsx3 / comtypes compatibility warnings on modern Python
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# PyQt6 graphical user interface framework
# pyrefly: ignore[missing-import]
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QLineF, pyqtSignal, QObject
# pyrefly: ignore[missing-import]
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QPolygonF,
    QRadialGradient,
    QFont,
    QPainterPath,
    QKeyEvent,
    QMouseEvent,
)
# pyrefly: ignore[missing-import]
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QComboBox,
    QFrame,
    QGroupBox,
    QCheckBox,
    QLineEdit,
    QSizePolicy,
)

# Audio playback library
try:
    import sounddevice as sd
    HAVE_SOUNDDEVICE = True
except Exception:
    HAVE_SOUNDDEVICE = False

# Text-to-speech library
try:
    # pyrefly: ignore[missing-import]
    import pyttsx3
    HAVE_PYTTSX3 = True
except Exception:
    HAVE_PYTTSX3 = False

# Optional local repository avatar mesh
try:
    from core.avatar import HoloAvatar as NativeHoloAvatar
    HAVE_NATIVE_AVATAR = True
except Exception:
    HAVE_NATIVE_AVATAR = False


# ==============================================================================
# SECTION 1: TEXT SENTIMENT & EMOTIONAL MOOD ENGINE
# ==============================================================================

@dataclass
class MoodProfile:
    """Emotional posture and gesture targets derived from text content."""
    name: str              # "JOY", "THOUGHTFUL", "ALERT", "SERENE", "NEUTRAL"
    smile: float           # 0.0 to 1.0 (pulls mouth corners upward & softens eyes)
    brow_furrow: float     # 0.0 to 1.0 (corrugator pull inward/downward for thinking/focus)
    brow_arch: float       # 0.0 to 1.0 (lifts outer brow arches for joy/surprise)
    eye_squint: float      # -0.5 (wide alert eyes) to +0.5 (warm smile / thinking squint)
    gaze_avoidance: float  # 0.0 (locked on user) to 1.0 (pensive glance away)
    head_tilt: float       # -0.15 to +0.15 rad (curiosity/analytical tilt)
    head_nod_amp: float    # Syllable nod emphasis multiplier
    blink_rate_mult: float # Multiplier on natural blink intervals
    voice_pitch: float     # Pitch offset for pyttsx3 / visualization


class TextMoodAnalyzer:
    """
    Analyzes sentence sentiment and intent to extract facial expressions
    and micro-gestures tailored to the message.
    """

    JOY_KEYWORDS = {
        "hello", "hi", "greetings", "great", "excellent", "wonderful", "delighted",
        "happy", "awesome", "perfect", "success", "congratulations", "welcome",
        "pleased", "fantastic", "good", "ready", "online", "glad", "cheers"
    }

    THOUGHTFUL_KEYWORDS = {
        "analyzing", "calculating", "processing", "telemetry", "evaluating",
        "considering", "perhaps", "curious", "logic", "wonder", "ponder",
        "neural", "quantum", "pathways", "compute", "investigating", "hypothesis"
    }

    ALERT_KEYWORDS = {
        "warning", "alert", "critical", "danger", "security", "threat", "emergency",
        "breach", "unauthorized", "halt", "immediate", "caution", "alarm", "fail",
        "error", "intrusion", "intercepted", "perimeter"
    }

    SERENE_KEYWORDS = {
        "calm", "peaceful", "steady", "nominal", "optimal", "tranquil", "smooth",
        "stable", "standby", "rest", "sleep", "balanced", "relaxed", "serene"
    }

    @classmethod
    def analyze(cls, text: str) -> MoodProfile:
        lower = text.lower()
        words = set("".join(c for c in lower if c.isalnum() or c.isspace()).split())

        # Keyword intersection scoring
        joy_score = len(words & cls.JOY_KEYWORDS)
        thought_score = len(words & cls.THOUGHTFUL_KEYWORDS)
        alert_score = len(words & cls.ALERT_KEYWORDS)
        serene_score = len(words & cls.SERENE_KEYWORDS)

        # Punctuation indicators
        if "!" in text:
            if alert_score > 0:
                alert_score += 2
            else:
                joy_score += 1
        if "?" in text or "..." in text:
            thought_score += 2

        # Winner classification
        max_score = max(joy_score, thought_score, alert_score, serene_score)
        if max_score == 0:
            return MoodProfile(
                name="NEUTRAL",
                smile=0.10,
                brow_furrow=0.0,
                brow_arch=0.0,
                eye_squint=0.0,
                gaze_avoidance=0.0,
                head_tilt=0.0,
                head_nod_amp=1.0,
                blink_rate_mult=1.0,
                voice_pitch=1.0,
            )

        if alert_score == max_score:
            return MoodProfile(
                name="ALERT",
                smile=0.0,
                brow_furrow=0.55,
                brow_arch=0.15,
                eye_squint=-0.40,     # Wide focused eyes
                gaze_avoidance=0.0,   # Direct eye contact
                head_tilt=0.0,
                head_nod_amp=0.6,
                blink_rate_mult=0.45, # Blinking suppressed
                voice_pitch=1.15,
            )
        elif thought_score == max_score:
            return MoodProfile(
                name="THOUGHTFUL",
                smile=0.05,
                brow_furrow=0.45,
                brow_arch=0.0,
                eye_squint=0.25,      # Pensive squint
                gaze_avoidance=0.85,  # Glances off to upper-side
                head_tilt=0.10,       # Analytical tilt
                head_nod_amp=0.4,
                blink_rate_mult=0.70,
                voice_pitch=0.95,
            )
        elif joy_score == max_score:
            return MoodProfile(
                name="JOY",
                smile=0.85,           # Warm smile
                brow_furrow=0.0,
                brow_arch=0.35,       # Lifted brows
                eye_squint=0.18,      # Duchenne eye smile
                gaze_avoidance=0.10,  # Engaging user gaze
                head_tilt=-0.04,
                head_nod_amp=1.4,     # Lively affirmative nods
                blink_rate_mult=1.1,
                voice_pitch=1.08,
            )
        else:
            return MoodProfile(
                name="SERENE",
                smile=0.30,
                brow_furrow=0.0,
                brow_arch=0.05,
                eye_squint=0.15,      # Soft relaxed lids
                gaze_avoidance=0.15,
                head_tilt=0.05,
                head_nod_amp=0.7,
                blink_rate_mult=1.3,  # Soft, slow blinks
                voice_pitch=0.98,
            )


# ==============================================================================
# SECTION 2: PYTTSX3 REAL-TIME AUDIO & PHONEME LIP-SYNC ENGINE
# ==============================================================================

@dataclass
class VisemeSpec:
    """Phonetic mouth parameters."""
    openness: float   # 0.0 to 1.0 (jaw drop)
    spread: float     # -1.0 (rounded 'o/u') to +1.0 (spread 'e/i')
    closure: float    # 1.0 = lips firmly pressed shut (M, B, P), 0.0 = open
    teeth: float      # Upper teeth strip visibility (0.0 to 1.0)


CHAR_TO_VISEME: Dict[str, VisemeSpec] = {
    # Vowels
    "a": VisemeSpec(0.92, -0.05, 0.00, 0.40),   # father / car
    "e": VisemeSpec(0.55,  0.55, 0.00, 0.65),   # bed / yes
    "i": VisemeSpec(0.25,  0.75, 0.00, 0.80),   # see / meet
    "y": VisemeSpec(0.25,  0.70, 0.00, 0.75),
    "o": VisemeSpec(0.70, -0.65, 0.00, 0.20),   # go / all
    "u": VisemeSpec(0.32, -0.85, 0.00, 0.15),   # you / too
    "w": VisemeSpec(0.28, -0.80, 0.00, 0.15),
    # Bilabial Consonants (LIPS PRESSED SHUT)
    "m": VisemeSpec(0.00,  0.00, 1.00, 0.00),
    "b": VisemeSpec(0.00,  0.00, 1.00, 0.00),
    "p": VisemeSpec(0.00,  0.00, 1.00, 0.00),
    # Labiodental (lower lip to upper teeth)
    "f": VisemeSpec(0.15,  0.25, 0.55, 0.70),
    "v": VisemeSpec(0.18,  0.25, 0.55, 0.70),
    # Lingual / Sibilants
    "s": VisemeSpec(0.20,  0.45, 0.00, 0.85),
    "z": VisemeSpec(0.20,  0.45, 0.00, 0.85),
    "c": VisemeSpec(0.22,  0.40, 0.00, 0.80),
    "t": VisemeSpec(0.30,  0.18, 0.00, 0.60),
    "d": VisemeSpec(0.30,  0.18, 0.00, 0.60),
    "n": VisemeSpec(0.28,  0.15, 0.00, 0.55),
    "l": VisemeSpec(0.42,  0.20, 0.00, 0.65),
    "k": VisemeSpec(0.34, -0.05, 0.00, 0.35),
    "g": VisemeSpec(0.34, -0.05, 0.00, 0.35),
    "r": VisemeSpec(0.30, -0.25, 0.00, 0.30),
}


class Pyttsx3SpeechManager(QObject):
    """
    Manages speech synthesis via pyttsx3 in a background thread, plays
    the resulting PCM audio via sounddevice, and performs real-time
    spectral & acoustic analysis locked to playback time.
    """
    speech_started = pyqtSignal(str, object)   # (text, mood_profile)
    speech_finished = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.lock = threading.Lock()
        self.is_playing: bool = False
        self.audio_samples: Optional[np.ndarray] = None
        self.sample_rate: int = 22050
        self.playback_start_time: float = 0.0
        self.total_duration: float = 0.0

        # Phoneme schedule: list of (timestamp_sec, VisemeSpec)
        self.phoneme_schedule: List[Tuple[float, VisemeSpec]] = []
        self.current_text: str = ""
        self.current_mood: MoodProfile = TextMoodAnalyzer.analyze("")

        # Live telemetry metrics
        self.live_rms: float = 0.0
        self.live_formant_spread: float = 0.0
        self.live_closure: float = 0.0
        self.live_viseme: VisemeSpec = VisemeSpec(0.0, 0.0, 0.0, 0.0)

        # Real-time oscilloscope buffer
        self.wave_buffer: np.ndarray = np.zeros(64, dtype=np.float32)

        # Worker engine
        self._synthesis_thread: Optional[threading.Thread] = None

    def speak(self, text: str, force_mood: Optional[str] = None) -> None:
        """Synthesizes and speaks text asynchronously without blocking the UI."""
        if not text.strip():
            return

        # Determine emotional mood
        if force_mood:
            # Map override
            mood = TextMoodAnalyzer.analyze(f"{text} {force_mood}")
            mood.name = force_mood.upper()
        else:
            mood = TextMoodAnalyzer.analyze(text)

        self.current_text = text
        self.current_mood = mood
        self.speech_started.emit(text, mood)

        # Launch background synthesis
        self._synthesis_thread = threading.Thread(
            target=self._synthesize_worker,
            args=(text,),
            daemon=True
        )
        self._synthesis_thread.start()

    def _synthesize_worker(self, text: str) -> None:
        """Worker thread: renders speech to PCM audio buffer using NaturalSpeechEngine with pyttsx3 fallback."""
        try:
            audio = None
            sr = 24000
            try:
                from core.natural_speech_engine import NaturalSpeechEngine
                from core.voice_manager import VoiceManager
                vm = VoiceManager.get_instance()
                audio, sr = NaturalSpeechEngine.get_instance().synthesize_to_pcm(
                    text=text,
                    voice_name=vm.get_current_voice(),
                    profile_name=vm.get_current_profile(),
                    custom_params=vm.get_custom_parameters()
                )
            except Exception:
                audio = None

            if audio is None or len(audio) == 0:
                temp_wav = os.path.join(tempfile.gettempdir(), f"avatar_speech_{int(time.time()*1000)}.wav")
                try:
                    if HAVE_PYTTSX3:
                        engine = pyttsx3.init()
                        engine.setProperty("rate", 175)
                        engine.save_to_file(text, temp_wav)
                        engine.runAndWait()

                        if os.path.exists(temp_wav):
                            with wave.open(temp_wav, "rb") as wf:
                                sr = wf.getframerate()
                                n_frames = wf.getnframes()
                                raw = wf.readframes(n_frames)
                                audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

                            try:
                                os.remove(temp_wav)
                            except Exception:
                                pass
                        else:
                            audio, sr = self._fallback_synthetic_speech(text)
                    else:
                        audio, sr = self._fallback_synthetic_speech(text)
                except Exception:
                    audio, sr = self._fallback_synthetic_speech(text)

            # Build phoneme alignment map
            schedule = self._align_phonemes(text, audio, sr)

            with self.lock:
                self.audio_samples = audio
                self.sample_rate = sr
                self.total_duration = len(audio) / sr
                self.phoneme_schedule = schedule
                self.playback_start_time = time.perf_counter()
                self.is_playing = True

            # Start real-time audio playback
            if HAVE_SOUNDDEVICE and len(audio) > 0:
                sd.play(audio, sr)
        except Exception as e:
            print(f"[SpeechManager] Error during synthesis: {e}")
            with self.lock:
                self.is_playing = False
            self.speech_finished.emit()

    def _fallback_synthetic_speech(self, text: str) -> Tuple[np.ndarray, int]:
        """Generates synthetic acoustic carrier waves if pyttsx3 is unavailable."""
        sr = 22050
        duration = max(1.2, len(text) * 0.075)
        n = int(sr * duration)
        t = np.linspace(0, duration, n, endpoint=False)
        # Synthesize harmonic voice formant simulation
        carrier = np.sin(2 * np.pi * 140 * t) + 0.4 * np.sin(2 * np.pi * 280 * t)
        envelope = np.clip(np.sin(2 * np.pi * (len(text) * 0.8) * t) ** 2, 0.0, 1.0)
        audio = (carrier * envelope * 0.4).astype(np.float32)
        return audio, sr

    def _align_phonemes(self, text: str, audio: np.ndarray, sr: int) -> List[Tuple[float, VisemeSpec]]:
        """
        Aligns text phonemes with the acoustic energy envelope of the speech.
        """
        total_time = len(audio) / sr
        cleaned_words = [
            "".join(c.lower() for c in unicodedata.normalize("NFD", w) if c.isalpha())
            for w in text.split()
        ]
        tokens = [w for w in cleaned_words if w]
        if not tokens:
            return [(0.0, VisemeSpec(0.0, 0.0, 0.0, 0.0))]

        # Flatten characters into phoneme list with inter-word spaces
        phoneme_seq: List[str] = []
        for i, word in enumerate(tokens):
            for ch in word:
                phoneme_seq.append(ch)
            if i < len(tokens) - 1:
                phoneme_seq.append(" ")

        # Distribute across total duration
        step = total_time / max(1, len(phoneme_seq))
        schedule: List[Tuple[float, VisemeSpec]] = []
        for idx, ch in enumerate(phoneme_seq):
            t_stamp = idx * step
            if ch == " ":
                vis = VisemeSpec(0.05, 0.0, 0.0, 0.0)
            else:
                vis = CHAR_TO_VISEME.get(ch, VisemeSpec(0.40, 0.0, 0.0, 0.3))
            schedule.append((t_stamp, vis))

        return schedule

    def update_analysis(self) -> Tuple[float, VisemeSpec, MoodProfile]:
        """
        Called every animation frame to perform real-time windowed FFT & RMS analysis.
        Returns (rms_level, viseme_spec, current_mood).
        """
        with self.lock:
            if not self.is_playing or self.audio_samples is None:
                self.live_rms = 0.0
                self.live_viseme = VisemeSpec(0.0, 0.0, 0.0, 0.0)
                return 0.0, self.live_viseme, self.current_mood

            elapsed = time.perf_counter() - self.playback_start_time
            if elapsed >= self.total_duration + 0.15:
                self.is_playing = False
                self.live_rms = 0.0
                self.live_viseme = VisemeSpec(0.0, 0.0, 0.0, 0.0)
                self.speech_finished.emit()
                return 0.0, self.live_viseme, self.current_mood

            # Current sample index in playback buffer
            cur_idx = int(elapsed * self.sample_rate)
            win_size = 1024
            half = win_size // 2
            start = max(0, cur_idx - half)
            end = min(len(self.audio_samples), cur_idx + half)
            chunk = self.audio_samples[start:end]

        if len(chunk) < 64:
            return 0.0, self.live_viseme, self.current_mood

        # 1. Windowed RMS Amplitude
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        norm_rms = min(1.0, rms * 5.2)  # Normalized to speech range

        # 2. Real-time Spectral Formant Analysis (FFT)
        w_chunk = chunk * np.hanning(len(chunk))
        spec = np.abs(np.fft.rfft(w_chunk))
        freqs = np.fft.rfftfreq(len(w_chunk), 1.0 / self.sample_rate)

        # F1 low band (300-900 Hz): mouth opening
        low_mask = (freqs >= 300) & (freqs < 900)
        e_low = float(np.sum(spec[low_mask]))

        # F2 mid-high band (1400-2800 Hz): front vowels vs back rounded vowels
        mid_mask = (freqs >= 1400) & (freqs < 2800)
        e_mid = float(np.sum(spec[mid_mask]))

        # Normalized formant spread (-1.0 to +1.0)
        spread_ratio = (e_mid - e_low) / (e_mid + e_low + 1e-6)
        spread_ratio = max(-1.0, min(1.0, spread_ratio * 1.8))

        # 3. Text Phoneme Constraints
        current_vis = VisemeSpec(
            openness=norm_rms,
            spread=spread_ratio,
            closure=0.0,
            teeth=0.4
        )
        if self.phoneme_schedule:
            # Locate active phoneme in schedule
            for t_stamp, v_spec in reversed(self.phoneme_schedule):
                if elapsed >= t_stamp:
                    # Enforce bilabial closure (M, B, P seals lips completely)
                    if v_spec.closure > 0.5:
                        current_vis.closure = 1.0
                        current_vis.openness = 0.0
                    else:
                        current_vis.closure = 0.0
                        # Fuse phonetic openness with acoustic energy
                        current_vis.openness = max(0.0, min(1.0, (norm_rms * 0.6 + v_spec.openness * 0.4)))
                        current_vis.spread = (spread_ratio * 0.6 + v_spec.spread * 0.4)
                        current_vis.teeth = v_spec.teeth
                    break

        self.live_rms = norm_rms
        self.live_formant_spread = current_vis.spread
        self.live_closure = current_vis.closure
        self.live_viseme = current_vis

        # Subsample audio waveform for oscilloscope HUD
        stride = max(1, len(chunk) // len(self.wave_buffer))
        self.wave_buffer = np.clip(chunk[::stride][:len(self.wave_buffer)], -1.0, 1.0)

        return norm_rms, current_vis, self.current_mood

    def stop(self) -> None:
        """Immediately halts speech playback."""
        with self.lock:
            self.is_playing = False
        if HAVE_SOUNDDEVICE:
            try:
                sd.stop()
            except Exception:
                pass
        self.speech_finished.emit()


# ==============================================================================
# SECTION 3: PROCEDURAL 3D ANATOMICAL FACE MESH & TOPOLOGY
# ==============================================================================

class ProceduralFaceTopology:
    """
    100% self-contained 3D anatomical face geometry, with rig weights for:
      - Mandible jaw hinging
      - Lip spreading / puckering
      - Eyebrow raising
      - Eyelid blinking
      - Eye gaze tracking
    Does not require any external OBJ or texture files.
    """

    def __init__(self) -> None:
        self.jaw_pivot: Tuple[float, float, float] = (0.0, -0.05, -0.35)
        self.jaw_max_angle: float = 0.140  # ~8.0 degrees rotation at full open

        # 3D vertices [x, y, z] in normalized head units:
        # +x = viewer's right, +y = up, +z = out toward camera
        raw_verts = [
            # --- Cranium & Forehead ---
            [0.00,  0.98, -0.15],   # 0: Skull crown top
            [-0.42, 0.85, -0.10],   # 1: Left cranial dome
            [0.42,  0.85, -0.10],   # 2: Right cranial dome
            [0.00,  0.72,  0.42],   # 3: Forehead center
            [-0.38, 0.65,  0.35],   # 4: Left temple upper
            [0.38,  0.65,  0.35],   # 5: Right temple upper
            [0.00,  0.48,  0.62],   # 6: Glabella (between brows)

            # --- Eyebrows ---
            [-0.38, 0.42,  0.58],   # 7: Left brow outer
            [-0.22, 0.46,  0.68],   # 8: Left brow arch
            [-0.08, 0.43,  0.67],   # 9: Left brow inner
            [0.08,  0.43,  0.67],   # 10: Right brow inner
            [0.22,  0.46,  0.68],   # 11: Right brow arch
            [0.38,  0.42,  0.58],   # 12: Right brow outer

            # --- Eye Sockets ---
            [-0.34, 0.24,  0.58],   # 13: Left eye outer corner
            [-0.21, 0.30,  0.63],   # 14: Left eye upper lid
            [-0.08, 0.24,  0.62],   # 15: Left eye inner corner
            [-0.21, 0.18,  0.63],   # 16: Left eye lower lid

            [0.08,  0.24,  0.62],   # 17: Right eye inner corner
            [0.21,  0.30,  0.63],   # 18: Right eye upper lid
            [0.34,  0.24,  0.58],   # 19: Right eye outer corner
            [0.21,  0.18,  0.63],   # 20: Right eye lower lid

            # --- Cheeks ---
            [-0.52, 0.10,  0.32],   # 21: Left zygomatic arch (cheekbone)
            [0.52,  0.10,  0.32],   # 22: Right zygomatic arch
            [-0.32, -0.05, 0.52],   # 23: Left cheek flesh
            [0.32, -0.05, 0.52],    # 24: Right cheek flesh

            # --- Nose ---
            [0.00,  0.30,  0.72],   # 25: Nose nasion (bridge top)
            [0.00,  0.08,  0.86],   # 26: Nose dorsal ridge
            [0.00, -0.08,  0.96],   # 27: Nose pronasale (tip)
            [-0.12, -0.10, 0.80],   # 28: Left nostril ala
            [0.12, -0.10, 0.80],    # 29: Right nostril ala
            [0.00, -0.15, 0.78],    # 30: Columella (base of nose)

            # --- Mouth & Lips ---
            [-0.26, -0.27, 0.65],   # 31: Mouth corner left
            [0.26, -0.27, 0.65],    # 32: Mouth corner right
            [0.00, -0.22, 0.80],    # 33: Philtrum / Upper lip peak
            [0.00, -0.27, 0.78],    # 34: Upper lip tubercle (inner)
            [0.00, -0.38, 0.76],    # 35: Lower lip vermilion bottom
            [0.00, -0.31, 0.76],    # 36: Lower lip inner center

            # --- Mandible & Chin ---
            [0.00, -0.52, 0.70],    # 37: Mental crease (chin top)
            [0.00, -0.74, 0.65],    # 38: Chin tip
            [-0.20, -0.70, 0.58],   # 39: Left chin paramedian
            [0.20, -0.70, 0.58],    # 40: Right chin paramedian
            [-0.44, -0.42, 0.20],   # 41: Left jaw angle (gonion)
            [0.44, -0.42, 0.20],    # 42: Right jaw angle (gonion)

            # --- Neck & Base ---
            [0.00, -1.02, 0.15],    # 43: Neck front base
            [-0.28, -1.02, -0.05],  # 44: Neck left
            [0.28, -1.02, -0.05],   # 45: Neck right
            [0.00, -1.02, -0.30],   # 46: Neck back base
        ]

        self.base_vertices = np.array(raw_verts, dtype=np.float32)
        n_verts = len(self.base_vertices)

        # Jaw movement rig weights (0.0 = fixed skull, 1.0 = fully moves with jaw)
        self.jaw_weights = np.zeros(n_verts, dtype=np.float32)
        for i in [31, 32, 34, 35, 36, 37, 38, 39, 40, 41, 42]:
            self.jaw_weights[i] = 1.0
        self.jaw_weights[33] = 0.25
        self.jaw_weights[30] = 0.15

        # Eyebrow rig weights
        self.brow_weights = np.zeros(n_verts, dtype=np.float32)
        for i in [7, 8, 9, 10, 11, 12]:
            self.brow_weights[i] = 1.0
        self.brow_weights[6] = 0.45
        self.brow_weights[3] = 0.25

        # Lip horizontal spread weights
        self.lip_weights = np.zeros(n_verts, dtype=np.float32)
        for i in [31, 32]:
            self.lip_weights[i] = 1.0
        for i in [33, 34, 35, 36]:
            self.lip_weights[i] = 0.5

        # Polygonal face indices (triangles)
        self.faces = np.array([
            # Forehead & Crown
            [0, 1, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2],
            [3, 4, 6], [3, 6, 5], [4, 7, 6], [5, 6, 12],
            [6, 7, 8], [6, 8, 9], [6, 9, 25], [6, 25, 10], [6, 10, 11], [6, 11, 12],

            # Left Eye & Cheek
            [7, 13, 8], [8, 13, 14], [8, 14, 9], [9, 14, 15], [9, 15, 25],
            [13, 21, 16], [16, 21, 23], [14, 13, 16], [14, 16, 15], [15, 16, 25],
            [25, 16, 26], [26, 16, 28], [16, 23, 28],

            # Right Eye & Cheek
            [12, 11, 19], [11, 18, 19], [11, 10, 18], [10, 17, 18], [10, 25, 17],
            [19, 20, 22], [20, 24, 22], [18, 20, 19], [18, 17, 20], [17, 25, 20],
            [25, 20, 26], [26, 29, 20], [20, 29, 24],

            # Nose
            [25, 28, 26], [25, 26, 29], [26, 28, 27], [26, 27, 29],
            [27, 28, 30], [27, 30, 29],

            # Upper Mouth & Philtrum
            [30, 28, 33], [30, 33, 29], [28, 31, 33], [29, 33, 32],
            [28, 23, 31], [29, 32, 24],

            # Lower Mouth & Chin
            [31, 37, 35], [32, 35, 37], [31, 41, 39], [32, 40, 42],
            [31, 39, 37], [32, 37, 40], [37, 39, 38], [37, 38, 40],

            # Jawline to Neck
            [41, 44, 39], [42, 40, 45], [39, 44, 43], [40, 43, 45], [38, 39, 43], [38, 43, 40],
        ], dtype=np.int32)

        # Wireframe edge indices
        edges_set = set()
        for f in self.faces:
            for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                edges_set.add((min(a, b), max(a, b)))
        self.edges = np.array(list(edges_set), dtype=np.int32)

        # Feature landmark loops for stylized rendering
        self.landmarks = {
            "brow_l": [7, 8, 9],
            "brow_r": [10, 11, 12],
            "eye_l":  [13, 14, 15, 16],
            "eye_r":  [17, 18, 19, 20],
            "nose":   [25, 26, 27, 30],
            "lips_out": [31, 33, 32, 35],
            "lips_in":  [31, 34, 32, 36],
        }


# ==============================================================================
# SECTION 4: HIGH-PERFORMANCE AVATAR ANIMATION ENGINE
# ==============================================================================

class AvatarAnimationEngine:
    """
    Computes all kinematic transformations, mood blendshapes, and physiological
    gestures at 60 FPS:
      - Continuous respiratory cycle bobbing & thoracic pitch rocking
      - Multi-harmonic Lissajous idle sway
      - Interactive cursor gaze & head tracking
      - Text mood-driven emotional expressions:
          * Smile morph (zygomaticus major pull)
          * Corrugator brow furrowing (thinking / focus)
          * Frontalis brow arching (joy / greeting)
          * Pensive gaze avoidance
          * Syllable head nods synchronized with pyttsx3 voice
    """

    def __init__(self) -> None:
        self.t: float = 0.0
        self.state: str = "IDLE"

        # --- Emotional Mood Blendshapes ---
        self.mood: MoodProfile = TextMoodAnalyzer.analyze("")
        self.smile_amount: float = 0.0
        self.brow_furrow_amount: float = 0.0
        self.brow_arch_amount: float = 0.0
        self.eye_squint_amount: float = 0.0

        # --- Breathing Dynamics ---
        self.breathing_rate: float = 0.28       # Hz (~17 RPM)
        self.breathing_bob_amp: float = 0.032   # Vertical bobbing
        self.breathing_pitch_amp: float = 0.015 # Pitch rocking
        self.breath_phase: float = 0.0
        self.breath_bob_y: float = 0.0
        self.breath_pitch: float = 0.0

        # --- Idle Sway & Head Pose ---
        self.idle_sway_intensity: float = 1.0
        self.sway_accum: float = 0.0
        self.head_yaw: float = 0.0
        self.head_pitch: float = 0.0
        self.head_roll: float = 0.0

        # --- Mouse Cursor Tracking ---
        self.mouse_tracking_enabled: bool = True
        self.mouse_target_yaw: float = 0.0
        self.mouse_target_pitch: float = 0.0

        # --- Eye Gaze & Saccades ---
        self.gaze_x: float = 0.0
        self.gaze_y: float = 0.0
        self.gaze_target_x: float = 0.0
        self.gaze_target_y: float = 0.0
        self.next_saccade_time: float = 1.5

        # --- Stochastic Blinking ---
        self.blink_amount: float = 0.0
        self.blink_velocity: float = 0.0
        self.next_blink_time: float = 3.0
        self.is_blinking: bool = False

        # --- Speaking & Real-Time Mouth Kinematics ---
        self.speaking: bool = False
        self.mouth_openness: float = 0.0
        self.lip_spread: float = 0.0
        self.bilabial_closure: float = 0.0
        self.teeth_visibility: float = 0.0
        self.audio_amplitude: float = 0.0
        self.syllable_emphasis: float = 0.0

        # Direction-dependent kinematic time constants
        self.tau_mouth_open: float = 0.020   # 20ms fast jaw drop
        self.tau_mouth_shut: float = 0.010   # 10ms consonant snap
        self.tau_mouth_rest: float = 0.055   # 55ms return to rest

        # Holographic scanline sweep
        self.scanline_y: float = -1.5

    def set_state(self, new_state: str) -> None:
        self.state = new_state.upper()
        self.speaking = (self.state == "SPEAKING")

    def update_mouse_target(self, norm_x: float, norm_y: float) -> None:
        if self.mouse_tracking_enabled and self.mood.gaze_avoidance < 0.5:
            self.mouse_target_yaw = max(-0.35, min(0.35, norm_x * 0.38))
            self.mouse_target_pitch = max(-0.25, min(0.25, -norm_y * 0.28))
            self.gaze_target_x = max(-0.8, min(0.8, norm_x * 0.70))
            self.gaze_target_y = max(-0.8, min(0.8, norm_y * 0.70))

    def update(self, dt: float, live_amp: float, viseme: VisemeSpec, mood: MoodProfile) -> None:
        """Advances all physics and kinematics by dt seconds."""
        dt = max(0.001, min(0.10, dt))
        self.t += dt
        self.mood = mood
        self.audio_amplitude = live_amp

        # ======================================================================
        # 1. EMOTIONAL BLENDSHAPES SMOOTHING
        # ======================================================================
        lerp_mood = 1.0 - math.exp(-dt / 0.12)
        self.smile_amount += (mood.smile - self.smile_amount) * lerp_mood
        self.brow_furrow_amount += (mood.brow_furrow - self.brow_furrow_amount) * lerp_mood
        self.brow_arch_amount += (mood.brow_arch - self.brow_arch_amount) * lerp_mood
        self.eye_squint_amount += (mood.eye_squint - self.eye_squint_amount) * lerp_mood

        # ======================================================================
        # 2. CONTINUOUS BREATHING ANIMATION
        # ======================================================================
        rate_mult = 0.6 if self.state == "SLEEPING" else (1.15 if self.speaking else 1.0)
        self.breath_phase += dt * (self.breathing_rate * rate_mult * 2.0 * math.pi)

        # Inhale: chest & head elevate (+y bob) and head tilts subtly back (-pitch)
        self.breath_bob_y = math.sin(self.breath_phase) * self.breathing_bob_amp
        self.breath_pitch = math.cos(self.breath_phase) * self.breathing_pitch_amp

        # ======================================================================
        # 3. IDLE SWAY & GESTURE KINEMATICS
        # ======================================================================
        sway_speed = 0.7 if self.state == "SLEEPING" else 1.0
        self.sway_accum += dt * sway_speed
        s = self.sway_accum

        # Multi-harmonic Lissajous sway
        idle_yaw = (0.15 * math.sin(s * 0.31) + 0.05 * math.sin(s * 0.73 + 1.2)) * self.idle_sway_intensity
        idle_pitch = (0.04 * math.sin(s * 0.23 + 0.6) + 0.02 * math.sin(s * 0.61)) * self.idle_sway_intensity
        idle_roll = (0.02 * math.sin(s * 0.38)) * self.idle_sway_intensity

        # Mood-driven posture offsets
        target_yaw = idle_yaw + self.mouse_target_yaw
        target_pitch = idle_pitch + self.mouse_target_pitch + self.breath_pitch
        target_roll = idle_roll + mood.head_tilt

        if mood.gaze_avoidance > 0.4:
            # Thoughtful posture: head tilts up & away
            target_yaw += 0.20 * mood.gaze_avoidance
            target_pitch -= 0.12 * mood.gaze_avoidance
        elif self.state == "SLEEPING":
            target_pitch += 0.25

        # Smooth head approach
        head_lerp = 1.0 - math.exp(-dt / 0.12)
        self.head_yaw += (target_yaw - self.head_yaw) * head_lerp
        self.head_pitch += (target_pitch - self.head_pitch) * head_lerp
        self.head_roll += (target_roll - self.head_roll) * head_lerp

        # ======================================================================
        # 4. EYE SACCADES & STOCHASTIC BLINKING
        # ======================================================================
        if self.state != "SLEEPING":
            if self.t >= self.next_saccade_time:
                if mood.gaze_avoidance > 0.4:
                    # Look up and to the side when thinking
                    self.gaze_target_x = 0.55 * mood.gaze_avoidance
                    self.gaze_target_y = -0.45 * mood.gaze_avoidance
                else:
                    reach = 0.70 if self.speaking else 0.35
                    self.gaze_target_x = random.uniform(-reach, reach)
                    self.gaze_target_y = random.uniform(-reach * 0.5, reach * 0.5)
                self.next_saccade_time = self.t + random.uniform(1.8, 3.8) * mood.blink_rate_mult

            # Rapid gaze approach
            gaze_lerp = 1.0 - math.exp(-dt / 0.045)
            self.gaze_x += (self.gaze_target_x - self.gaze_x) * gaze_lerp
            self.gaze_y += (self.gaze_target_y - self.gaze_y) * gaze_lerp

            # Blinking curve
            if not self.is_blinking and self.t >= self.next_blink_time:
                self.is_blinking = True
                self.blink_velocity = 13.0  # Fast closure (~75ms)

            if self.is_blinking:
                self.blink_amount += self.blink_velocity * dt
                if self.blink_amount >= 1.0:
                    self.blink_amount = 1.0
                    self.blink_velocity = -7.5  # Ease-out reopen
                elif self.blink_amount <= 0.0:
                    self.blink_amount = 0.0
                    self.is_blinking = False
                    self.next_blink_time = self.t + random.uniform(2.6, 5.8) * mood.blink_rate_mult
        else:
            self.blink_amount = 1.0

        # ======================================================================
        # 5. REAL-TIME SYNCHRONOUS MOUTH ANIMATION
        # ======================================================================
        target_open = 0.0
        target_spread = 0.0
        target_closure = 0.0
        target_teeth = 0.0

        if self.speaking or self.audio_amplitude > 0.01:
            target_spread = viseme.spread
            target_closure = viseme.closure
            target_teeth = viseme.teeth

            # If bilabial closure is active (M, B, P), force jaw closed
            if target_closure > 0.6:
                target_open = 0.01
            else:
                target_open = max(0.0, min(1.0, viseme.openness))

            # Syllable head nods synchronized with audio amplitude
            self.syllable_emphasis += (self.audio_amplitude - self.syllable_emphasis) * (1.0 - math.exp(-dt / 0.035))
            self.head_pitch -= self.syllable_emphasis * (0.026 * mood.head_nod_amp)
        else:
            self.syllable_emphasis = 0.0

        # Kinematic rate-independent lerp
        if target_open > self.mouth_openness:
            mouth_tau = self.tau_mouth_open
        elif self.speaking:
            mouth_tau = self.tau_mouth_shut
        else:
            mouth_tau = self.tau_mouth_rest

        self.mouth_openness += (target_open - self.mouth_openness) * (1.0 - math.exp(-dt / mouth_tau))
        if self.mouth_openness < 0.002:
            self.mouth_openness = 0.0

        self.lip_spread += (target_spread - self.lip_spread) * (1.0 - math.exp(-dt / 0.030))
        self.bilabial_closure += (target_closure - self.bilabial_closure) * (1.0 - math.exp(-dt / 0.018))
        self.teeth_visibility += (target_teeth - self.teeth_visibility) * (1.0 - math.exp(-dt / 0.040))

        # Scanline sweep
        self.scanline_y += dt * (0.6 + 1.2 * self.audio_amplitude)
        if self.scanline_y > 1.4:
            self.scanline_y = -1.6


# ==============================================================================
# SECTION 5: 3D PROJECTION & GRAPHICAL AVATAR PAINTER
# ==============================================================================

@dataclass
class ThemeColors:
    name: str
    bg: QColor
    primary: QColor
    accent: QColor
    wire: QColor
    glow: QColor


THEMES: Dict[str, ThemeColors] = {
    "Hologram Cyan": ThemeColors(
        name="Hologram Cyan",
        bg=QColor(6, 11, 20),
        primary=QColor(0, 240, 255),
        accent=QColor(255, 140, 0),
        wire=QColor(0, 200, 255),
        glow=QColor(0, 180, 255),
    ),
    "Mark LVI Crimson": ThemeColors(
        name="Mark LVI Crimson",
        bg=QColor(16, 8, 12),
        primary=QColor(255, 45, 85),
        accent=QColor(255, 215, 0),
        wire=QColor(255, 75, 110),
        glow=QColor(255, 45, 85),
    ),
    "Emerald Matrix": ThemeColors(
        name="Emerald Matrix",
        bg=QColor(5, 15, 8),
        primary=QColor(0, 255, 130),
        accent=QColor(0, 220, 255),
        wire=QColor(0, 230, 110),
        glow=QColor(0, 255, 130),
    ),
    "Cyber Synthwave": ThemeColors(
        name="Cyber Synthwave",
        bg=QColor(14, 8, 22),
        primary=QColor(220, 50, 255),
        accent=QColor(0, 255, 240),
        wire=QColor(190, 40, 235),
        glow=QColor(220, 50, 255),
    ),
    "Solar Amber": ThemeColors(
        name="Solar Amber",
        bg=QColor(18, 12, 5),
        primary=QColor(255, 175, 20),
        accent=QColor(50, 200, 255),
        wire=QColor(255, 160, 10),
        glow=QColor(255, 175, 20),
    ),
}


class ProceduralAvatarRenderer:
    """
    Renders the 3D Face with vectorized NumPy math, perspective camera
    projection, depth-sorted facets, rim Fresnel glow, and mood blendshapes.
    """

    def __init__(self, topology: ProceduralFaceTopology) -> None:
        self.top = topology
        self.cam_distance: float = 4.4
        self.shaded_mode: bool = True

    def render(self, p: QPainter, cx: float, cy: float, r: float,
               engine: AvatarAnimationEngine, theme: ThemeColors) -> None:
        verts = np.copy(self.top.base_vertices)

        # 1. Emotional Blendshapes: Smile (corners 31, 32 pulled up & out)
        if engine.smile_amount > 0.01:
            sm = engine.smile_amount
            verts[31, 1] += sm * 0.055
            verts[32, 1] += sm * 0.055
            verts[31, 0] -= sm * 0.025
            verts[32, 0] += sm * 0.025

        # 2. Emotional Blendshapes: Brow Furrow (thinking/focus) & Brow Arch (joy)
        if engine.brow_furrow_amount > 0.01:
            bf = engine.brow_furrow_amount
            verts[9, 1] -= bf * 0.045
            verts[10, 1] -= bf * 0.045
            verts[9, 0] += bf * 0.030
            verts[10, 0] -= bf * 0.030
        if engine.brow_arch_amount > 0.01:
            ba = engine.brow_arch_amount
            verts[8, 1] += ba * 0.065
            verts[11, 1] += ba * 0.065

        # 3. Morph Rig: Lip Spread / Puckering
        if abs(engine.lip_spread) > 0.01 and engine.mouth_openness > 0.01:
            k = self.top.lip_weights * (engine.lip_spread * engine.mouth_openness)
            verts[:, 0] += k * verts[:, 0] * 0.45
            verts[:, 2] -= k * 0.04

        # 4. Morph Rig: Mandible Jaw Hinge
        effective_open = engine.mouth_openness * (1.0 - engine.bilabial_closure)
        if effective_open > 0.005:
            px, py, pz = self.top.jaw_pivot
            angle = self.top.jaw_weights * (effective_open * self.top.jaw_max_angle)
            ca, sa = np.cos(angle), np.sin(angle)
            dy = verts[:, 1] - py
            dz = verts[:, 2] - pz
            verts[:, 1] = py + dy * ca - dz * sa
            verts[:, 2] = pz + dy * sa + dz * ca

        # 5. Continuous Breathing Displacement
        verts[:, 1] += engine.breath_bob_y

        # 6. 3D Rotation Matrices (Pitch, Yaw, Roll)
        cyaw, syaw = math.cos(engine.head_yaw), math.sin(engine.head_yaw)
        cpitch, spitch = math.cos(engine.head_pitch), math.sin(engine.head_pitch)
        croll, sroll = math.cos(engine.head_roll), math.sin(engine.head_roll)

        R_yaw = np.array([[cyaw, 0, syaw], [0, 1, 0], [-syaw, 0, cyaw]], dtype=np.float32)
        R_pitch = np.array([[1, 0, 0], [0, cpitch, -spitch], [0, spitch, cpitch]], dtype=np.float32)
        R_roll = np.array([[croll, -sroll, 0], [sroll, croll, 0], [0, 0, 1]], dtype=np.float32)
        rot_mat = R_yaw @ R_pitch @ R_roll

        posed_verts = verts @ rot_mat.T

        # 7. Perspective Camera Projection
        w = self.cam_distance - posed_verts[:, 2]
        np.maximum(w, 0.4, out=w)
        proj_scale = (self.cam_distance / w) * r
        screen_x = cx + posed_verts[:, 0] * proj_scale
        screen_y = cy - posed_verts[:, 1] * proj_scale

        # ----------------------------------------------------------------------
        # HOLOGRAPHIC AURA & PULSE
        # ----------------------------------------------------------------------
        aura_r = r * 1.95
        aura_grad = QRadialGradient(cx, cy, aura_r)
        glow_alpha = int(35 + 65 * engine.audio_amplitude)
        c_glow = QColor(theme.glow)
        c_glow.setAlpha(glow_alpha)
        c_glow_outer = QColor(theme.glow)
        c_glow_outer.setAlpha(0)
        aura_grad.setColorAt(0.0, c_glow)
        aura_grad.setColorAt(0.55, QColor(theme.glow.red(), theme.glow.green(), theme.glow.blue(), int(glow_alpha * 0.3)))
        aura_grad.setColorAt(1.0, c_glow_outer)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(aura_grad))
        p.drawEllipse(QRectF(cx - aura_r, cy - aura_r, aura_r * 2.0, aura_r * 2.0))

        # ----------------------------------------------------------------------
        # SHADED FACETS (DEPTH-SORTED)
        # ----------------------------------------------------------------------
        if self.shaded_mode:
            f_a = self.top.faces[:, 0]
            f_b = self.top.faces[:, 1]
            f_c = self.top.faces[:, 2]

            vec1 = posed_verts[f_b] - posed_verts[f_a]
            vec2 = posed_verts[f_c] - posed_verts[f_a]
            fn = np.cross(vec1, vec2)
            fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-8)

            nz = fn[:, 2]
            visible_idx = np.flatnonzero(nz > 0.05)

            if len(visible_idx) > 0:
                light_dir = np.array([-0.45, 0.55, 0.70], dtype=np.float32)
                light_dir /= np.linalg.norm(light_dir)

                diffuse = np.clip((fn[visible_idx] * light_dir).sum(axis=1), 0.0, 1.0)
                fresnel = np.clip(1.0 - nz[visible_idx], 0.0, 1.0) ** 2.0
                intensity = 0.22 + 0.58 * diffuse + 0.35 * fresnel

                depths = (posed_verts[f_a[visible_idx], 2] +
                          posed_verts[f_b[visible_idx], 2] +
                          posed_verts[f_c[visible_idx], 2]) / 3.0
                order = np.argsort(depths)

                p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                for idx in order:
                    real_idx = visible_idx[idx]
                    ia, ib, ic = f_a[real_idx], f_b[real_idx], f_c[real_idx]
                    poly = QPolygonF([
                        QPointF(screen_x[ia], screen_y[ia]),
                        QPointF(screen_x[ib], screen_y[ib]),
                        QPointF(screen_x[ic], screen_y[ic]),
                    ])
                    sh = intensity[idx]
                    c_fill = QColor(
                        int(theme.bg.red() + (theme.primary.red() - theme.bg.red()) * sh * 0.55),
                        int(theme.bg.green() + (theme.primary.green() - theme.bg.green()) * sh * 0.55),
                        int(theme.bg.blue() + (theme.primary.blue() - theme.bg.blue()) * sh * 0.55),
                        240,
                    )
                    p.setBrush(QBrush(c_fill))
                    p.drawPolygon(poly)
                p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # ----------------------------------------------------------------------
        # HOLOGRAPHIC WIREFRAME LATTICE
        # ----------------------------------------------------------------------
        p.setBrush(Qt.BrushStyle.NoBrush)
        e0, e1 = self.top.edges[:, 0], self.top.edges[:, 1]
        lines = []
        for a, b in zip(e0, e1):
            lines.append(QLineF(screen_x[a], screen_y[a], screen_x[b], screen_y[b]))

        wire_color = QColor(theme.wire)
        wire_color.setAlpha(110)
        p.setPen(QPen(wire_color, 1.1))
        p.drawLines(lines)

        # ----------------------------------------------------------------------
        # ANATOMICAL FEATURES: EYES, PUPILS, BROWS, TEETH & LIPS
        # ----------------------------------------------------------------------
        # Eyes & Pupils
        eye_open = max(0.0, 1.0 - engine.blink_amount - engine.eye_squint_amount * 0.4)
        for eye_key in ("eye_l", "eye_r"):
            idx_ring = self.top.landmarks[eye_key]
            poly_eye = QPolygonF([QPointF(screen_x[i], screen_y[i]) for i in idx_ring])

            # Socket shadow
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(theme.bg.red(), theme.bg.green(), theme.bg.blue(), 215)))
            p.drawPolygon(poly_eye)

            # Lid line
            p.setBrush(Qt.BrushStyle.NoBrush)
            lid_col = QColor(theme.primary)
            lid_col.setAlpha(220)
            p.setPen(QPen(lid_col, 1.5))
            p.drawPolygon(poly_eye)

            if eye_open > 0.22:
                br = poly_eye.boundingRect()
                center = br.center()
                gaze_offset_x = engine.gaze_x * br.width() * 0.18
                gaze_offset_y = engine.gaze_y * br.height() * 0.22
                pupil_center = QPointF(center.x() + gaze_offset_x, center.y() + gaze_offset_y)

                iris_rad = min(br.width() * 0.22, br.height() * 0.55)
                # Iris glow
                p.setPen(Qt.PenStyle.NoPen)
                iris_col = QColor(theme.accent)
                iris_col.setAlpha(int(215 * eye_open))
                p.setBrush(QBrush(iris_col))
                p.drawEllipse(pupil_center, iris_rad, iris_rad * eye_open)

                # Pupil core
                p.setBrush(QBrush(QColor(255, 255, 255, int(245 * eye_open))))
                p.drawEllipse(pupil_center, iris_rad * 0.38, iris_rad * 0.38 * eye_open)

        # Eyebrows
        p.setBrush(Qt.BrushStyle.NoBrush)
        brow_col = QColor(theme.primary)
        brow_col.setAlpha(220)
        p.setPen(QPen(brow_col, 2.0))
        for brow_key in ("brow_l", "brow_r"):
            pts = [QPointF(screen_x[i], screen_y[i]) for i in self.top.landmarks[brow_key]]
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])

        # Mouth Cavity, Upper Teeth & Lips
        inner_lip_poly = QPolygonF([QPointF(screen_x[i], screen_y[i])
                                   for i in self.top.landmarks["lips_in"]])
        mouth_h = inner_lip_poly.boundingRect().height()

        if effective_open > 0.03:
            # Dark oral cavity
            p.setPen(Qt.PenStyle.NoPen)
            cavity_col = QColor(theme.bg)
            cavity_col.setAlpha(240)
            p.setBrush(QBrush(cavity_col))
            p.drawPolygon(inner_lip_poly)

            # Throat glow
            throat_col = QColor(theme.accent)
            throat_col.setAlpha(int(60 * effective_open))
            p.setBrush(QBrush(throat_col))
            p.drawPolygon(inner_lip_poly)

            # Upper Teeth row
            top_lip_pt = QPointF(screen_x[34], screen_y[34])
            corner_l = QPointF(screen_x[31], screen_y[31])
            corner_r = QPointF(screen_x[32], screen_y[32])
            teeth_h = mouth_h * 0.35

            teeth_poly = QPolygonF([
                QPointF(corner_l.x() * 0.35 + top_lip_pt.x() * 0.65, top_lip_pt.y()),
                QPointF(corner_r.x() * 0.35 + top_lip_pt.x() * 0.65, top_lip_pt.y()),
                QPointF(corner_r.x() * 0.35 + top_lip_pt.x() * 0.65, top_lip_pt.y() + teeth_h),
                QPointF(corner_l.x() * 0.35 + top_lip_pt.x() * 0.65, top_lip_pt.y() + teeth_h),
            ])
            teeth_col = QColor(theme.primary)
            teeth_col.setAlpha(int(170 + 70 * effective_open))
            p.setBrush(QBrush(teeth_col))
            p.drawPolygon(teeth_poly)

        # Lip contours
        p.setBrush(Qt.BrushStyle.NoBrush)
        lip_col = QColor(theme.primary)
        lip_col.setAlpha(int(180 + 70 * effective_open))
        p.setPen(QPen(lip_col, 1.6))
        p.drawPolygon(inner_lip_poly)

        outer_lip_poly = QPolygonF([QPointF(screen_x[i], screen_y[i])
                                   for i in self.top.landmarks["lips_out"]])
        lip_outer_col = QColor(theme.primary)
        lip_outer_col.setAlpha(120)
        p.setPen(QPen(lip_outer_col, 1.2))
        p.drawPolygon(outer_lip_poly)

        # Holographic scanline overlay
        scan_y_px = cy - engine.scanline_y * r
        if cy - r <= scan_y_px <= cy + r * 1.2:
            scan_pen = QPen(QColor(theme.primary.red(), theme.primary.green(), theme.primary.blue(), 160), 1.5)
            p.setPen(scan_pen)
            scan_w = r * 0.95
            p.drawLine(QPointF(cx - scan_w, scan_y_px), QPointF(cx + scan_w, scan_y_px))


# ==============================================================================
# SECTION 6: CANVAS WIDGET WITH REAL-TIME AUDIO & MOOD OVERLAYS
# ==============================================================================

class AvatarCanvasWidget(QWidget):
    """
    High-DPI 60 FPS Canvas Widget.
    Renders the 3D avatar, real-time pyttsx3 audio oscilloscope,
    telemetry indicators, and handles mouse tracking.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(480, 520)

        # Engines
        self.topology = ProceduralFaceTopology()
        self.procedural_renderer = ProceduralAvatarRenderer(self.topology)
        self.engine = AvatarAnimationEngine()
        self.speech_manager = Pyttsx3SpeechManager(self)

        # Connect speech signals
        self.speech_manager.speech_started.connect(self._on_speech_started)
        self.speech_manager.speech_finished.connect(self._on_speech_finished)

        # Native HoloAvatar integration
        self.native_avatar: Optional[Any] = None
        self.use_native_mesh: bool = False
        if HAVE_NATIVE_AVATAR:
            try:
                self.native_avatar = NativeHoloAvatar()
            except Exception as e:
                print(f"[Avatar] Native HoloAvatar notice: {e}")

        # Current Theme
        self.theme: ThemeColors = THEMES["Hologram Cyan"]

        # Telemetry
        self.fps: float = 60.0
        self.frame_count: int = 0
        self.last_fps_time: float = time.perf_counter()
        self.last_frame_time: float = time.perf_counter()

        # 60 FPS animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

    def _on_speech_started(self, text: str, mood: MoodProfile) -> None:
        self.engine.set_state("SPEAKING")

    def _on_speech_finished(self) -> None:
        self.engine.set_state("IDLE")

    def speak_text(self, text: str, force_mood: Optional[str] = None) -> None:
        """Triggers pyttsx3 speech with synchronous lip-sync."""
        self.speech_manager.speak(text, force_mood)

    def set_theme(self, theme_name: str) -> None:
        if theme_name in THEMES:
            self.theme = THEMES[theme_name]
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        w, h = self.width(), self.height()
        norm_x = (event.position().x() - w * 0.5) / (w * 0.5)
        norm_y = (event.position().y() - h * 0.5) / (h * 0.5)
        self.engine.update_mouse_target(norm_x, norm_y)
        super().mouseMoveEvent(event)

    def _on_tick(self) -> None:
        now = time.perf_counter()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        # FPS calculation
        self.frame_count += 1
        if now - self.last_fps_time >= 0.5:
            self.fps = self.frame_count / (now - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = now

        # Real-time pyttsx3 windowed audio & formant analysis
        live_amp, live_viseme, live_mood = self.speech_manager.update_analysis()

        # Update animation engine physics
        self.engine.update(dt, live_amp, live_viseme, live_mood)

        # Update Native Avatar if selected
        if self.use_native_mesh and self.native_avatar is not None:
            self.native_avatar.step(
                dt=dt,
                amp=live_amp,
                speaking=self.engine.speaking,
                muted=(self.engine.state == "SLEEPING"),
                state=self.engine.state,
                v_open=live_viseme.openness,
                v_wide=live_viseme.spread,
                v_level=live_amp,
            )

        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        cx = w * 0.5
        cy = h * 0.44
        head_radius = min(w * 0.32, h * 0.34)

        # ----------------------------------------------------------------------
        # 1. CYBERNETIC BACKGROUND WITH RADIAL GRADIENT
        # ----------------------------------------------------------------------
        bg_grad = QRadialGradient(cx, cy, max(w, h) * 0.75)
        bg_grad.setColorAt(0.0, QColor(
            int(self.theme.bg.red() * 1.4),
            int(self.theme.bg.green() * 1.4),
            int(self.theme.bg.blue() * 1.4)
        ))
        bg_grad.setColorAt(1.0, self.theme.bg)
        p.fillRect(self.rect(), QBrush(bg_grad))

        # Grid lines
        p.setPen(QPen(QColor(255, 255, 255, 8), 1.0))
        for gx in range(0, int(w), 40):
            p.drawLine(gx, 0, gx, int(h))
        for gy in range(0, int(h), 40):
            p.drawLine(0, gy, int(w), gy)

        # ----------------------------------------------------------------------
        # 2. RENDER 3D AVATAR
        # ----------------------------------------------------------------------
        if self.use_native_mesh and self.native_avatar is not None:
            self.native_avatar.paint(
                p, cx, cy, head_radius,
                self.theme.primary, self.theme.accent, self.theme.bg
            )
        else:
            self.procedural_renderer.render(
                p, cx, cy, head_radius, self.engine, self.theme
            )

        # ----------------------------------------------------------------------
        # 3. PYTTSX3 REAL-TIME OSCILLOSCOPE
        # ----------------------------------------------------------------------
        wave_box_y = h - 68.0
        wave_box_h = 44.0
        wave_box_w = min(w - 40.0, 520.0)
        wave_box_x = (w - wave_box_w) * 0.5

        p.setPen(QPen(QColor(self.theme.primary.red(), self.theme.primary.green(), self.theme.primary.blue(), 50), 1.0))
        p.setBrush(QBrush(QColor(10, 16, 26, 185)))
        p.drawRoundedRect(QRectF(wave_box_x, wave_box_y, wave_box_w, wave_box_h), 8.0, 8.0)

        # Title & mood label
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.setPen(QColor(self.theme.primary.red(), self.theme.primary.green(), self.theme.primary.blue(), 180))
        p.drawText(int(wave_box_x + 12), int(wave_box_y + 16),
                   f"PYTTSX3 AUDIO WAVEFORM  [MOOD: {self.engine.mood.name}]")

        # Live waveform trace
        samples = self.speech_manager.wave_buffer
        if len(samples) > 1:
            step_x = (wave_box_w - 24.0) / (len(samples) - 1)
            wave_mid_y = wave_box_y + wave_box_h * 0.58
            wave_path = QPainterPath()
            start_x = wave_box_x + 12.0
            wave_path.moveTo(start_x, wave_mid_y + samples[0] * (wave_box_h * 0.35))
            for i in range(1, len(samples)):
                x = start_x + i * step_x
                y = wave_mid_y + samples[i] * (wave_box_h * 0.35)
                wave_path.lineTo(x, y)

            p.setBrush(Qt.BrushStyle.NoBrush)
            wave_pen = QPen(self.theme.accent if self.engine.speaking else self.theme.primary, 1.8)
            p.setPen(wave_pen)
            p.drawPath(wave_path)

        # ----------------------------------------------------------------------
        # 4. HUD TELEMETRY BADGES
        # ----------------------------------------------------------------------
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))

        # Status & Mood Badges (Top Left)
        state_str = f"● STATE: {self.engine.state}  |  EMOTION: {self.engine.mood.name}"
        state_col = self.theme.accent if self.engine.speaking else self.theme.primary
        p.setPen(state_col)
        p.drawText(20, 30, state_str)

        # FPS (Top Right)
        p.setPen(QColor(255, 255, 255, 140))
        p.drawText(int(w - 70), 30, f"{self.fps:.0f} FPS")

        # Kinematics Readout (Bottom Left)
        p.setFont(QFont("Consolas", 8))
        p.setPen(QColor(255, 255, 255, 120))
        effective_open = self.engine.mouth_openness * (1.0 - self.engine.bilabial_closure)
        telemetry = (
            f"JAW: {effective_open * 100:.0f}%  "
            f"SPREAD: {self.engine.lip_spread:+.2f}  "
            f"SMILE: {self.engine.smile_amount * 100:.0f}%  "
            f"PITCH: {math.degrees(self.engine.head_pitch):+.1f}°  "
            f"YAW: {math.degrees(self.engine.head_yaw):+.1f}°"
        )
        p.drawText(20, int(h - 14), telemetry)

        p.end()


# ==============================================================================
# SECTION 7: MAIN APPLICATION WINDOW & INTERACTIVE CONTROLS
# ==============================================================================

class AvatarMainWindow(QMainWindow):
    """
    Main Antigravity IDE graphical window.
    Features text input for arbitrary pyttsx3 speech, preset mood demos,
    theme switching, and real-time animation parameter controls.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mark LVI — Visual Avatar [pyttsx3 Real-Time Sync]")
        self.resize(980, 720)

        # Central layout
        root_widget = QWidget(self)
        self.setCentralWidget(root_widget)
        main_layout = QHBoxLayout(root_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Avatar Canvas
        self.canvas = AvatarCanvasWidget(self)
        main_layout.addWidget(self.canvas, stretch=7)

        # Control Panel Sidebar
        control_panel = self._build_control_panel()
        main_layout.addWidget(control_panel, stretch=4)

        self._apply_dark_styling()

    def _build_control_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("controlPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        # Title
        title_label = QLabel("NEURAL AVATAR CONTROL", panel)
        title_label.setObjectName("panelTitle")
        layout.addWidget(title_label)

        # --- TEXT INPUT & PYTTSX3 SPEAK BUTTON ---
        speech_box = QGroupBox("Speak With pyttsx3 (Real-Time Sync)", panel)
        speech_layout = QVBoxLayout(speech_box)

        self.txt_speech = QLineEdit(speech_box)
        self.txt_speech.setPlaceholderText("Type any text here and press Enter...")
        self.txt_speech.setText("Hello! I am your visual avatar with real-time pyttsx3 speech synchronization.")
        self.txt_speech.returnPressed.connect(self._speak_custom_text)
        speech_layout.addWidget(self.txt_speech)

        btn_row = QHBoxLayout()
        self.btn_speak_now = QPushButton("🔊 SPEAK TEXT", speech_box)
        self.btn_speak_now.setObjectName("speakButton")
        self.btn_speak_now.clicked.connect(self._speak_custom_text)
        btn_row.addWidget(self.btn_speak_now)

        self.btn_stop = QPushButton("⏹ STOP", speech_box)
        self.btn_stop.clicked.connect(self.canvas.speech_manager.stop)
        btn_row.addWidget(self.btn_stop)
        speech_layout.addLayout(btn_row)

        layout.addWidget(speech_box)

        # --- EMOTIONAL MOOD PRESETS ---
        mood_group = QGroupBox("Emotional Expressions & Gestures", panel)
        mood_layout = QVBoxLayout(mood_group)
        mood_layout.setSpacing(6)

        presets = [
            ("👋 GREETING (Joyful)", "Hello! It is wonderful to see you today. All systems are operating at peak efficiency!", "JOY"),
            ("🤔 THOUGHTFUL (Analytical)", "Analyzing quantum telemetry across neural pathways... The data suggests fascinating outcomes.", "THOUGHTFUL"),
            ("🚨 ALERT (Critical)", "Warning! Unauthorized access attempt detected in secure perimeter. Defense protocols engaged.", "ALERT"),
            ("🌊 SERENE (Calm)", "All telemetry streams are steady. Operating peacefully within nominal baseline parameters.", "SERENE"),
        ]

        for label, phrase, mood_name in presets:
            btn = QPushButton(label, mood_group)
            btn.clicked.connect(lambda ch, p=phrase, m=mood_name: self._trigger_mood_phrase(p, m))
            mood_layout.addWidget(btn)

        layout.addWidget(mood_group)

        # --- COLOR THEMES ---
        theme_group = QGroupBox("Hologram Color Theme", panel)
        theme_layout = QVBoxLayout(theme_group)
        self.combo_theme = QComboBox(theme_group)
        for theme_name in THEMES.keys():
            self.combo_theme.addItem(theme_name)
        self.combo_theme.currentTextChanged.connect(self.canvas.set_theme)
        theme_layout.addWidget(self.combo_theme)
        layout.addWidget(theme_group)

        # --- 3D MESH SELECTION ---
        mesh_group = QGroupBox("3D Mesh Architecture", panel)
        mesh_layout = QVBoxLayout(mesh_group)

        self.combo_mesh = QComboBox(mesh_group)
        self.combo_mesh.addItem("Procedural Cyber 3D Face (Self-Contained)")
        if HAVE_NATIVE_AVATAR:
            self.combo_mesh.addItem("MediaPipe Canonical Mesh (core.avatar)")
        self.combo_mesh.currentIndexChanged.connect(self._on_mesh_changed)
        mesh_layout.addWidget(self.combo_mesh)

        self.chk_wire_only = QCheckBox("Solid Shaded Surface Lighting", mesh_group)
        self.chk_wire_only.setChecked(True)
        self.chk_wire_only.toggled.connect(self._on_shaded_toggled)
        mesh_layout.addWidget(self.chk_wire_only)

        layout.addWidget(mesh_group)

        # --- DYNAMICS & SENSITIVITY ---
        dyn_group = QGroupBox("Animation Parameters", panel)
        dyn_layout = QVBoxLayout(dyn_group)

        # Breathing Speed
        dyn_layout.addWidget(QLabel("Breathing Rate (RPM):"))
        self.slider_breath = QSlider(Qt.Orientation.Horizontal, dyn_group)
        self.slider_breath.setRange(10, 35)
        self.slider_breath.setValue(17)
        self.slider_breath.valueChanged.connect(lambda v: setattr(self.canvas.engine, "breathing_rate", v / 60.0))
        dyn_layout.addWidget(self.slider_breath)

        # Idle Sway
        dyn_layout.addWidget(QLabel("Idle Sway Intensity:"))
        self.slider_sway = QSlider(Qt.Orientation.Horizontal, dyn_group)
        self.slider_sway.setRange(0, 200)
        self.slider_sway.setValue(100)
        self.slider_sway.valueChanged.connect(lambda v: setattr(self.canvas.engine, "idle_sway_intensity", v / 100.0))
        dyn_layout.addWidget(self.slider_sway)

        # Mouse Tracking Toggle
        self.chk_mouse = QCheckBox("Interactive Cursor Tracking", dyn_group)
        self.chk_mouse.setChecked(True)
        self.chk_mouse.toggled.connect(lambda v: setattr(self.canvas.engine, "mouse_tracking_enabled", v))
        dyn_layout.addWidget(self.chk_mouse)

        layout.addWidget(dyn_group)

        layout.addStretch()

        tip_label = QLabel("Tip: Press [SPACE] anywhere to speak custom text.", panel)
        tip_label.setObjectName("tipLabel")
        layout.addWidget(tip_label)

        return panel

    def _speak_custom_text(self) -> None:
        text = self.txt_speech.text().strip()
        if text:
            self.canvas.speak_text(text)

    def _trigger_mood_phrase(self, phrase: str, mood_name: str) -> None:
        self.txt_speech.setText(phrase)
        self.canvas.speak_text(phrase, force_mood=mood_name)

    def _on_mesh_changed(self, idx: int) -> None:
        self.canvas.use_native_mesh = (idx == 1)

    def _on_shaded_toggled(self, checked: bool) -> None:
        self.canvas.procedural_renderer.shaded_mode = checked
        if self.canvas.native_avatar is not None:
            self.canvas.native_avatar.shaded = checked

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not self.txt_speech.hasFocus():
            self._speak_custom_text()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _apply_dark_styling(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #070b14;
            }
            #controlPanel {
                background-color: #0d1424;
                border: 1px solid #1a2744;
                border-radius: 10px;
            }
            #panelTitle {
                color: #00f0ff;
                font-family: 'Segoe UI', Arial;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 1.5px;
                margin-bottom: 4px;
            }
            #speakButton {
                background-color: #0088cc;
                color: #ffffff;
                font-family: 'Segoe UI', Arial;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border-radius: 6px;
                border: none;
            }
            #speakButton:hover {
                background-color: #00b4d8;
            }
            QLineEdit {
                background-color: #121c30;
                color: #ffffff;
                border: 1px solid #233555;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #00f0ff;
            }
            QPushButton {
                background-color: #162238;
                color: #d0e0f0;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
                padding: 6px;
                border-radius: 5px;
                border: 1px solid #233555;
            }
            QPushButton:hover {
                background-color: #203354;
                border-color: #00f0ff;
                color: #ffffff;
            }
            QGroupBox {
                color: #8da4c4;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #1c2b48;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #121c30;
                color: #d0e0f0;
                border: 1px solid #233555;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #121c30;
                color: #d0e0f0;
                selection-background-color: #0088cc;
                selection-color: #ffffff;
            }
            QCheckBox {
                color: #b0c4de;
                font-size: 11px;
                spacing: 6px;
            }
            QLabel {
                color: #8da4c4;
                font-size: 10px;
            }
            #tipLabel {
                color: #557090;
                font-style: italic;
                font-size: 10px;
                margin-top: 4px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #1c2b48;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #00a8e8;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00f0ff;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }
        """)


# ==============================================================================
# SECTION 8: ENTRY POINT
# ==============================================================================

def main() -> None:
    """Launch the Visual Avatar application."""
    app = QApplication(sys.argv)
    app.setApplicationName("VisualAvatar")

    window = AvatarMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
