"""
core/stt.py — Offline Speech-to-Text Engines for HONESTIC OS

Supports:
- Vosk: Lightweight real-time offline transcription (preferred default).
- Faster-Whisper: Optional higher-quality offline transcription backend.
- Neither: Graceful fallback without hard dependencies, alerting user to type.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Tuple
import numpy as np


# ── Configuration Management ─────────────────────────────────────────────────

def get_offline_stt_config() -> dict:
    """Reads offline STT and voice quality configuration from api_keys.json."""
    defaults = {
        "engine": "auto",        # "auto" | "vosk" | "whisper" | "none"
        "model_path": "",        # optional custom path to model directory
        "language": "auto",      # "auto" | "en-us" | etc.
        "voice_quality": "clear" # "normal" | "clear" | "slow"
    }
    try:
        cfg_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            return {
                "engine": str(data.get("offline_stt_engine", defaults["engine"])).strip().lower(),
                "model_path": str(data.get("offline_stt_model_path", "")).strip(),
                "language": str(data.get("offline_stt_language", defaults["language"])).strip().lower(),
                "voice_quality": str(data.get("offline_voice_quality", defaults["voice_quality"])).strip().lower(),
            }
    except Exception:
        pass
    return defaults


def set_offline_stt_config(
    engine: Optional[str] = None,
    model_path: Optional[str] = None,
    language: Optional[str] = None,
    voice_quality: Optional[str] = None
) -> dict:
    """Updates offline STT and voice quality settings in api_keys.json."""
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    data = {}
    try:
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if engine is not None:
        data["offline_stt_engine"] = engine.strip().lower()
    if model_path is not None:
        data["offline_stt_model_path"] = model_path.strip()
    if language is not None:
        data["offline_stt_language"] = language.strip().lower()
    if voice_quality is not None:
        data["offline_voice_quality"] = voice_quality.strip().lower()

    try:
        cfg_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    except Exception:
        pass

    return get_offline_stt_config()


# ── Vosk STT Engine ──────────────────────────────────────────────────────────

class VoskSTT:
    """Lightweight offline streaming and batch transcription using Vosk."""

    _cached_models: Dict[str, object] = {}
    _cached_model_paths: Dict[str, str] = {}

    def __init__(self, model_path: Optional[str] = None, language: str = "en-us"):
        self.model = None
        self._rec = None
        self.model_loaded = False
        self.engine_name = "vosk"
        self.loaded_model_path = ""
        self.load_error = ""
        self.language = (language or "en-us").strip().lower()

        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)  # Suppress internal C++ Kaldi debug logs
        except ImportError as e:
            self.load_error = f"vosk package not installed ({e})"
            return

        lang_key = "te" if self.language in ("te", "telugu") else "en-us"

        # Check memory cache first
        if lang_key in VoskSTT._cached_models:
            self.model = VoskSTT._cached_models[lang_key]
            self.loaded_model_path = VoskSTT._cached_model_paths.get(lang_key, "")
            self.model_loaded = True
        else:
            candidates = []
            if model_path and os.path.exists(model_path):
                candidates.append(model_path)

            env_path = os.environ.get("VOSK_MODEL_PATH", "").strip()
            if env_path and os.path.exists(env_path):
                candidates.append(env_path)

            base_dir = Path(__file__).resolve().parent.parent

            # Model search order based on target language
            if lang_key == "te":
                search_paths = [
                    base_dir / "models" / "vosk-model-small-te-0.42",
                    base_dir / "models" / "vosk-te",
                    Path.home() / ".cache" / "vosk" / "vosk-model-small-te-0.42",
                ]
            else:
                search_paths = [
                    base_dir / "models" / "vosk-model-small-en-us-0.15",
                    base_dir / "models" / "vosk",
                    base_dir / "config" / "vosk-model",
                    Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15",
                ]

            for p in search_paths:
                if p.exists() and p.is_dir() and str(p) not in candidates:
                    candidates.append(str(p))

            # Scan models/ and ~/.cache/vosk/ for matching subdirectories
            for root in [base_dir / "models", Path.home() / ".cache" / "vosk"]:
                if root.exists():
                    try:
                        for sub in root.iterdir():
                            if sub.is_dir() and "vosk" in sub.name.lower():
                                if (lang_key == "te" and "te" in sub.name.lower()) or (lang_key == "en-us" and "te" not in sub.name.lower()):
                                    if str(sub) not in candidates:
                                        candidates.append(str(sub))
                    except Exception:
                        pass

            for path in candidates:
                try:
                    self.model = Model(path)
                    self.loaded_model_path = path
                    self.model_loaded = True
                    VoskSTT._cached_models[lang_key] = self.model
                    VoskSTT._cached_model_paths[lang_key] = path
                    break
                except Exception as e:
                    self.load_error = str(e)
                    continue

            # Fallback to vosk automatic download if candidate path not found
            if not self.model_loaded:
                try:
                    self.model = Model(lang=lang_key)
                    self.loaded_model_path = f"lang:{lang_key}"
                    self.model_loaded = True
                    VoskSTT._cached_models[lang_key] = self.model
                    VoskSTT._cached_model_paths[lang_key] = self.loaded_model_path
                except Exception as e:
                    self.load_error = str(e)

        if self.model_loaded and self.model:
            try:
                self._rec = KaldiRecognizer(self.model, 16000)
            except Exception as e:
                self.model_loaded = False
                self.load_error = str(e)

    def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw 16-bit mono PCM bytes."""
        if not self.model_loaded or not self._rec or not pcm_bytes:
            return ""
        try:
            self._rec.Reset()
            self._rec.AcceptWaveform(pcm_bytes)
            res = json.loads(self._rec.FinalResult())
            return res.get("text", "").strip()
        except Exception:
            return ""

    def process_chunk(self, audio_bytes: bytes) -> tuple[str, bool]:
        """Feed raw int16 LE PCM bytes. Returns (text, is_final)."""
        if not self.model_loaded or not self._rec:
            return "", False
        try:
            if self._rec.AcceptWaveform(audio_bytes):
                result = json.loads(self._rec.Result())
                return result.get("text", ""), True
            partial = json.loads(self._rec.PartialResult())
            return partial.get("partial", ""), False
        except Exception:
            return "", False


# ── Faster-Whisper STT Engine ────────────────────────────────────────────────

class WhisperSTT:
    """Optional higher-quality offline transcription using faster-whisper."""

    def __init__(
        self,
        model_name: str = "base",
        language: Optional[str] = None,
        model_path: Optional[str] = None
    ):
        self.model_loaded = False
        self.load_error = ""
        self._model = None
        self._language = None if (not language or language.strip().lower() == "auto") else language.strip().lower()
        self.engine_name = "faster-whisper"

        try:
            from faster_whisper import WhisperModel
            import torch
            try:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute = "float16" if device == "cuda" else "int8"
            except Exception:
                device, compute = "cpu", "int8"

            target = model_path if (model_path and os.path.exists(model_path)) else model_name
            self._model = WhisperModel(target, device=device, compute_type=compute)
            self.model_loaded = True
        except ImportError as e:
            self.load_error = f"faster_whisper package not installed ({e})"
        except Exception as e:
            self.load_error = str(e)

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe a float32 mono 16 kHz numpy array. Returns transcript string."""
        if not self.model_loaded or not self._model:
            return ""
        try:
            segments, _ = self._model.transcribe(
                audio,
                language=self._language,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
            )
            return " ".join(s.text for s in segments).strip()
        except Exception as e:
            return ""


# ── Public Offline STT Dispatcher ────────────────────────────────────────────

def transcribe_offline_audio(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    cfg: Optional[dict] = None
) -> Tuple[str, str, bool, str]:
    """
    Attempts to transcribe PCM audio bytes using configured or available offline engines.
    Preferences:
      1. If engine == 'none': disabled.
      2. If engine in ('vosk', 'auto'): Try Vosk.
      3. If engine in ('whisper', 'auto'): Try faster-whisper.
    Returns:
      (transcript_text, engine_name, model_loaded, detail_msg)
    """
    if not pcm_bytes:
        return "", "none", False, "No audio bytes received"

    config = cfg or get_offline_stt_config()
    pref_engine = config.get("engine", "auto").strip().lower()
    model_path = config.get("model_path", "").strip() or None
    language = config.get("language", "auto").strip().lower()

    if pref_engine == "none":
        return "", "none", False, "Offline STT disabled in configuration"

    # 1. Vosk Attempt (preferred lightweight engine)
    if pref_engine in ("vosk", "auto"):
        try:
            v_stt = VoskSTT(model_path=model_path, language=language)
            if v_stt.model_loaded:
                text = v_stt.transcribe(pcm_bytes, sample_rate=sample_rate)
                return text, "vosk", True, f"Loaded model: {v_stt.loaded_model_path}"
            elif pref_engine == "vosk":
                return "", "vosk", False, f"Vosk model not loaded: {v_stt.load_error}"
        except Exception as e:
            if pref_engine == "vosk":
                return "", "vosk", False, f"Vosk error: {e}"

    # 2. Faster-Whisper Attempt
    if pref_engine in ("whisper", "auto"):
        try:
            w_stt = WhisperSTT(model_name="tiny", language=language, model_path=model_path)
            if w_stt.model_loaded:
                samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                text = w_stt.transcribe(samples)
                return text, "faster-whisper", True, "Model loaded"
            elif pref_engine == "whisper":
                return "", "faster-whisper", False, f"Whisper model not loaded: {w_stt.load_error}"
        except Exception as e:
            if pref_engine == "whisper":
                return "", "faster-whisper", False, f"Whisper error: {e}"

    return "", "none", False, "No offline speech recognition engine available or model missing"
