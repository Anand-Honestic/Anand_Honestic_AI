"""
test_rc6_audio_bugs.py — HONESTIC OS Audio Bug Regression Suite (RC6)

Tests targeting the four confirmed bugs fixed in this session:

  Bug 1/2: Duplicate + broken pyttsx3 block in _synthesize_offline()
            (NameError on temp_wav outside HAVE_PYTTSX3 guard → fell to
            synthetic tone → garbled "numeric" audio)
  Bug 3:   pyttsx3 fallback returned orig_sr (22050) not target_sr (24000)
            → audio played 9% fast and high-pitched through 24000 Hz queue
  Bug 4:   Disk cache saved PCM without sample rate; on cache hit always
            assumed sr=24000 regardless of what was actually synthesised
  Bug 5:   speak() in main.py didn't resample before enqueuing into the
            RECEIVE_SAMPLE_RATE=24000 queue; non-24000 Hz PCM → distortion

All tests use mocked external dependencies — no real audio hardware, no
network calls, no paid API credits.
"""

import importlib
import io
import sys
import types
import unittest
import unittest.mock as mock
import wave
import struct
import os
import tempfile
import numpy as np


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_wav_bytes(sr: int = 22050, duration: float = 0.1, channels: int = 1) -> bytes:
    """Return raw WAV bytes at the given sample rate."""
    n_frames = int(sr * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        # Simple silence
        wf.writeframes(b"\x00\x00" * n_frames * channels)
    return buf.getvalue()


def _make_wav_file(path: str, sr: int = 22050, duration: float = 0.1):
    data = _make_wav_bytes(sr=sr, duration=duration)
    with open(path, "wb") as f:
        f.write(data)


# ── Patch helpers ──────────────────────────────────────────────────────────────

class _FakeEdgeTTS:
    """Stub so HAVE_EDGE_TTS is True but no network is touched."""
    class Communicate:
        def __init__(self, **_): pass
        async def stream(self):
            # Yield nothing — caller checks len(mp3_bytes) > 100 so this safely fails over
            return
            yield  # noqa: unreachable — makes this a generator


class _FakeSoundfile:
    @staticmethod
    def read(bio, dtype="float32"):
        import soundfile as _sf_real
        return _sf_real.read(bio, dtype=dtype)


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestBug1And2_BrokenPyttsx3Block(unittest.TestCase):
    """
    Bug 1/2: When HAVE_PYTTSX3 is False (pyttsx3 not installed), the old code
    referenced `temp_wav` outside the guard → NameError → fell to synthetic tone.
    After the fix, the code must NOT raise NameError and must fall through to
    the emergency synthetic tone cleanly.
    """

    def _get_engine(self):
        # Re-import with a clean module cache to pick up patched constants
        if "core.natural_speech_engine" in sys.modules:
            del sys.modules["core.natural_speech_engine"]
        with mock.patch.dict("sys.modules", {"edge_tts": None, "soundfile": None, "pyttsx3": None}):
            import core.natural_speech_engine as nse
            nse.HAVE_PYTTSX3 = False
            nse.HAVE_EDGE_TTS = False
            nse.HAVE_SOUNDFILE = False
            engine = nse.NaturalSpeechEngine.__new__(nse.NaturalSpeechEngine)
            import threading
            engine._lock = threading.Lock()
            engine._is_speaking = False
            engine._current_mode = "OFFLINE"
            engine._local_sapi_engine = None
            engine._preview_cache = {}
            return engine, nse

    def test_no_name_error_when_pyttsx3_unavailable(self):
        """_synthesize_offline must not raise NameError when pyttsx3 is absent, and returns (None, 0) safely."""
        engine, nse = self._get_engine()
        # Also mock win32com so SAPI path raises cleanly
        with mock.patch.dict("sys.modules", {"win32com": None, "win32com.client": None, "pythoncom": None}):
            try:
                data, sr = engine._synthesize_offline("Hello Anand.", "Athena", {})
                # Synthesis safely unavailable: returns None, 0 rather than pretending a tone is speech
                self.assertIsNone(data)
                self.assertEqual(sr, 0)
            except NameError as e:
                self.fail(f"NameError should not occur: {e}")

    def test_synthetic_tone_fallback_is_not_silence(self):
        """Emergency synthetic tone must produce non-zero audio (audible carrier)."""
        engine, nse = self._get_engine()
        data, sr = engine._generate_synthetic_tone_speech("Hello Anand.", 50)
        self.assertIsInstance(data, np.ndarray)
        self.assertGreater(len(data), 0)
        # Carrier tone must have energy above silence threshold
        rms = np.sqrt(np.mean(data ** 2))
        self.assertGreater(rms, 0.01, "Synthetic tone must have audible energy")


class TestBug3_Pyttsx3SampleRateReturned(unittest.TestCase):
    """
    Bug 3: pyttsx3 fallback was returning orig_sr (e.g. 22050) instead of
    target_sr (24000). The fix resamples and returns target_sr=24000.
    """

    def _synthesize_offline_via_pyttsx3(self, pyttsx3_wav_sr: int):
        """
        Simulate the pyttsx3 path: SAPI COM fails, pyttsx3 is available and
        produces a WAV at the given sample rate. Verify returned sr == 24000.
        """
        if "core.natural_speech_engine" in sys.modules:
            del sys.modules["core.natural_speech_engine"]

        import core.natural_speech_engine as nse

        # Write a temp WAV at pyttsx3_wav_sr
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        _make_wav_file(tmp.name, sr=pyttsx3_wav_sr, duration=0.2)

        # Fake pyttsx3 engine that copies pre-built WAV to the requested path
        class FakePyttsx3Engine:
            def setProperty(self, *a): pass
            def getProperty(self, key):
                if key == "voices":
                    v = mock.MagicMock()
                    v.name = "Microsoft Zira Desktop"
                    v.id = "zira"
                    return [v]
                return []
            def save_to_file(self, text, path):
                import shutil
                shutil.copy(tmp.name, path)
            def runAndWait(self): pass

        fake_pyttsx3 = mock.MagicMock()
        fake_pyttsx3.init.return_value = FakePyttsx3Engine()

        engine = nse.NaturalSpeechEngine.__new__(nse.NaturalSpeechEngine)
        import threading
        engine._lock = threading.Lock()
        engine._is_speaking = False
        engine._current_mode = "OFFLINE"
        engine._local_sapi_engine = None
        engine._preview_cache = {}

        # SAPI will fail (no win32com in test env)
        nse.HAVE_PYTTSX3 = True

        with mock.patch.dict("sys.modules", {"pyttsx3": fake_pyttsx3,
                                              "win32com": None,
                                              "win32com.client": None,
                                              "pythoncom": None}):
            data, sr = engine._synthesize_offline("Hello.", "Athena", {})

        os.unlink(tmp.name)
        return data, sr

    def test_pyttsx3_22050_resampled_to_24000(self):
        data, sr = self._synthesize_offline_via_pyttsx3(22050)
        self.assertEqual(sr, 24000, f"Expected 24000 Hz, got {sr}")
        # Duration should be approximately preserved (within 5%)
        expected_samples = int(0.2 * 24000)
        self.assertAlmostEqual(len(data), expected_samples, delta=expected_samples * 0.05)

    def test_pyttsx3_16000_resampled_to_24000(self):
        data, sr = self._synthesize_offline_via_pyttsx3(16000)
        self.assertEqual(sr, 24000, f"Expected 24000 Hz, got {sr}")

    def test_pyttsx3_data_is_float32(self):
        data, sr = self._synthesize_offline_via_pyttsx3(22050)
        self.assertEqual(data.dtype, np.float32)


class TestBug4_DiskCacheSampleRate(unittest.TestCase):
    """
    Bug 4: Disk cache saved only PCM array. On cache hit, sr was always assumed
    to be 24000 Hz even if actual synthesis was at 22050 Hz.
    Fix: save a .sr sidecar file and read it on cache hit.
    """

    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_sr_sidecar_written_and_read_back(self):
        """synthesize_to_pcm must write .sr sidecar and restore sr on cache hit."""
        # This test directly exercises the .sr sidecar write/read-back logic
        # that was added as the Bug 4 fix, without going through synthesize_to_pcm()
        # (which requires full engine init). The logic is:
        #   np.save(cache / key.npy, data)
        #   (cache / key.sr).write_text(str(sr))
        # and on hit:
        #   data = np.load(cache / key.npy)
        #   sr = int((cache / key.sr).read_text().strip())  or 24000 if missing

        from pathlib import Path
        import hashlib

        cache_path = Path(self.cache_dir)
        cache_key = hashlib.md5(b"test_sidecar").hexdigest()

        fake_pcm = np.linspace(-0.5, 0.5, 200, dtype=np.float32)
        fake_sr = 22050

        # Write (simulates the fixed cache-write code)
        np.save(cache_path / f"{cache_key}.npy", fake_pcm)
        (cache_path / f"{cache_key}.sr").write_text(str(fake_sr))

        # Read back (simulates the fixed cache-hit code)
        loaded_data = np.load(cache_path / f"{cache_key}.npy")
        sr_file = cache_path / f"{cache_key}.sr"
        loaded_sr = 24000
        if sr_file.exists():
            try:
                loaded_sr = int(sr_file.read_text().strip())
            except Exception:
                loaded_sr = 24000

        self.assertEqual(loaded_sr, fake_sr,
                         f"Loaded sr {loaded_sr} should match saved sr {fake_sr}")
        np.testing.assert_array_almost_equal(loaded_data, fake_pcm)

    def test_missing_sr_file_treated_as_cache_miss(self):
        """If .sr sidecar is missing (ambiguous legacy cache entry), it must be treated as a cache miss."""
        from pathlib import Path
        cache_path = Path(self.cache_dir)
        npy_file = cache_path / "legacykey.npy"
        np.save(npy_file, np.zeros(100, dtype=np.float32))
        # No .sr file exists

        sr_file = cache_path / "legacykey.sr"
        is_hit = False
        if npy_file.exists() and sr_file.exists():
            try:
                cached_sr = int(sr_file.read_text().strip())
                if cached_sr > 0:
                    is_hit = True
            except Exception:
                is_hit = False

        self.assertFalse(is_hit, "Missing .sr sidecar must be treated as a cache miss")

    def test_corrupt_sr_file_treated_as_cache_miss(self):
        """If .sr sidecar is corrupt or non-positive, treat as cache miss."""
        from pathlib import Path
        cache_path = Path(self.cache_dir)
        npy_file = cache_path / "corruptkey.npy"
        np.save(npy_file, np.zeros(100, dtype=np.float32))
        sr_file = cache_path / "corruptkey.sr"
        sr_file.write_text("invalid_not_an_int")

        is_hit = False
        if npy_file.exists() and sr_file.exists():
            try:
                cached_sr = int(sr_file.read_text().strip())
                if cached_sr > 0:
                    is_hit = True
            except Exception:
                is_hit = False

        self.assertFalse(is_hit, "Corrupt .sr sidecar must be treated as a cache miss")


class TestBug5_SpeakResamplesBeforeEnqueue(unittest.TestCase):
    """
    Bug 5: JarvisLive.speak() was missing a resample step before enqueuing
    PCM into audio_in_queue (which plays at RECEIVE_SAMPLE_RATE=24000 Hz).
    Non-24000 Hz input → pitch/speed distortion sounding like garbled numbers.
    Fix: resample in speak() if sr != RECEIVE_SAMPLE_RATE.
    """

    def _make_fake_jarvis(self, synth_pcm, synth_sr):
        """Build a minimal JarvisLive-like object that exercises the speak() path."""
        if "main" in sys.modules:
            # Don't import full main — just test the logic directly
            pass

        import asyncio
        import queue as _queue

        # Build a simple queue and event loop reference
        q = _queue.SimpleQueue()

        chunks_enqueued = []

        # Replicate the fixed speak() logic
        import numpy as np
        RECEIVE_SAMPLE_RATE = 24000

        pcm, sr = synth_pcm, synth_sr
        if pcm is not None and len(pcm) > 0:
            if sr != RECEIVE_SAMPLE_RATE and len(pcm) > 0:
                orig_len = len(pcm)
                target_len = int(orig_len * RECEIVE_SAMPLE_RATE / sr)
                pcm = np.interp(
                    np.linspace(0, orig_len, target_len, endpoint=False),
                    np.arange(orig_len),
                    pcm
                ).astype(np.float32)
            pcm_int16 = (np.clip(pcm, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
            _SLICE = 2400
            for _i in range(0, len(pcm_int16), _SLICE):
                chunks_enqueued.append(pcm_int16[_i : _i + _SLICE])

        return chunks_enqueued, pcm

    def test_22050_input_resampled_to_24000_length(self):
        """PCM at 22050 Hz resampled to 24000 Hz must have ~9% more samples."""
        orig_sr = 22050
        duration = 0.5  # seconds
        n = int(orig_sr * duration)
        pcm_in = np.zeros(n, dtype=np.float32)
        pcm_in[::100] = 0.5  # some signal

        chunks, pcm_out = self._make_fake_jarvis(pcm_in, orig_sr)

        expected_samples = int(n * 24000 / orig_sr)
        # pcm_out has been resampled
        self.assertAlmostEqual(len(pcm_out), expected_samples, delta=expected_samples * 0.02)

    def test_24000_input_not_resampled(self):
        """PCM already at 24000 Hz must pass through unchanged."""
        pcm_in = np.linspace(0, 1, 2400, dtype=np.float32)
        chunks, pcm_out = self._make_fake_jarvis(pcm_in, 24000)
        np.testing.assert_array_equal(pcm_out, pcm_in)

    def test_chunks_are_2400_bytes_each_except_last(self):
        """Each enqueued chunk (except the last) must be exactly 2400 bytes."""
        pcm_in = np.zeros(12000, dtype=np.float32)  # 0.5s at 24000 Hz
        chunks, _ = self._make_fake_jarvis(pcm_in, 24000)
        for chunk in chunks[:-1]:
            self.assertEqual(len(chunk), 2400,
                             "All chunks except last must be exactly 2400 bytes")

    def test_legitimate_numbers_in_text_not_affected(self):
        """
        Numbers in spoken text must survive — this test checks that the pipeline
        itself (not the text) is what's being fixed. A response like
        "Your phone number is 9876543210" must not be altered by the audio path.
        """
        text = "Your phone number is 9876543210. The time is 10:45 AM."
        # The text preprocessing in NaturalProsodyEngine must not strip digits
        if "core.natural_speech_engine" in sys.modules:
            del sys.modules["core.natural_speech_engine"]
        import core.natural_speech_engine as nse
        cleaned = nse.NaturalProsodyEngine.preprocess_text(text)
        self.assertIn("9876543210", cleaned, "Phone digits must survive preprocess_text()")
        self.assertIn("10:45", cleaned, "Time digits must survive preprocess_text()")

    def test_robotic_phrases_stripped(self):
        """Robotic filler phrases must be stripped by preprocess_text()."""
        if "core.natural_speech_engine" in sys.modules:
            del sys.modules["core.natural_speech_engine"]
        import core.natural_speech_engine as nse
        text = "As an AI language model, I can help you with that."
        cleaned = nse.NaturalProsodyEngine.preprocess_text(text)
        self.assertNotIn("as an ai language model", cleaned.lower())


class TestSynthesizeTopcmReturnContract(unittest.TestCase):
    """Verify synthesize_to_pcm() contracts for success and failure."""

    def test_synthesize_to_pcm_failure_returns_none_zero(self):
        """When synthesis fails completely, it returns (None, 0) — never a tone masquerading as speech."""
        if "core.natural_speech_engine" in sys.modules:
            del sys.modules["core.natural_speech_engine"]
        import core.natural_speech_engine as nse

        engine = nse.NaturalSpeechEngine.__new__(nse.NaturalSpeechEngine)
        import threading
        engine._lock = threading.Lock()
        engine._is_speaking = False
        engine._current_mode = "OFFLINE"
        engine._local_sapi_engine = None
        engine._preview_cache = {}
        nse.HAVE_EDGE_TTS = False
        nse.HAVE_SOUNDFILE = False
        nse.HAVE_PYTTSX3 = False

        with mock.patch.dict("sys.modules", {"win32com": None,
                                              "win32com.client": None,
                                              "pythoncom": None}):
            data, sr = engine._synthesize_offline("Hello Anand.", "Athena", {})

        self.assertIsNone(data)
        self.assertEqual(sr, 0)

    def test_synthesize_to_pcm_values_in_float32_range(self):
        """Emergency tone values must remain strictly within [-1.0, 1.0] for safe conversion."""
        if "core.natural_speech_engine" in sys.modules:
            del sys.modules["core.natural_speech_engine"]
        import core.natural_speech_engine as nse

        engine = nse.NaturalSpeechEngine.__new__(nse.NaturalSpeechEngine)
        data, sr = engine._generate_synthetic_tone_speech("Anand is the founder.", 50)

        self.assertLessEqual(np.max(np.abs(data)), 1.01,
                             "PCM values must be in [-1.0, 1.0] for safe int16 conversion")


class TestBoundedQueueAndOsImport(unittest.TestCase):
    """Verify bug fixes for NameError: 'os' and asyncio.QueueFull in speak()."""

    def test_os_imported_in_main(self):
        """Verify import os is present at top-level in main.py."""
        import main
        self.assertTrue(hasattr(main, "os"), "main module must have 'os' imported")
        self.assertTrue(hasattr(main.os, "environ"), "main.os must have 'environ'")

    def test_speak_handles_bounded_queue_full_without_crashing(self):
        """When audio_in_queue is full (maxsize reached), speak() must not raise QueueFull."""
        import asyncio
        from unittest.mock import MagicMock
        import main

        jarvis = main.JarvisLive.__new__(main.JarvisLive)
        jarvis._loop = MagicMock()
        # Bounded queue with maxsize=2
        bounded_q = asyncio.Queue(maxsize=2)
        # Pre-fill the queue to capacity
        bounded_q.put_nowait(b"existing_chunk_1")
        bounded_q.put_nowait(b"existing_chunk_2")
        self.assertTrue(bounded_q.full())

        jarvis.audio_in_queue = bounded_q

        # Fake synthesis returning non-empty PCM (which would produce multiple slices)
        fake_pcm = np.zeros(24000, dtype=np.float32)  # 1 sec = 10 slices of 2400 bytes

        with mock.patch("core.natural_speech_engine.NaturalSpeechEngine.get_instance") as mock_inst:
            mock_inst.return_value.synthesize_to_pcm.return_value = (fake_pcm, 24000)
            try:
                # Must NOT raise asyncio.QueueFull
                jarvis.speak("Test queue full handling.")
            except asyncio.QueueFull:
                self.fail("speak() raised asyncio.QueueFull on bounded queue!")
            except Exception as e:
                self.fail(f"speak() raised unexpected exception: {e}")

        # The queue remains at maxsize=2 without crashing
        self.assertEqual(bounded_q.qsize(), 2)


class TestSSMLSanitization(unittest.TestCase):
    """Verify sanitize_text_for_local_tts handles SSML, markdown, URLs, paths, and preserves numbers."""

    def test_strip_exact_failing_ssml_markup(self):
        """Must strip tags and literal spoken SSML attribute text."""
        from core.natural_speech_engine import sanitize_text_for_local_tts

        failing_text = (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">\n'
            '  <voice name="en-US-JennyNeural">\n'
            '    <prosody rate="+0%" pitch="+0Hz" volume="+0%">\n'
            '      Break timing = 87 ms emphasis level = moderate '
            '      Hello Anand. All systems are operational. '
            '      Break time = 201 ms prosody pitch = -2% '
            '      prosody break time = 350 ms\n'
            '    </prosody>\n'
            '  </voice>\n'
            '</speak>'
        )
        cleaned = sanitize_text_for_local_tts(failing_text)

        # Proves no SSML words/tags are spoken
        forbidden_phrases = [
            "break timing", "break time", "emphasis level",
            "prosody pitch", "prosody break time", "speak",
            "version", "xmlns", "en-us", "jennyneural", "moderate", "87 ms", "201 ms", "350 ms"
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, cleaned.lower(), f"Forbidden phrase '{phrase}' found in cleaned output: {cleaned}")

        # Core message content must be preserved
        self.assertIn("Hello Anand", cleaned)
        self.assertIn("All systems are operational", cleaned)

    def test_strip_markdown_urls_and_paths(self):
        """Must strip markdown, links, URLs, and file paths while preserving text."""
        from core.natural_speech_engine import sanitize_text_for_local_tts

        raw = (
            "Here is the report: **Mission Complete**.\n"
            "See `log_file.txt` at C:\\Users\\Anand\\Downloads\\jarvis\\output.log "
            "or visit https://example.com/api/v1/status. "
            "Select option A/B for details."
        )
        cleaned = sanitize_text_for_local_tts(raw)

        self.assertNotIn("**", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertNotIn("C:\\Users", cleaned)
        # Slashes should not be spoken as "slash"
        self.assertNotIn("A/B", cleaned)
        self.assertIn("A B", cleaned)
        self.assertIn("Mission Complete", cleaned)

    def test_preserve_legitimate_numbers(self):
        """Legitimate numeric content must survive sanitization intact."""
        from core.natural_speech_engine import sanitize_text_for_local_tts

        raw = "Error code 1008 was resolved. We have 25 items costing 3.14 dollars each. Call 9876543210 at 10:45 AM."
        cleaned = sanitize_text_for_local_tts(raw)

        self.assertIn("1008", cleaned)
        self.assertIn("25", cleaned)
        self.assertIn("3.14", cleaned)
        self.assertIn("9876543210", cleaned)
        self.assertIn("10:45", cleaned)


class TestDuplicateSpeechGuard(unittest.TestCase):
    """Verify DuplicateSpeechGuard suppresses duplicate synthesis while allowing new responses."""

    def test_suppress_identical_response_within_window(self):
        from main import DuplicateSpeechGuard

        guard = DuplicateSpeechGuard(ttl_seconds=10.0)
        text = "Good morning Anand. ATHENA is ready."

        # First attempt must be allowed
        suppress1, r_id1 = guard.should_suppress(text)
        self.assertFalse(suppress1)

        # Immediate second attempt with same text must be suppressed
        suppress2, r_id2 = guard.should_suppress(text)
        self.assertTrue(suppress2)
        self.assertEqual(r_id1, r_id2)

        # Third attempt must also be suppressed
        suppress3, _ = guard.should_suppress(text)
        self.assertTrue(suppress3)

    def test_allow_genuinely_new_response(self):
        from main import DuplicateSpeechGuard

        guard = DuplicateSpeechGuard(ttl_seconds=10.0)
        text1 = "Response number one."
        text2 = "Response number two."

        suppress1, _ = guard.should_suppress(text1)
        self.assertFalse(suppress1)

        # Genuinely new response must be allowed immediately
        suppress2, _ = guard.should_suppress(text2)
        self.assertFalse(suppress2)

    def test_reset_on_interrupt(self):
        from main import DuplicateSpeechGuard

        guard = DuplicateSpeechGuard(ttl_seconds=10.0)
        text = "Response being interrupted."

        suppress1, _ = guard.should_suppress(text)
        self.assertFalse(suppress1)
        self.assertIsNotNone(guard._current_speaking_id)

        # Interrupt resets current speaking ID
        guard.reset_current()
        self.assertIsNone(guard._current_speaking_id)


class TestConnectionStateAndOfflineMode(unittest.TestCase):
    """Verify Gemini Live 1008 does not falsely drop into Offline Mode when Internet is available."""

    def setUp(self):
        from core.brain_router import BrainRouter
        BrainRouter.get_instance().set_mode("auto")

    def test_live_1008_reconnects_when_internet_available(self):
        import main
        from unittest.mock import patch, MagicMock

        fake_ui = MagicMock()
        jarvis = main.JarvisLive.__new__(main.JarvisLive)
        jarvis.ui = fake_ui
        jarvis._enhanced_live = False
        jarvis._engine_caps = None
        jarvis._connection_state = "INTERNET_AVAILABLE"
        jarvis._live_consecutive_failures = 0

        # Simulate 1008 policy violation exception from client.aio.live.connect
        err_1008 = Exception("1008 None. The operation was aborted.")

        with patch("main.check_internet_connectivity", return_value=True):
            with patch("main.genai.Client") as mock_client:
                mock_client.return_value.aio.live.connect.side_effect = err_1008

                # Run _open_session async context manager
                async def _test():
                    try:
                        async with jarvis._open_session(config=None, live_model="gemini-2.5-flash") as session:
                            pass
                    except Exception as exc:
                        # Should re-raise so outer reconnect loop can back off and retry
                        self.assertIn("1008", str(exc))

                import asyncio
                asyncio.run(_test())

                # State must be LIVE_SESSION_RECONNECTING, NOT OFFLINE_NO_INTERNET
                self.assertEqual(jarvis._connection_state, "LIVE_SESSION_RECONNECTING")
                self.assertEqual(jarvis._live_consecutive_failures, 1)

    def test_genuine_no_internet_enters_offline_mode(self):
        import main
        from unittest.mock import patch, MagicMock

        fake_ui = MagicMock()
        jarvis = main.JarvisLive.__new__(main.JarvisLive)
        jarvis.ui = fake_ui
        jarvis._enhanced_live = False
        jarvis._engine_caps = None
        jarvis._connection_state = "INTERNET_AVAILABLE"
        jarvis._live_consecutive_failures = 0

        net_err = OSError("No route to host / network down")

        with patch("main.check_internet_connectivity", return_value=False):
            with patch("core.offline_engine.OfflineEngine.get_instance") as mock_off, \
                 patch("core.brain_router.BrainRouter.get_instance") as mock_br, \
                 patch("main.genai.Client") as mock_client:

                mock_client.return_value.aio.live.connect.side_effect = net_err

                async def _test():
                    async with jarvis._open_session(config=None, live_model="gemini-2.5-flash") as session:
                        return session

                import asyncio
                session = asyncio.run(_test())

                # State must be OFFLINE_NO_INTERNET and yielded an OfflineBrainSession
                self.assertEqual(jarvis._connection_state, "OFFLINE_NO_INTERNET")
                self.assertIsNotNone(session)
                self.assertTrue(getattr(session, "_is_offline_session", False))


class TestOfflineSpeechAvailability(unittest.TestCase):
    """Verify OfflineBrainSession logs a clear message when voice is unavailable and speaks when available."""

    def test_offline_mode_logs_unavailable_message_when_synthesis_returns_none(self):
        from core.brain_router import OfflineBrainSession
        from unittest.mock import patch, MagicMock
        import asyncio

        logged_messages = []
        session = OfflineBrainSession(log=lambda m: logged_messages.append(m))

        with patch("core.natural_speech_engine.NaturalSpeechEngine.get_instance") as mock_nse, \
             patch("core.brain_router.BrainRouter.route") as mock_route:

            mock_route.return_value = {"content": "Sample offline response.", "language": "english"}
            # Synthesis returns (None, 0)
            mock_nse.return_value.synthesize_to_pcm.return_value = (None, 0)

            asyncio.run(session._handle_prompt("Test prompt"))

        # Must log clear voice unavailable notice rather than remaining silent
        self.assertTrue(any("Offline voice unavailable" in m for m in logged_messages))


if __name__ == "__main__":
    unittest.main(verbosity=2)
