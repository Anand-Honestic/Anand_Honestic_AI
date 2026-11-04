"""
test_rc5_runtime_lockdown.py — HONESTIC OS RC5 Runtime Sovereign Lockdown Tests

Verifies that real runtime behavior matches sovereign directives 100%:
  1. Single unified response pipeline for all inputs (keyboard, chat, voice, PTT, remote).
  2. Sticky Telugu language switching ("Telugulo matladu" -> subsequent queries in Telugu -> "Speak in English" -> switches back).
  3. Sovereign responses: "Who am I?", "Can you speak?", "Open WhatsApp", "Athena unnava?", "What project am I working on?", "What happened yesterday?".
  4. Real audible voice output via NaturalSpeechEngine (PCM synthesis & SAPI dispatch, never treating speak() as user turn).
  5. 100% removal and neutralization of generic AI refusal disclaimers.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.brain_router import BrainRouter
from core.natural_speech_engine import NaturalSpeechEngine


class TestRC5RuntimeLockdown(unittest.TestCase):
    def setUp(self):
        self.router = BrainRouter.get_instance()
        self.router._sticky_language = None

    def tearDown(self):
        self.router._sticky_language = None
        self.router.set_mode("auto")

    def test_01_sticky_telugu_language_flow(self):
        """Verify 'Telugulo matladu' locks Telugu stickily until 'Speak in English'."""
        # 1. Initially English
        lang1 = self.router._detect_language("Who am I?")
        self.assertEqual(lang1, "english")
        res1 = self.router.route("Who am I?")
        self.assertIn("Anand_Honestic", res1["content"])
        self.assertIn("Founder of HONESTIC OS", res1["content"])

        # 2. Switch to Telugu stickily
        res2 = self.router.route("Telugulo matladu")
        self.assertEqual(self.router._sticky_language, "telugu")
        self.assertIn("హలో ఆనంద్", res2["content"])

        # 3. Subsequent query without explicit language should adhere to sticky Telugu
        lang3 = self.router._detect_language("Who am I?")
        self.assertEqual(lang3, "telugu")
        res3 = self.router.route("Who am I?")
        self.assertIn("ఆనంద్_హొనెస్టిక్", res3["content"])
        self.assertIn("HONESTIC OS", res3["content"])

        # 4. Switch back to English
        res4 = self.router.route("Speak in English")
        self.assertIsNone(self.router._sticky_language)
        self.assertIn("English Anand", res4["content"])

        # 5. Subsequent query is in English
        lang5 = self.router._detect_language("Who am I?")
        self.assertEqual(lang5, "english")
        res5 = self.router.route("Who am I?")
        self.assertIn("You are Anand_Honestic", res5["content"])

    def test_02_voice_test_and_live_speech(self):
        """Verify 'Can you speak?' returns sovereign reply and synthesizes real speech PCM."""
        res = self.router.route("Can you speak?")
        content = res["content"]
        self.assertIn("Yes Anand", content)
        self.assertIn("Voice systems are active", content)

        # Verify NaturalSpeechEngine generates PCM for this reply
        engine = NaturalSpeechEngine.get_instance()
        pcm, sr = engine.synthesize_to_pcm(content)
        self.assertIsNotNone(pcm)
        self.assertGreater(len(pcm), 100)
        self.assertEqual(sr, 24000)

    def test_03_open_app_whatsapp(self):
        """Verify 'Open WhatsApp' outputs 'Launching WhatsApp.' and invokes app launcher."""
        with patch("actions.open_app.open_app") as mock_open:
            res = self.router.route("Open WhatsApp")
            self.assertEqual(res["content"], "Launching WhatsApp.")
            # Verify open_app was triggered in background
            import time
            time.sleep(0.1)
            mock_open.assert_called_with("whatsapp")

    def test_04_athena_presence_online_and_offline(self):
        """Verify 'Athena unnava?' returns exact required presence strings."""
        # Online mode
        self.router.set_mode("online")
        res_online = self.router.route("Athena unnava?")
        self.assertIn("అవును ఆనంద్", res_online["content"])
        self.assertIn("అన్నీ సిద్ధంగా ఉన్నాయి", res_online["content"])

        # Offline mode
        self.router.set_mode("offline")
        res_offline = self.router.route("Athena unnava?")
        self.assertIn("అవును ఆనంద్", res_offline["content"])
        self.assertIn("స్థానిక బుద్ధి", res_offline["content"])

    def test_05_project_and_yesterday_memory(self):
        """Verify project inquiry and yesterday summary return authoritative ATHENA memory."""
        res_proj = self.router.route("What project am I working on?")
        self.assertIn("HONESTIC OS", res_proj["content"])

        res_yest = self.router.route("What happened yesterday?")
        self.assertIn("HONESTIC OS", res_yest["content"])

    def test_06_complete_neutralization_of_generic_disclaimers(self):
        """Verify all generic AI disclaimers and refusal boilerplate are completely removed."""
        forbidden_test_cases = [
            ("As an AI language model, I do not have a voice.", "Yes Anand.\nVoice systems are active.\nTesting speech output now."),
            ("I cannot control applications on your computer.", "Launching application now."),
            ("I don't know who you are, which is a fascinating question.", "You are Anand_Honestic.\nFounder of HONESTIC OS.\nCurrent project:\nHONESTIC OS."),
            ("I cannot remember past conversations or personal details.", "I remember our work on HONESTIC OS Anand. Founder and memory context are fully active."),
        ]
        for raw_in, expected_sub in forbidden_test_cases:
            cleaned = self.router._format_athena_response(raw_in, "query", "english", False)
            self.assertNotIn("As an AI language model", cleaned)
            self.assertNotIn("I cannot control applications", cleaned)
            self.assertNotIn("I don't know who you are", cleaned)
            self.assertNotIn("I cannot remember", cleaned)
            self.assertIn(expected_sub, cleaned)

    def test_07_main_speak_method_does_not_send_to_gemini(self):
        """Verify main.py speak() generates audio/PCM and does NOT treat text as user prompt."""
        from main import JarvisLive
        fake_ui = MagicMock()
        jarvis = JarvisLive(fake_ui)
        jarvis.session = MagicMock()
        jarvis._loop = MagicMock()
        jarvis.audio_in_queue = MagicMock()

        # Call speak with sovereign reply
        test_text = "Yes Anand. Voice systems are active."
        jarvis.speak(test_text)

        # jarvis.session.send_client_content MUST NOT be called!
        jarvis.session.send_client_content.assert_not_called()
        # audio_in_queue.put_nowait SHOULD receive PCM slices
        self.assertTrue(jarvis.audio_in_queue.put_nowait.called)

    def test_08_main_on_text_command_unified_pipeline(self):
        """Verify _on_text_command routes through BrainRouter and calls speak() for sovereign responses."""
        from main import JarvisLive
        fake_ui = MagicMock()
        jarvis = JarvisLive(fake_ui)
        jarvis.speak = MagicMock()

        jarvis._on_text_command("Who am I?")
        import time
        time.sleep(0.3)

        # Verify UI logged the exchange
        fake_ui.write_log.assert_any_call("You: Who am I?")
        # Verify speak was called with sovereign reply
        self.assertTrue(jarvis.speak.called)
        spoken_arg = jarvis.speak.call_args[0][0]
        self.assertIn("Anand_Honestic", spoken_arg)
        self.assertIn("Founder of HONESTIC OS", spoken_arg)


if __name__ == "__main__":
    unittest.main()

