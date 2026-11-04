"""
actions/visual_learning.py — HONESTIC OS Visual Learning Action Tool

Exposes 7-part visual learning modules (explanation, diagram, architecture, real example, quiz)
to Gemini Live and the UI.
"""

from __future__ import annotations
from core.visual_learning import VisualLearningEngine


def visual_learning_action(parameters: dict, player=None, session_memory=None) -> str:
    topic = parameters.get("topic", "DNS").strip()
    engine = VisualLearningEngine.get_instance()
    mod = engine.explain(topic)

    text_resp = (
        f"Visual Learning Card for [{mod['title']}]\n\n"
        f"1. Explanation: {mod['explanation']}\n\n"
        f"2. Architecture & Flow:\n{mod['diagram']}\n"
        f"3. Real Example:\n{mod['real_example']}\n\n"
        f"4. Quick Knowledge Check:\n"
        f"{mod['quiz']['question']}\n" +
        "\n".join(mod['quiz']['options']) +
        f"\n(Answer: {mod['quiz']['correct']} — {mod['quiz']['explanation']})"
    )

    if player:
        try:
            player.write_log(f"ATHENA: Generated Visual Learning Blueprint for '{mod['title']}'.")
        except Exception:
            pass

    return text_resp


# ── Action Tool Declaration (auto-discovered by core/action_loader.py) ──────
TOOL = {
    "name": "visual_learning",
    "description": (
        "Generates a complete visual learning package for any topic (DNS, HTTP, HTTPS, "
        "Linux, Networking, Python, Cybersecurity, Coding, AI, Architecture, etc.). "
        "Outputs explanation, ASCII/flowchart diagram, component topology, real code example, and quiz."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "topic": {
                "type": "STRING",
                "description": "The technical topic to visually explain (e.g. 'DNS', 'HTTPS', 'Python', 'Linux').",
            }
        },
        "required": ["topic"],
    },
    "handler": visual_learning_action,
}
