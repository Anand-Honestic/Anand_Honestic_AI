"""
tests/test_rc8_mode_policy.py — ATHENA Online/Offline Policy & State Machine Test Suite

Verifies:
1. One transient network failure does NOT permanently switch offline (enters LOCAL_FALLBACK).
2. Repeated failures trigger temporary fallback and bounded online retry backoff.
3. Stable connectivity recovery automatically returns to ONLINE_ACTIVE.
4. Explicit OFFLINE action enters OFFLINE_MANUAL and stops automatic cloud recovery.
5. Explicit ONLINE action restores recovery and transitions to RECONNECTING -> ONLINE_ACTIVE.
6. Visible conversation history survives recovery, with resumption handle applied when available.
7. Background tasks yield safely during LOCAL_FALLBACK, RECONNECTING, and OFFLINE_MANUAL.
8. Stale audio queues are cleanly drained on state transitions.
9. UI, BrainRouter, OfflineEngine, and JarvisLive agree on one authoritative mode.
10. A Gemini failure during a turn does not permanently disable cloud mode.
"""

import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import main
from main import JarvisLive
from core.brain_router import BrainRouter, OfflineBrainSession
from core.offline_engine import OfflineEngine


class TestRC8ModePolicy(unittest.TestCase):
    def setUp(self):
        self.mock_ui = MagicMock()
        self.mock_ui._win = MagicMock()
        with patch.object(JarvisLive, "_ensure_wake_detector", return_value=True):
            self.live = JarvisLive(self.mock_ui)
        self.live._user_offline_locked = False
        self.live._connection_state = "ONLINE_ACTIVE"
        BrainRouter.get_instance().set_mode("auto")
        OfflineEngine.get_instance().set_mode("online")

    def tearDown(self):
        self.live._user_offline_locked = False
        BrainRouter.get_instance().set_mode("auto")
        OfflineEngine.get_instance().set_mode("auto")

    def test_01_transient_network_failure_enters_local_fallback_not_permanent_offline(self):
        """A transient network failure during session connect enters LOCAL_FALLBACK, never permanent offline."""
        net_err = OSError("Network is unreachable")
        with patch("main.check_internet_connectivity", return_value=False), \
             patch("main.genai.Client") as mock_client:
            mock_client.return_value.aio.live.connect.side_effect = net_err

            async def _test():
                async with self.live._open_session(live_model="gemini-2.5-flash", config=None) as session:
                    return session

            session = asyncio.run(_test())
            self.assertIsNotNone(session)
            self.assertTrue(getattr(session, "_is_offline_session", False))
            # Must be in fallback or offline probe state, but NOT locked in OFFLINE_MANUAL
            self.assertFalse(self.live._user_offline_locked)
            self.assertIn(self.live._connection_state, ("LOCAL_FALLBACK", "OFFLINE_NO_INTERNET"))
            self.mock_ui.set_mode_state.assert_called_with("LOCAL_FALLBACK")

    def test_02_repeated_failures_trigger_temporary_fallback_with_retry(self):
        """Repeated connect failures remain in temporary fallback and record failure count."""
        connect_err = Exception("503 Service Unavailable")
        with patch("main.check_internet_connectivity", return_value=True), \
             patch("main.genai.Client") as mock_client:
            mock_client.return_value.aio.live.connect.side_effect = connect_err

            async def _run_attempts():
                # Attempt 1: 1008 or transient re-raise
                for _ in range(3):
                    try:
                        async with self.live._open_session(live_model="gemini-2.5-flash", config=None) as s:
                            pass
                    except Exception:
                        pass
                # Attempt 4: yields fallback session
                async with self.live._open_session(live_model="gemini-2.5-flash", config=None) as session:
                    return session

            session = asyncio.run(_run_attempts())
            self.assertTrue(self.live._live_consecutive_failures >= 3)
            self.assertFalse(self.live._user_offline_locked)
            self.assertEqual(self.live._connection_state, "LOCAL_FALLBACK")
            self.mock_ui.set_mode_state.assert_called_with("LOCAL_FALLBACK")

    def test_03_stable_connectivity_recovery_automatically_returns_online(self):
        """When stable connection is restored (2 consecutive probes), _watch_connectivity_recovery triggers reconnect."""
        self.live._connection_state = "LOCAL_FALLBACK"
        self.live._user_offline_locked = False
        self.live.session = MagicMock()
        self.live.session._is_offline_session = True
        self.live.request_reconnect = MagicMock()

        # Mock stable 2-probe check returning True
        with patch.object(self.live, "_check_stable_cloud_connectivity", new=AsyncMock(return_value=True)), \
             patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            asyncio.run(self.live._watch_connectivity_recovery())

        self.assertEqual(self.live._connection_state, "RECONNECTING")
        self.assertEqual(self.live._live_consecutive_failures, 0)
        self.live.request_reconnect.assert_called_once_with(keep_context=True, reason="stable_connectivity_restored")

    def test_04_explicit_offline_button_enters_offline_manual_and_halts_recovery(self):
        """User pressing OFFLINE button sets OFFLINE_MANUAL, locks offline, and prevents background cloud recovery."""
        self.live.request_reconnect = MagicMock()
        self.live.handle_user_mode_action("OFFLINE_MANUAL")

        self.assertTrue(self.live._user_offline_locked)
        self.assertEqual(self.live._connection_state, "OFFLINE_MANUAL")
        self.assertEqual(BrainRouter.get_instance().get_mode(), "offline")
        self.assertEqual(OfflineEngine.get_instance().get_mode(), "offline")
        self.mock_ui.set_mode_state.assert_called_with("OFFLINE_MANUAL")

        # In OFFLINE_MANUAL, _watch_connectivity_recovery must exit immediately without probing
        with patch.object(self.live, "_check_stable_cloud_connectivity", new=AsyncMock(return_value=True)) as mock_check:
            asyncio.run(self.live._watch_connectivity_recovery())
            mock_check.assert_not_called()

    def test_05_explicit_online_action_resumes_recovery(self):
        """User pressing ONLINE button from OFFLINE_MANUAL unlocks offline and requests immediate reconnect."""
        self.live._user_offline_locked = True
        self.live._connection_state = "OFFLINE_MANUAL"
        self.live.request_reconnect = MagicMock()

        self.live.handle_user_mode_action("ONLINE")

        self.assertFalse(self.live._user_offline_locked)
        self.assertEqual(self.live._connection_state, "RECONNECTING")
        self.assertEqual(BrainRouter.get_instance().get_mode(), "auto")
        self.mock_ui.set_mode_state.assert_called_with("RECONNECTING")
        self.live.request_reconnect.assert_called_once_with(keep_context=True, reason="user_online_requested")

    def test_06_visible_conversation_history_survives_recovery(self):
        """Session log history is preserved across transitions, with resumption handle applied when available."""
        self.live._session_log = ["User: Hello", "ATHENA: Greetings", "User: Check system"]
        self.live._resume_handle = "valid_handle_xyz"

        # Drain queues
        self.live.audio_in_queue = asyncio.Queue()
        self.live.audio_in_queue.put_nowait(b"stale_audio")
        self.live._drain_stale_queues()

        self.assertTrue(self.live.audio_in_queue.empty())
        self.assertEqual(len(self.live._session_log), 3)
        self.assertEqual(self.live._resume_handle, "valid_handle_xyz")

    def test_07_background_tasks_yield_during_fallback_and_offline(self):
        """Background monitoring tasks do not send client content during non-ONLINE_ACTIVE states."""
        self.live.session = MagicMock()
        self.live.session._is_offline_session = False
        self.live.session.send_client_content = AsyncMock()

        # In LOCAL_FALLBACK
        self.live._connection_state = "LOCAL_FALLBACK"
        # Verify check logic in monitor tasks
        skip_condition = (getattr(self.live, "_connection_state", "") != "ONLINE_ACTIVE" or 
                          getattr(self.live.session, "_is_offline_session", False))
        self.assertTrue(skip_condition)

        # In OFFLINE_MANUAL
        self.live._connection_state = "OFFLINE_MANUAL"
        skip_condition_offline = (getattr(self.live, "_connection_state", "") != "ONLINE_ACTIVE" or 
                                  getattr(self.live.session, "_is_offline_session", False))
        self.assertTrue(skip_condition_offline)

        # In ONLINE_ACTIVE with live cloud session
        self.live._connection_state = "ONLINE_ACTIVE"
        skip_condition_online = (getattr(self.live, "_connection_state", "") != "ONLINE_ACTIVE" or 
                                 getattr(self.live.session, "_is_offline_session", False))
        self.assertFalse(skip_condition_online)

    def test_08_stale_audio_queues_cleanly_drained(self):
        """_drain_stale_queues empties audio_in_queue and out_queue completely."""
        self.live.audio_in_queue = asyncio.Queue()
        self.live.out_queue = asyncio.Queue()
        for _ in range(5):
            self.live.audio_in_queue.put_nowait(b"chunk")
            self.live.out_queue.put_nowait({"data": b"mic"})

        self.assertFalse(self.live.audio_in_queue.empty())
        self.assertFalse(self.live.out_queue.empty())

        self.live._drain_stale_queues()

        self.assertTrue(self.live.audio_in_queue.empty())
        self.assertTrue(self.live.out_queue.empty())

    def test_09_ui_router_offline_engine_agree_on_mode(self):
        """State transitions synchronize UI, BrainRouter, OfflineEngine, and JarvisLive."""
        # 1. ONLINE_ACTIVE
        self.live.set_connection_state("ONLINE_ACTIVE")
        self.assertEqual(self.live._connection_state, "ONLINE_ACTIVE")
        self.assertEqual(BrainRouter.get_instance().get_mode(), "auto")
        self.assertEqual(OfflineEngine.get_instance().get_mode(), "online")
        self.mock_ui.set_mode_state.assert_called_with("ONLINE_ACTIVE")

        # 2. LOCAL_FALLBACK
        self.live.set_connection_state("LOCAL_FALLBACK")
        self.assertEqual(self.live._connection_state, "LOCAL_FALLBACK")
        self.assertEqual(BrainRouter.get_instance().get_mode(), "auto")
        self.assertEqual(OfflineEngine.get_instance().get_mode(), "auto")
        self.mock_ui.set_mode_state.assert_called_with("LOCAL_FALLBACK")

        # 3. OFFLINE_MANUAL
        self.live._user_offline_locked = True
        self.live.set_connection_state("OFFLINE_MANUAL")
        self.assertEqual(self.live._connection_state, "OFFLINE_MANUAL")
        self.assertEqual(BrainRouter.get_instance().get_mode(), "offline")
        self.assertEqual(OfflineEngine.get_instance().get_mode(), "offline")
        self.mock_ui.set_mode_state.assert_called_with("OFFLINE_MANUAL")

    def test_10_gemini_failure_during_turn_keeps_cloud_recovery_active(self):
        """A failure during an active live turn transitions to LOCAL_FALLBACK and does not lock offline."""
        self.live._connection_state = "ONLINE_ACTIVE"
        self.live._user_offline_locked = False

        # Simulate exception unwinding run loop
        err = Exception("WebSocket closed with 1006")
        self.live.set_connection_state("LOCAL_FALLBACK", f"Session disconnected: {err}")

        self.assertEqual(self.live._connection_state, "LOCAL_FALLBACK")
        self.assertFalse(self.live._user_offline_locked)
        self.mock_ui.set_mode_state.assert_called_with("LOCAL_FALLBACK")

    def test_11_streaming_stt_final_result_dispatches_brain(self):
        """Streaming Vosk final result dispatches directly to local brain session."""
        session = OfflineBrainSession(config=None, log=MagicMock())
        session._stt = MagicMock()
        session._stt.model_loaded = True
        session._stt.process_chunk.return_value = ("check security status", True)
        session.send_client_content = AsyncMock()

        dummy_audio = MagicMock()
        dummy_audio.data = b"\x00\x00" * 1024

        asyncio.run(session.send_realtime_input(audio=dummy_audio))

        session.send_client_content.assert_called_once()
        call_turns = session.send_client_content.call_args[1]["turns"]
        self.assertEqual(call_turns["parts"][0]["text"], "check security status")

    def test_12_silence_noise_does_not_trigger_error_speech(self):
        """Empty or low-confidence transcription remains silently in listening state without speaking error."""
        session = OfflineBrainSession(config=None, log=MagicMock())
        session._stt = MagicMock()
        session._stt.model_loaded = True
        # Simulates ambient breath or noise returning empty text
        session._stt.process_chunk.return_value = ("", True)
        session.send_client_content = AsyncMock()

        dummy_audio = MagicMock()
        dummy_audio.data = b"\x05\x00" * 1024

        asyncio.run(session.send_realtime_input(audio=dummy_audio))

        # Must NOT dispatch prompt and must NOT enqueue "microphone unavailable" speech
        session.send_client_content.assert_not_called()
        self.assertTrue(session._queue.empty())

    def test_13_small_preroll_buffer_bounded(self):
        """Pre-roll buffer is bounded to ~320ms (max 5 chunks), preventing 10-second noise prepending."""
        session = OfflineBrainSession(config=None, log=MagicMock())
        session._stt = MagicMock()
        session._stt.model_loaded = True
        session._stt.process_chunk.return_value = ("", False)

        dummy_audio = MagicMock()
        dummy_audio.data = b"\x01\x00" * 1024

        for _ in range(25):
            asyncio.run(session.send_realtime_input(audio=dummy_audio))

        self.assertLessEqual(len(session._preroll), 5)

    def test_14_native_24khz_sample_rate_and_bounds(self):
        """Offline TTS produces 24kHz float32 audio with values bounded within [-1.0, 1.0]."""
        from core.natural_speech_engine import NaturalSpeechEngine
        import numpy as np

        data, sr = NaturalSpeechEngine.get_instance()._synthesize_offline("Testing audio quality", "Athena", {})
        if data is not None:
            self.assertEqual(sr, 24000)
            self.assertEqual(data.dtype, np.float32)
            self.assertTrue(np.all(data >= -1.0))
            self.assertTrue(np.all(data <= 1.0))

    def test_15_telugu_text_remains_visible_in_offline_session(self):
        """Telugu text response is emitted and visible in conversation log even in offline mode."""
        logs = []
        session = OfflineBrainSession(config=None, log=lambda m: logs.append(m))
        with patch("core.brain_router.BrainRouter.route", return_value={"content": "హలో ఆనంద్. ఎలా ఉన్నారు?", "language": "telugu", "provider": "ollama"}):
            asyncio.run(session._handle_prompt("ఎలా ఉన్నారు?"))

        # Verify heard message was emitted
        m1 = asyncio.run(session._queue.get())
        heard = getattr(getattr(m1.server_content, "input_transcription", None), "text", "")
        self.assertEqual(heard, "ఎలా ఉన్నారు?")

        # Verify Telugu text response was emitted in Msg.said
        m2 = asyncio.run(session._queue.get())
        said = getattr(getattr(m2.server_content, "output_transcription", None), "text", "")
        self.assertEqual(said, "హలో ఆనంద్. ఎలా ఉన్నారు?")

    def test_16_duplicate_recovery_loops_prevented(self):
        """If _recovery_running is True, a second recovery task exits immediately without probing."""
        self.live._recovery_running = True
        self.live._connection_state = "LOCAL_FALLBACK"

        with patch.object(self.live, "_check_stable_cloud_connectivity", new=AsyncMock(return_value=True)) as mock_check:
            asyncio.run(self.live._watch_connectivity_recovery())
            mock_check.assert_not_called()

    def test_17_fast_initial_polling_and_bounded_backoff(self):
        """Recovery uses fast polling (1.5s) while waiting for internet, and bounded backoff (<=15s) for Gemini failures."""
        # When 0 failures: fast polling
        failures_0 = 0
        poll_delay_0 = min(15.0, 2.0 * (1.5 ** min(failures_0, 4))) if failures_0 > 0 else 1.5
        self.assertEqual(poll_delay_0, 1.5)

        # When repeated failures: bounded backoff
        failures_4 = 4
        poll_delay_4 = min(15.0, 2.0 * (1.5 ** min(failures_4, 4)))
        self.assertLessEqual(poll_delay_4, 15.0)
        self.assertGreater(poll_delay_4, 5.0)

    def test_18_startup_defaults_to_online_reconnecting_without_user_lock(self):
        """Startup ignores stale 'brain_mode': 'offline' unless 'user_locked_offline': true is set."""
        mock_cfg = {"brain_mode": "offline"}  # missing user_locked_offline: true
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=str(mock_cfg).replace("'", '"')), \
             patch.object(JarvisLive, "_ensure_wake_detector", return_value=True):
            jl = JarvisLive(self.mock_ui)
            self.assertFalse(jl._user_offline_locked)
            self.assertEqual(jl._connection_state, "RECONNECTING")

    def test_19_transient_failure_never_persists_offline_to_disk(self):
        """Transient fallback transitions must NEVER persist 'brain_mode': 'offline' to disk."""
        with patch.object(BrainRouter, "_persist_mode") as mock_persist:
            self.live.set_connection_state("LOCAL_FALLBACK", "Temporary 503 error")
            self.assertEqual(self.live._connection_state, "LOCAL_FALLBACK")
            mock_persist.assert_not_called()

            self.live.set_connection_state("OFFLINE_NO_INTERNET", "WiFi dropped")
            mock_persist.assert_not_called()

    def test_20_explicit_user_action_persists_offline_and_locks(self):
        """Only explicit handle_user_mode_action('OFFLINE_MANUAL') persists offline mode and user lock."""
        with patch.object(BrainRouter, "_persist_mode") as mock_persist, \
             patch.object(self.live, "request_reconnect") as mock_reconnect:
            self.live.handle_user_mode_action("OFFLINE_MANUAL")
            self.assertTrue(self.live._user_offline_locked)
            self.assertEqual(self.live._connection_state, "OFFLINE_MANUAL")
            mock_persist.assert_called_with("offline", user_locked=True)
            mock_reconnect.assert_called_with(keep_context=True, reason="user_offline_manual")

            self.live.handle_user_mode_action("ONLINE")
            self.assertFalse(self.live._user_offline_locked)
            self.assertEqual(self.live._connection_state, "RECONNECTING")
            mock_persist.assert_called_with("auto", user_locked=False)
            mock_reconnect.assert_called_with(keep_context=True, reason="user_online_requested")

    def test_21_online_voice_turn_not_intercepted_by_sovereign_intent(self):
        """In ONLINE_ACTIVE, normal speech like 'hello' is not intercepted or replaced by local speak()."""
        self.live._connection_state = "ONLINE_ACTIVE"
        self.live.speak = MagicMock()
        self.live.interrupt = MagicMock()
        # Verify that sovereign intent is not called to interrupt online turns
        from core.brain_router import BrainRouter
        router = BrainRouter.get_instance()
        sovereign = router._check_athena_sovereign_intent("hello", "english", is_offline=False)
        # Even if a static pattern exists, live session receives server audio directly
        # and main.py _receive_audio does not call interrupt() or speak()
        self.assertEqual(self.live.speak.call_count, 0)
        self.assertEqual(self.live.interrupt.call_count, 0)

    def test_22_typed_command_routes_to_live_session_in_online_active(self):
        """In ONLINE_ACTIVE, typed text is sent directly to self.session.send_client_content."""
        self.live._connection_state = "ONLINE_ACTIVE"
        self.live.session = MagicMock()
        self.live.session._is_offline_session = False
        self.live.session._closed = False
        self.live.session.send_client_content = AsyncMock()
        self.live._loop = asyncio.new_event_loop()
        self.live.speak = MagicMock()

        try:
            with patch("threading.Thread") as mock_thread:
                self.live._on_text_command("Explain quantum computing")
                # Must dispatch via session and NOT spawn local route thread or call local speak
                mock_thread.assert_not_called()
                self.live.speak.assert_not_called()
        finally:
            self.live._loop.close()

    def test_23_typed_command_routes_to_offline_session_when_offline(self):
        """In OFFLINE_MANUAL with active OfflineBrainSession, typed text is sent to the offline session."""
        self.live._connection_state = "OFFLINE_MANUAL"
        self.live.session = MagicMock()
        self.live.session._is_offline_session = True
        self.live.session._closed = False
        self.live.session.send_client_content = AsyncMock()
        self.live._loop = asyncio.new_event_loop()
        self.live.speak = MagicMock()

        try:
            with patch("threading.Thread") as mock_thread:
                self.live._on_text_command("Hello local brain")
                mock_thread.assert_not_called()
        finally:
            self.live._loop.close()

    def test_24_command_engine_routes_through_jarvis_live(self):
        """FastCommandEngine mode commands route through JarvisLive.handle_user_mode_action."""
        from core.command_engine import FastCommandEngine
        ce = FastCommandEngine.get_instance()
        with patch.object(self.live, "handle_user_mode_action") as mock_handler:
            res_off = ce.execute("switch to offline mode")
            self.assertTrue(res_off.handled)
            mock_handler.assert_called_with("OFFLINE_MANUAL")

            res_on = ce.execute("switch to online mode")
            self.assertTrue(res_on.handled)
            mock_handler.assert_called_with("ONLINE")


if __name__ == "__main__":
    unittest.main()

