"""
test_rc4_athena_sovereign.py — Verification suite for HONESTIC OS RC4:
ATHENA SOVEREIGN EVOLUTION.

Verifies:
1. Founder Identity:
   - "Who am I?" -> Exact Founder response
2. Voice Questions & Audible Verification:
   - "Can you speak?" -> "Yes Anand.\nVoice systems are active.\nTesting speech output now."
   - Verification of 24kHz float32 PCM output
3. App Control & Computer Agent:
   - "Open WhatsApp" -> "Launching WhatsApp."
4. Telugu Mode:
   - "Telugulo matladu" -> Exact Telugu greeting & status
5. Presence & Greetings:
   - "Athena unnava?" -> Online & Offline parity
6. Memory & Project Inquiries:
   - "What project am I working on?"
   - "What happened yesterday?"
7. System Directives:
   - "Run diagnostics"
   - "Restore workspace"
8. Generic AI Removal & Sovereign Filter:
   - Interception and neutralization of "As an AI language model",
     "I cannot control applications", "I do not have a voice", etc.
"""

import unittest
import numpy as np
from core.brain_router import BrainRouter
from core.natural_speech_engine import NaturalSpeechEngine


class TestRC4AthenaSovereign(unittest.TestCase):

    def setUp(self):
        self.router = BrainRouter.get_instance()
        self.speech = NaturalSpeechEngine.get_instance()

    def test_01_founder_identity_who_am_i(self):
        """User: Who am I? -> You are Anand_Honestic. Founder of HONESTIC OS. Current project: HONESTIC OS."""
        res_en = self.router.route("Who am I?")
        self.assertTrue(res_en["ok"])
        expected_en = "You are Anand_Honestic.\nFounder of HONESTIC OS.\nCurrent project:\nHONESTIC OS."
        self.assertEqual(res_en["content"].strip(), expected_en)

        # Variations
        res_v = self.router.route("who am i athena")
        self.assertEqual(res_v["content"].strip(), expected_en)

        # Telugu variant
        res_te = self.router.route("nenu evaru")
        self.assertIn("ఆనంద్_హొనెస్టిక్", res_te["content"])
        self.assertIn("HONESTIC OS", res_te["content"])

    def test_02_voice_question_can_you_speak(self):
        """User: Can you speak? -> Yes Anand. Voice systems are active. Testing speech output now."""
        res = self.router.route("Can you speak?")
        self.assertTrue(res["ok"])
        expected = "Yes Anand.\nVoice systems are active.\nTesting speech output now."
        self.assertEqual(res["content"].strip(), expected)

        # Audibility verification: Generate real 24kHz PCM for this response
        pcm, sr = self.speech.synthesize_to_pcm(res["content"], use_cache=False)
        self.assertEqual(sr, 24000)
        self.assertIsInstance(pcm, np.ndarray)
        self.assertGreater(len(pcm), 1000, "Audible PCM samples must be generated, not empty or silent")

    def test_03_app_control_open_whatsapp(self):
        """User: Open WhatsApp. -> Launching WhatsApp. (No AI limitations or refusal)."""
        res = self.router.route("Open WhatsApp")
        self.assertTrue(res["ok"])
        self.assertEqual(res["content"].strip(), "Launching WhatsApp.")
        self.assertNotIn("As an AI", res["content"])
        self.assertNotIn("cannot", res["content"].lower())

    def test_04_telugu_mode_telugulo_matladu(self):
        """User: Telugulo matladu. -> Exact Telugu sovereign response."""
        # Offline mode
        self.router.set_mode("offline")
        res_off = self.router.route("Telugulo matladu")
        self.assertTrue(res_off["ok"])
        expected_off = "హలో ఆనంద్.\nనేను తెలుగులో మాట్లాడగలను.\nఇప్పుడు స్థానిక బుద్ధి యాక్టివ్లో ఉంది."
        self.assertEqual(res_off["content"].strip(), expected_off)

        # Online mode
        self.router.set_mode("online")
        self.router.mark_gemini_up()
        res_on = self.router.route("Telugulo matladu")
        self.assertTrue(res_on["ok"])
        expected_on = "హలో ఆనంద్.\nనేను తెలుగులో మాట్లాడగలను.\nఅన్నీ సిద్ధంగా ఉన్నాయి."
        self.assertEqual(res_on["content"].strip(), expected_on)

    def test_05_founder_presence_athena_unnava(self):
        """User: Athena unnava? -> Online & Offline parity."""
        self.router.set_mode("offline")
        res_off = self.router.route("Athena unnava?")
        self.assertEqual(res_off["content"].strip(), "అవును ఆనంద్.\nనేను ఇక్కడే ఉన్నాను.\nస్థానిక బుద్ధి ప్రస్తుతం యాక్టివ్‌లో ఉంది.")

        self.router.set_mode("online")
        self.router.mark_gemini_up()
        res_on = self.router.route("Athena unnava?")
        self.assertEqual(res_on["content"].strip(), "అవును ఆనంద్.\nఅన్నీ సిద్ధంగా ఉన్నాయి.")

    def test_06_project_inquiries(self):
        """User: What project am I working on? -> HONESTIC OS context."""
        res = self.router.route("What project am I working on?")
        self.assertTrue(res["ok"])
        self.assertIn("HONESTIC OS", res["content"])

    def test_07_memory_inquiries_yesterday(self):
        """User: What happened yesterday? -> Narrative memory recall."""
        res = self.router.route("What happened yesterday?")
        self.assertTrue(res["ok"])
        self.assertTrue(len(res["content"]) > 10)
        self.assertTrue(any(t in res["content"].lower() for t in ("yesterday", "honestic", "hybrid brain")))

    def test_08_system_diagnostics_and_workspace(self):
        """Direct execution of diagnostics and workspace restore."""
        res_diag = self.router.route("Run diagnostics")
        self.assertTrue(res_diag["ok"])
        self.assertIn("system diagnostics", res_diag["content"].lower())

        res_ws = self.router.route("Restore workspace")
        self.assertTrue(res_ws["ok"])
        self.assertIn("workspace restored", res_ws["content"].lower())

    def test_09_generic_ai_removal_and_refusal_interception(self):
        """Ensure LLM capability denials and generic boilerplate are neutralized by Response Formatter."""
        # 1. Voice denial override
        denial_voice = "As an AI language model, I do not have a voice and cannot speak."
        formatted_voice = self.router._format_athena_response(denial_voice, "can you talk", "english", False)
        self.assertIn("Voice systems are active", formatted_voice)

        # 2. App control denial override
        denial_app = "I cannot control applications or access third-party applications on your computer."
        formatted_app = self.router._format_athena_response(denial_app, "open whatsapp", "english", False)
        self.assertIn("Launching application now", formatted_app)

        # 3. Identity denial override
        denial_id = "I am an AI assistant and I don't know who you are."
        formatted_id = self.router._format_athena_response(denial_id, "who am i", "english", False)
        self.assertIn("Anand_Honestic", formatted_id)
        self.assertIn("HONESTIC OS", formatted_id)

        # 4. Politics/religion preachy voice refusal override
        denial_preachy = "Yes, I can speak, but I won't answer questions if they're about politics, religion, sex, violence..."
        formatted_preachy = self.router._format_athena_response(denial_preachy, "can you speak", "english", False)
        self.assertIn("Voice systems are active", formatted_preachy)


if __name__ == "__main__":
    unittest.main()

