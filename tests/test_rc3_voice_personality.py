"""
test_rc3_voice_personality.py — Verification suite for HONESTIC OS RC3:
OFFLINE ATHENA VOICE & PERSONALITY EVOLUTION.

Verifies:
1. Unified ATHENA Personality:
   - Offline "Athena unnava?" -> "అవును ఆనంద్.\nనేను ఇక్కడే ఉన్నాను.\nస్థానిక బుద్ధి ప్రస్తుతం యాక్టివ్‌లో ఉంది."
   - Online "Athena unnava?" -> "అవును ఆనంద్.\nఅన్నీ సిద్ధంగా ఉన్నాయి."
   - English "Hello" -> "Hello Anand.\nEverything looks ready.\nWhat would you like to work on?"
   - Telugu "హలో" -> "హలో ఆనంద్.\nనేను ఉన్నాను. ఏం పని చేద్దాం?"
2. Language Detection:
   - Telugu Unicode script
   - Transliterated Telugu tokens (unnava, em pani cheddam)
   - English & Mixed detection
3. ATHENA Response Formatter:
   - Stripping of <think>...</think> and <thought>...</thought> tags
   - Elimination of generic model greetings ("Hello! How can I assist you today?", "Certainly! Here is...")
   - Fallback to warm ATHENA persona
4. Voice Pipeline & Telemetry:
   - test_voice_pipeline() -> Text Generated, PCM Generated, Audio Device, Playback, Speech Output
   - get_debug_status() -> STT, LLM, TTS, Audio, Mic, Speaker, Voice Device
   - 24kHz float32 PCM generation via Windows SAPI / OneCore
5. OfflineBrainSession:
   - End-to-end event stream emitting Msg.said, Msg.audio, and Msg.turn_end
"""

import asyncio
import unittest
import numpy as np
from core.brain_router import BrainRouter, OfflineBrainSession
from core.natural_speech_engine import NaturalSpeechEngine


class TestRC3VoiceAndPersonality(unittest.TestCase):

    def setUp(self):
        self.router = BrainRouter.get_instance()
        self.speech = NaturalSpeechEngine.get_instance()

    def test_01_language_detection(self):
        """Verify automatic language detection across Telugu, transliterated Telugu, and English."""
        # Telugu Unicode script
        self.assertEqual(self.router._detect_language("హలో ఆనంద్"), "telugu")
        self.assertEqual(self.router._detect_language("అవును ఉన్నాను"), "telugu")

        # Transliterated Telugu
        self.assertEqual(self.router._detect_language("Athena unnava?"), "telugu")
        self.assertEqual(self.router._detect_language("em pani cheddam"), "telugu")

        # Mixed Telugu + English
        self.assertEqual(self.router._detect_language("Athena unnava project status enti"), "mixed")
        self.assertEqual(self.router._detect_language("హలో Anand, let's work"), "mixed")

        # Pure English
        self.assertEqual(self.router._detect_language("Hello Athena"), "english")
        self.assertEqual(self.router._detect_language("Write a Python function to sort numbers"), "english")

    def test_02_founder_presence_offline(self):
        """Athena unnava? in offline mode must return the exact Telugu founder presence statement."""
        self.router.set_mode("offline")
        res = self.router.route("Athena unnava?")
        self.assertTrue(res["ok"])
        expected = "అవును ఆనంద్.\nనేను ఇక్కడే ఉన్నాను.\nస్థానిక బుద్ధి ప్రస్తుతం యాక్టివ్‌లో ఉంది."
        self.assertEqual(res["content"], expected)

        # Variations
        res2 = self.router.route("unnava athena")
        self.assertEqual(res2["content"], expected)

    def test_03_founder_presence_online(self):
        """Athena unnava? in online mode must return the exact online presence statement."""
        self.router.set_mode("online")
        self.router.mark_gemini_up()
        res = self.router.route("Athena unnava?")
        self.assertTrue(res["ok"])
        expected = "అవును ఆనంద్.\nఅన్నీ సిద్ధంగా ఉన్నాయి."
        self.assertEqual(res["content"], expected)

    def test_04_founder_greetings_english_and_telugu(self):
        """Verify natural greetings for English and Telugu without robotic boilerplate."""
        res_en = self.router.route("Hello")
        self.assertEqual(res_en["content"], "Hello Anand.\nEverything looks ready.\nWhat would you like to work on?")

        res_hi = self.router.route("Hi Athena")
        self.assertEqual(res_hi["content"], "Hello Anand.\nEverything looks ready.\nWhat would you like to work on?")

        res_te = self.router.route("హలో")
        self.assertEqual(res_te["content"], "హలో ఆనంద్.\nనేను ఉన్నాను. ఏం పని చేద్దాం?")

    def test_05_response_formatter_strips_boilerplate(self):
        """Ensure <think> tags, generic greetings, and canned phrases are thoroughly stripped."""
        # 1. Strips generic greetings
        raw = "Hello! How can I assist you today? Here is the requested code:\n```python\nprint(1)\n```"
        formatted = self.router._format_athena_response(raw, "write code", "english", False)
        self.assertNotIn("Hello! How can I assist you today?", formatted)
        self.assertIn("```python\nprint(1)\n```", formatted)

        # 2. Strips <think> tags from reasoning models
        raw_think = "<think>The user wants to add two numbers</think>```python\ndef add(a, b): return a + b\n```"
        formatted_think = self.router._format_athena_response(raw_think, "add numbers", "english", False)
        self.assertNotIn("<think>", formatted_think)
        self.assertIn("def add(a, b)", formatted_think)

        # 3. Strips Certainly! Here's...
        raw_certain = "Certainly! Here is the python function:\ndef foo(): pass"
        formatted_certain = self.router._format_athena_response(raw_certain, "function", "english", False)
        self.assertNotIn("Certainly! Here is", formatted_certain)
        self.assertIn("def foo(): pass", formatted_certain)

        # 4. Pure empty / generic replacement
        formatted_empty = self.router._format_athena_response("Hello! How can I help you today?", "hi", "english", False)
        self.assertEqual(formatted_empty, "Hello Anand.\nEverything looks ready.\nWhat would you like to work on?")

    def test_06_voice_pipeline_audit(self):
        """Verify end-to-end Voice Center audit returning all 5 verified checkpoints."""
        res = self.speech.test_voice_pipeline()
        self.assertTrue(res["text_generated"])
        self.assertTrue(res["pcm_generated"])
        self.assertTrue(res["audio_device"])
        self.assertTrue(res["playback"])
        self.assertTrue(res["speech_output"])
        self.assertEqual(res["sample_rate"], 24000)
        self.assertGreater(res["samples"], 0)
        self.assertIn("Optimal", res["status"])

    def test_07_voice_debug_status(self):
        """Verify Debug Panel returns complete status telemetry across all 7 fields."""
        dbg = self.speech.get_debug_status()
        self.assertIn("stt_status", dbg)
        self.assertIn("llm_status", dbg)
        self.assertIn("tts_status", dbg)
        self.assertIn("audio_status", dbg)
        self.assertIn("mic_status", dbg)
        self.assertIn("speaker_status", dbg)
        self.assertIn("voice_device", dbg)

    def test_08_offline_speech_synthesis_audio(self):
        """Verify native offline SAPI generates actual 24kHz PCM for both English and Telugu."""
        pcm_en, sr_en = self.speech._synthesize_offline("Hello Anand. All systems ready.", "Athena", {"speed": 50})
        self.assertEqual(sr_en, 24000)
        self.assertIsInstance(pcm_en, np.ndarray)
        self.assertGreater(len(pcm_en), 1000)

        pcm_te, sr_te = self.speech._synthesize_offline("అవును ఆనంద్. నేను ఇక్కడే ఉన్నాను.", "Athena", {"speed": 50})
        self.assertEqual(sr_te, 24000)
        self.assertIsInstance(pcm_te, np.ndarray)
        self.assertGreater(len(pcm_te), 1000)

    def test_09_offline_brain_session_flow(self):
        """Verify OfflineBrainSession emits transcript, PCM audio, and turn_end events."""
        async def _run():
            session = OfflineBrainSession()
            self.assertTrue(session._is_offline_session)

            # Send presence query
            await session.send_client_content(turns={"parts": [{"text": "Athena unnava?"}]})

            received_said = False
            received_audio = False
            received_turn_end = False

            # Drain queue
            for _ in range(5):
                try:
                    msg = await asyncio.wait_for(session._queue.get(), timeout=3.0)
                    if getattr(msg, "data", None) is not None:
                        received_audio = True
                        self.assertGreater(len(msg.data), 0)
                    sc = getattr(msg, "server_content", None)
                    if sc:
                        if getattr(sc, "output_transcription", None):
                            received_said = True
                            self.assertIn("అవును ఆనంద్", sc.output_transcription.text)
                        if getattr(sc, "turn_complete", False):
                            received_turn_end = True
                    if received_said and received_audio and received_turn_end:
                        break
                except asyncio.TimeoutError:
                    break

            await session.close()
            self.assertTrue(received_said, "OfflineBrainSession should emit transcript via Msg.said")
            self.assertTrue(received_audio, "OfflineBrainSession should emit 24kHz PCM audio via Msg.audio")
            self.assertTrue(received_turn_end, "OfflineBrainSession should emit turn completion via Msg.turn_end")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
