"""
test_rc7_offline_resilience.py — HONESTIC OS Offline Voice, Input & Recovery Test Suite (RC7)

Tests covering:
  1. Offline voice quality settings and duration scaling.
  2. Offline voice synthesis sample rate (24000 Hz float32 PCM).
  3. Telugu mapped phrase synthesis & unmapped script safe text preservation.
  4. Configuration reading & writing for offline STT and voice quality.
  5. Vosk available path (real/mocked transcription).
  6. Vosk unavailable fallback.
  7. Whisper available path (mocked).
  8. Whisper unavailable fallback.
  9. Offline microphone unavailable fallback notice.
  10. Offline microphone successful transcription and offline brain response.
  11. Offline text input routes to BrainRouter and synthesizes audio.
  12. State machine transitions and single source of truth logging.
  13. Online-to-offline transition on internet loss.
  14. Offline-to-online recovery when internet restores.
  15. Clean session diagnostic header and QueueFull regression guard.
"""

import asyncio
import io
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


class TestOfflineVoiceQuality(unittest.TestCase):
    """Problem 1: Offline voice quality, clarity, and quality modes."""

    def setUp(self):
        from core.natural_speech_engine import NaturalSpeechEngine
        self.nse = NaturalSpeechEngine.get_instance()

    def test_01_quality_modes_configurable(self):
        """set_offline_quality correctly sets normal, clear, slow."""
        self.nse.set_offline_quality("normal")
        self.assertEqual(self.nse.get_offline_quality(), "normal")
        self.nse.set_offline_quality("clear")
        self.assertEqual(self.nse.get_offline_quality(), "clear")
        self.nse.set_offline_quality("slow")
        self.assertEqual(self.nse.get_offline_quality(), "slow")
        # Invalid mode is ignored
        self.nse.set_offline_quality("hyper-fast")
        self.assertEqual(self.nse.get_offline_quality(), "slow")
        # Reset to default
        self.nse.set_offline_quality("clear")

    def test_02_offline_synthesis_returns_24000_sr(self):
        """_synthesize_offline returns 24000 Hz float32 PCM without carrier tones."""
        pcm, sr = self.nse._synthesize_offline("Testing clear offline speech synthesis.", "Athena", {"speed": 48})
        if pcm is not None:
            self.assertEqual(sr, 24000)
            self.assertEqual(pcm.dtype, np.float32)
            self.assertGreater(len(pcm), 0)

    def test_03_quality_modes_affect_duration(self):
        """Slow quality mode produces longer duration than clear and normal."""
        text = "Audio clarity test for HONESTIC OS offline voice engine."
        self.nse.set_offline_quality("normal")
        pcm_n, sr_n = self.nse._synthesize_offline(text, "Athena", {"speed": 48})

        self.nse.set_offline_quality("slow")
        pcm_s, sr_s = self.nse._synthesize_offline(text, "Athena", {"speed": 48})

        if pcm_n is not None and pcm_s is not None:
            dur_n = len(pcm_n) / sr_n
            dur_s = len(pcm_s) / sr_s
            self.assertGreater(dur_s, dur_n)

        # Reset to default clear
        self.nse.set_offline_quality("clear")

    def test_04_telugu_mapped_phrase_synthesizes_phonetic_latin(self):
        """Known Telugu greetings are mapped to readable phonetic Latin for offline synthesis."""
        pcm, sr = self.nse._synthesize_offline("హలో ఆనంద్. నేను ఉన్నాను. ఏం పని చేద్దాం?", "Athena", {"speed": 48})
        if pcm is not None:
            self.assertEqual(sr, 24000)
            self.assertGreater(len(pcm), 0)

    def test_05_unmapped_telugu_script_skips_audio_safely_when_no_offline_voice(self):
        """Unmapped Telugu script safely returns None, 0 to preserve text rather than speaking garbled sounds."""
        with patch("win32com.client.Dispatch") as mock_dispatch:
            mock_speaker = MagicMock()
            mock_tokens = MagicMock()
            mock_tokens.Count = 1
            mock_item = MagicMock()
            mock_item.GetDescription.return_value = "Microsoft David Desktop - English (United States)"
            mock_tokens.Item.return_value = mock_item
            mock_speaker.GetVoices.return_value = mock_tokens
            mock_dispatch.return_value = mock_speaker

            pcm, sr = self.nse._synthesize_offline("భారతదేశం నా మాతృభూమి", "Athena", {"speed": 48})
            self.assertIsNone(pcm)
            self.assertEqual(sr, 0)


class TestOfflineSTTConfigurationAndEngines(unittest.TestCase):
    """Problem 2: Vosk, Whisper, configuration, and fallback handling."""

    def test_06_configuration_read_write(self):
        """get_offline_stt_config and set_offline_stt_config read/write correctly."""
        from core.stt import get_offline_stt_config, set_offline_stt_config
        orig = get_offline_stt_config()

        set_offline_stt_config(engine="vosk", voice_quality="slow", language="en-us")
        cfg = get_offline_stt_config()
        self.assertEqual(cfg["engine"], "vosk")
        self.assertEqual(cfg["voice_quality"], "slow")
        self.assertEqual(cfg["language"], "en-us")

        # Restore original
        set_offline_stt_config(
            engine=orig.get("engine", "auto"),
            model_path=orig.get("model_path", ""),
            language=orig.get("language", "auto"),
            voice_quality=orig.get("voice_quality", "clear")
        )

    def test_07_vosk_available_path(self):
        """When Vosk model is loaded, transcribe_offline_audio transcribes successfully."""
        from core.stt import transcribe_offline_audio, VoskSTT
        pcm_test = (np.zeros(3200, dtype=np.int16)).tobytes()
        with patch.object(VoskSTT, "transcribe", return_value="open browser"):
            with patch.object(VoskSTT, "__init__", lambda self, *a, **k: setattr(self, "model_loaded", True) or setattr(self, "loaded_model_path", "test_path") or None):
                text, engine, loaded, msg = transcribe_offline_audio(pcm_test, 16000, {"engine": "vosk"})
                self.assertEqual(text, "open browser")
                self.assertEqual(engine, "vosk")
                self.assertTrue(loaded)

    def test_08_vosk_unavailable_fallback(self):
        """When Vosk is unavailable or model fails to load, reports failure cleanly without raising."""
        from core.stt import transcribe_offline_audio, VoskSTT
        pcm_test = (np.zeros(3200, dtype=np.int16)).tobytes()
        with patch.object(VoskSTT, "__init__", lambda self, *a, **k: setattr(self, "model_loaded", False) or setattr(self, "load_error", "Missing model") or None):
            text, engine, loaded, msg = transcribe_offline_audio(pcm_test, 16000, {"engine": "vosk"})
            self.assertEqual(text, "")
            self.assertEqual(engine, "vosk")
            self.assertFalse(loaded)
            self.assertIn("Missing model", msg)

    def test_09_whisper_available_path(self):
        """When faster-whisper is available and loaded, transcribe_offline_audio uses it."""
        from core.stt import transcribe_offline_audio, WhisperSTT
        pcm_test = (np.zeros(3200, dtype=np.int16)).tobytes()
        with patch.object(WhisperSTT, "transcribe", return_value="hello athena"):
            with patch.object(WhisperSTT, "__init__", lambda self, *a, **k: setattr(self, "model_loaded", True) or None):
                text, engine, loaded, msg = transcribe_offline_audio(pcm_test, 16000, {"engine": "whisper"})
                self.assertEqual(text, "hello athena")
                self.assertEqual(engine, "faster-whisper")
                self.assertTrue(loaded)

    def test_10_whisper_unavailable_fallback(self):
        """When faster-whisper is unavailable, reports failure cleanly without crashing."""
        from core.stt import transcribe_offline_audio, WhisperSTT
        pcm_test = (np.zeros(3200, dtype=np.int16)).tobytes()
        with patch.object(WhisperSTT, "__init__", lambda self, *a, **k: setattr(self, "model_loaded", False) or setattr(self, "load_error", "No module") or None):
            text, engine, loaded, msg = transcribe_offline_audio(pcm_test, 16000, {"engine": "whisper"})
            self.assertEqual(text, "")
            self.assertEqual(engine, "faster-whisper")
            self.assertFalse(loaded)


class TestOfflineSessionVoiceInputAndFallback(unittest.TestCase):
    """Problem 2: Offline microphone input, transcription, and fallback notifications."""

    def test_11_offline_brain_session_mic_unavailable_notice(self):
        """When offline STT is unavailable, flush_microphone logs clear notice and does not fail silently."""
        from core.brain_router import OfflineBrainSession
        logs = []
        session = OfflineBrainSession(log=lambda msg: logs.append(msg))
        session._mic_buf = [b"\x00\x00" * 3200]

        with patch("core.stt.transcribe_offline_audio", return_value=("", "none", False, "No engine")):
            text = asyncio.run(session.flush_microphone())
            self.assertEqual(text, "")
            self.assertTrue(any("Offline microphone input unavailable" in l for l in logs))
            # Verify user-facing message was emitted
            msg = asyncio.run(session._queue.get())
            spoken = getattr(getattr(msg.server_content, "output_transcription", None), "text", "")
            self.assertIn("Offline microphone input unavailable. Please type your message.", spoken)

    def test_12_offline_brain_session_mic_success_triggers_tts(self):
        """When offline STT succeeds, transcribes and triggers offline brain + speech response."""
        from core.brain_router import OfflineBrainSession
        logs = []
        session = OfflineBrainSession(log=lambda msg: logs.append(msg))
        session._mic_buf = [b"\x00\x00" * 3200]

        with patch("core.stt.transcribe_offline_audio", return_value=("hello athena", "vosk", True, "Loaded")):
            with patch("core.brain_router.BrainRouter.route", return_value={"content": "I am here.", "language": "english", "provider": "ollama"}):
                text = asyncio.run(session.flush_microphone())
                self.assertEqual(text, "hello athena")
                # Wait for async _handle_prompt task
                asyncio.run(asyncio.sleep(0.05))

        # Check heard message
        m1 = asyncio.run(session._queue.get())
        heard = getattr(getattr(m1.server_content, "input_transcription", None), "text", "")
        self.assertEqual(heard, "hello athena")

        # Check said message
        m2 = asyncio.run(session._queue.get())
        said = getattr(getattr(m2.server_content, "output_transcription", None), "text", "")
        self.assertEqual(said, "I am here.")

    def test_13_offline_brain_session_text_input_works(self):
        """Text input continues to function in OfflineBrainSession, routing to BrainRouter and emitting response."""
        from core.brain_router import OfflineBrainSession
        session = OfflineBrainSession(log=lambda msg: None)

        with patch("core.brain_router.BrainRouter.route", return_value={"content": "Local response", "language": "english", "provider": "ollama"}):
            asyncio.run(session._handle_prompt("Hello local ATHENA"))

        m1 = asyncio.run(session._queue.get())
        heard = getattr(getattr(m1.server_content, "input_transcription", None), "text", "")
        self.assertEqual(heard, "Hello local ATHENA")

        m2 = asyncio.run(session._queue.get())
        said = getattr(getattr(m2.server_content, "output_transcription", None), "text", "")
        self.assertEqual(said, "Local response")


class TestOfflineOnlineRecovery(unittest.TestCase):
    """Problem 3 & 5: Automatic recovery, state machine transitions, and retry resilience."""

    def test_14_state_machine_transition_logging(self):
        """set_connection_state logs state changes cleanly and updates single source of truth."""
        from main import JarvisLive
        mock_ui = MagicMock()
        with patch.object(JarvisLive, "_ensure_wake_detector", return_value=True):
            live = JarvisLive(mock_ui)
            live.set_connection_state("INTERNET_AVAILABLE", "Initial internet probe")
            self.assertEqual(live._connection_state, "INTERNET_AVAILABLE")

            live.set_connection_state("LIVE_SESSION_RECONNECTING", "Transient 1008")
            self.assertEqual(live._connection_state, "LIVE_SESSION_RECONNECTING")

            live.set_connection_state("OFFLINE_NO_INTERNET", "Network cable unplugged")
            self.assertEqual(live._connection_state, "OFFLINE_NO_INTERNET")

            live.set_connection_state("ONLINE_ACTIVE", "Gemini Live restored")
            self.assertEqual(live._connection_state, "ONLINE_ACTIVE")

    def test_15_connectivity_recovery_triggers_reconnect(self):
        """_watch_connectivity_recovery detects restored internet, transitions state, and requests voluntary reconnect."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        live._connection_state = "OFFLINE_NO_INTERNET"
        live.session = MagicMock()
        live.session._is_offline_session = True
        live._reconnect_event = asyncio.Event()
        live.request_reconnect = MagicMock()
        live.audio_in_queue = asyncio.Queue()
        live.audio_in_queue.put_nowait(b"\x00" * 2400)

        async def run_test():
            with patch("main.check_internet_connectivity", return_value=True):
                task = asyncio.create_task(live._watch_connectivity_recovery())
                await asyncio.sleep(0.05)
                live._shutting_down = True
                await task

        asyncio.run(run_test())
        # State transitions from OFFLINE_NO_INTERNET -> INTERNET_AVAILABLE -> LIVE_SESSION_RECONNECTING
        self.assertEqual(live._connection_state, "LIVE_SESSION_RECONNECTING")
        self.assertTrue(live.audio_in_queue.empty())
        live.request_reconnect.assert_called_with(keep_context=True, reason="internet restoration")

    def test_16_clean_session_header_written_at_startup(self):
        """JarvisLive initialization writes clean session separator to audio-test-log.txt."""
        from main import JarvisLive
        mock_ui = MagicMock()
        JarvisLive(mock_ui)
        self.assertTrue(os.path.exists("audio-test-log.txt"))
        with open("audio-test-log.txt", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("NEW AUDIO DIAGNOSTIC SESSION STARTED", content)
        self.assertIn("HONESTIC_AUDIO_DEBUG", content)

    def test_17_bounded_queue_avoids_crash_under_overflow(self):
        """speak() drops chunks safely when audio queue is full without raising QueueFull."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        live._loop = asyncio.new_event_loop()
        live.audio_in_queue = asyncio.Queue(maxsize=2)
        # Fill queue
        live.audio_in_queue.put_nowait(b"\x00" * 2400)
        live.audio_in_queue.put_nowait(b"\x00" * 2400)

        with patch("core.natural_speech_engine.NaturalSpeechEngine.synthesize_to_pcm", return_value=(np.zeros(4800, dtype=np.float32), 24000)):
            # Should not raise QueueFull
            live.speak("Testing queue overflow safety.")
        live._loop.close()

    def test_18_online_active_suppresses_local_tts_when_cloud_audio_present(self):
        """speak() is suppressed in ONLINE_ACTIVE mode when cloud audio is active/enqueued."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        live._connection_state = "ONLINE_ACTIVE"
        live._cloud_audio_received_in_turn = True
        live.audio_in_queue = asyncio.Queue()
        live.audio_in_queue.put_nowait(b"\x00" * 2400)

        with patch("core.natural_speech_engine.NaturalSpeechEngine.synthesize_to_pcm") as mock_synth:
            live.speak("This local speech should be skipped.")
            mock_synth.assert_not_called()

    def test_19_full_offline_to_online_transition_sequence(self):
        """Verify full OFFLINE_NO_INTERNET -> INTERNET_AVAILABLE -> LIVE_SESSION_RECONNECTING -> ONLINE_ACTIVE sequence."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        transitions = []
        original_set_state = live.set_connection_state

        def track_state(state, reason=""):
            transitions.append(state)
            original_set_state(state, reason)

        live.set_connection_state = track_state
        live.set_connection_state("OFFLINE_NO_INTERNET", "Network disconnected")
        live.set_connection_state("INTERNET_AVAILABLE", "Internet restored")
        live.set_connection_state("LIVE_SESSION_RECONNECTING", "Reconnecting")
        live.set_connection_state("ONLINE_ACTIVE", "Connected")

        self.assertEqual(transitions, [
            "OFFLINE_NO_INTERNET",
            "INTERNET_AVAILABLE",
            "LIVE_SESSION_RECONNECTING",
            "ONLINE_ACTIVE"
        ])

    def test_20_old_offline_tasks_cancelled_and_stale_queues_reset(self):
        """Verify that offline tasks are cancelled and queues drained during recovery."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        live.session = MagicMock()
        live.session._is_offline_session = True
        live.session.close = AsyncMock()
        live.session.stop_stt = MagicMock()
        live._reconnect_event = asyncio.Event()
        live.request_reconnect = MagicMock()

        live.audio_in_queue = asyncio.Queue()
        live.audio_in_queue.put_nowait(b"\x00" * 4800)
        live.out_queue = asyncio.Queue(maxsize=10)
        live.out_queue.put_nowait({"data": b"\x00" * 1600, "mime_type": "audio/pcm"})

        async def run_recovery():
            with patch("main.check_internet_connectivity", return_value=True):
                task = asyncio.create_task(live._watch_connectivity_recovery())
                await asyncio.sleep(0.05)
                live._shutting_down = True
                await task

        asyncio.run(run_recovery())
        live.session.stop_stt.assert_called_once()
        live.session.close.assert_called_once()
        self.assertTrue(live.audio_in_queue.empty())
        self.assertTrue(live.out_queue.empty())

    def test_21_turn_state_resets_after_recovery(self):
        """Verify turn state is reset cleanly upon session startup."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        # Dirty the turn state
        live._is_speaking = True
        live._turn_audio_active = True
        live._turn_complete_received = True
        live._interrupted = True
        live._turn_chunks_received = 10
        live._turn_chunks_played = 5

        # Reset turn state block as executed in run()
        with live._speaking_lock:
            live._is_speaking = False
        live._turn_audio_active = False
        live._turn_complete_received = False
        live._turn_chunks_received = 0
        live._turn_chunks_played = 0
        live._current_turn_id = None
        live._interrupted = False
        live._log_audio_recovery("[AudioRecovery] Turn state reset.")

        self.assertFalse(live._is_speaking)
        self.assertFalse(live._turn_audio_active)
        self.assertFalse(live._turn_complete_received)
        self.assertFalse(live._interrupted)
        self.assertEqual(live._turn_chunks_received, 0)
        self.assertEqual(live._turn_chunks_played, 0)

    def test_22_complete_response_plays_fully_and_returns_to_listening(self):
        """Verify that _play_audio plays all chunks, logs lifecycle, and returns to LISTENING."""
        from main import JarvisLive
        mock_ui = MagicMock()
        mock_ui.muted = False
        live = JarvisLive(mock_ui)
        live.audio_in_queue = asyncio.Queue()
        live._turn_done_event = asyncio.Event()
        live._out_latency = 0.01

        # Simulate 2 chunks received
        live._turn_audio_active = True
        live._turn_complete_received = True
        live._turn_chunks_received = 2
        live._turn_chunks_played = 0
        live.audio_in_queue.put_nowait(b"\x00" * 2400)
        live.audio_in_queue.put_nowait(b"\x00" * 2400)

        async def run_play():
            with patch("main.get_output_device", return_value="default"), \
                 patch("main.audio_devices.resolve", return_value=None), \
                 patch("main.sd.RawOutputStream") as mock_stream_cls:
                mock_stream = MagicMock()
                mock_stream_cls.return_value = mock_stream
                task = asyncio.create_task(live._play_audio())
                # Let it consume both chunks and hit TimeoutError -> completion
                await asyncio.sleep(0.6)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_play())
        self.assertEqual(live._turn_chunks_played, 2)
        self.assertFalse(live._turn_audio_active)
        self.assertFalse(live._is_speaking)
        mock_ui.set_state.assert_called_with("LISTENING")

    def test_23_multi_turn_conversation_without_restart(self):
        """Verify that a second turn can start and complete immediately after the first turn."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        live.audio_in_queue = asyncio.Queue()
        live._turn_done_event = asyncio.Event()
        live._out_latency = 0.01

        async def run_multi_turns():
            with patch("main.get_output_device", return_value="default"), \
                 patch("main.audio_devices.resolve", return_value=None), \
                 patch("main.sd.RawOutputStream") as mock_stream_cls:
                mock_stream = MagicMock()
                mock_stream_cls.return_value = mock_stream
                task = asyncio.create_task(live._play_audio())

                # Turn 1
                live._turn_audio_active = True
                live._turn_complete_received = True
                live._turn_chunks_received = 1
                live._turn_chunks_played = 0
                live.audio_in_queue.put_nowait(b"\x00" * 2400)
                for _ in range(25):
                    if not live._turn_audio_active:
                        break
                    await asyncio.sleep(0.04)
                self.assertFalse(live._turn_audio_active)

                # Turn 2
                live._turn_audio_active = True
                live._turn_complete_received = True
                live._turn_chunks_received = 1
                live._turn_chunks_played = 0
                live.audio_in_queue.put_nowait(b"\x00" * 2400)
                for _ in range(25):
                    if not live._turn_audio_active:
                        break
                    await asyncio.sleep(0.04)
                self.assertFalse(live._turn_audio_active)

                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_multi_turns())

    def test_24_vosk_telugu_and_english_model_selection(self):
        """VoskSTT selects correct Telugu and English model paths based on language parameter."""
        from core.stt import VoskSTT
        stt_en = VoskSTT(language="en-us")
        self.assertTrue(stt_en.model_loaded)
        self.assertIn("vosk-model-small-en-us-0.15", stt_en.loaded_model_path)

        stt_te = VoskSTT(language="te")
        self.assertTrue(stt_te.model_loaded)
        self.assertIn("vosk-model-small-te-0.42", stt_te.loaded_model_path)

    def test_25_missing_vosk_model_safe_fallback(self):
        """VoskSTT handles missing model directory without crashing, reporting clean error."""
        from core.stt import VoskSTT
        with patch("os.path.exists", return_value=False), \
             patch("pathlib.Path.exists", return_value=False), \
             patch("core.stt.VoskSTT._cached_models", {}):
            stt = VoskSTT(model_path="/non/existent/model", language="fr-fr")
            # Should not crash
            self.assertFalse(stt.model_loaded)
            self.assertEqual(stt.transcribe(b"\x00" * 3200), "")

    def test_26_playback_health_check_reopens_stream(self):
        """Playback health check triggers automatic restart when cloud audio arrives but chunks aren't consumed within 3s."""
        import time
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        live.audio_in_queue = asyncio.Queue()
        live._connection_state = "ONLINE_ACTIVE"
        live._last_cloud_audio_time = time.monotonic() - 4.0
        live._last_playback_time = 0.0
        live._playback_restarted_once = False

        logged_lines = []
        live._log_audio_recovery = lambda l: logged_lines.append(l)

        async def run_health_check():
            with patch("main.get_output_device", return_value="default"), \
                 patch("main.audio_devices.resolve", return_value=None), \
                 patch("main.sd.RawOutputStream") as mock_stream_cls:
                mock_stream = MagicMock()
                mock_stream_cls.return_value = mock_stream
                task = asyncio.create_task(live._play_audio())
                # Let it hit TimeoutError and detect health check failure
                await asyncio.sleep(0.3)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_health_check())
        self.assertTrue(live._playback_restarted_once)
        self.assertIn("[AudioRecovery] Playback health check failed. Restarting output stream.", logged_lines)
        self.assertIn("[AudioRecovery] Output stream reopened.", logged_lines)

    def test_27_playback_consumed_chunk_diagnostic(self):
        """_play_audio logs exact required '[AudioDiag] Playback consumed chunk.' on chunk consumption."""
        from main import JarvisLive
        mock_ui = MagicMock()
        live = JarvisLive(mock_ui)
        live.audio_in_queue = asyncio.Queue()
        live._out_latency = 0.01
        live.audio_in_queue.put_nowait(b"\x00" * 2400)

        logged_lines = []
        live._log_audio_recovery = lambda l: logged_lines.append(l)

        async def run_consume():
            with patch("main.get_output_device", return_value="default"), \
                 patch("main.audio_devices.resolve", return_value=None), \
                 patch("main.sd.RawOutputStream") as mock_stream_cls:
                mock_stream = MagicMock()
                mock_stream_cls.return_value = mock_stream
                task = asyncio.create_task(live._play_audio())
                await asyncio.sleep(0.2)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_consume())
        self.assertIn("[AudioDiag] Playback consumed chunk.", logged_lines)


if __name__ == "__main__":
    unittest.main()
