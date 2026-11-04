"""
actions/automation_engine.py — HONESTIC OS Automation System & Routines

Routines:
- Study Mode (Chrome, Notes, VS Code, focus audio)
- Gaming Mode (Gaming performance, audio, game launchers)
- Work Mode (VS Code, Terminal, Browser, System check)
- Night Mode (Dim brightness, dark theme, low volume)
"""

from __future__ import annotations
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any

from actions.open_app import open_app
from actions.computer_settings import volume_set, brightness_set


ROUTINES: Dict[str, Dict[str, Any]] = {
    "study": {
        "name": "Study Mode",
        "description": "Launches Chrome, Notes, and VS Code; sets focus volume.",
        "apps": ["chrome", "notepad", "code"],
        "volume": 25,
        "brightness": 70,
        "announcement": "Study Mode active. Chrome, Notes, and VS Code launched with focus audio.",
    },
    "gaming": {
        "name": "Gaming Mode",
        "description": "Optimizes system for gaming, tunes audio and launches gaming hubs.",
        "apps": ["steam", "discord"],
        "volume": 70,
        "brightness": 90,
        "announcement": "Gaming Mode activated. Audio tuned and performance unleashed.",
    },
    "work": {
        "name": "Work Mode",
        "description": "Launches development workspace: VS Code, Terminal, and Browser.",
        "apps": ["code", "cmd", "chrome"],
        "volume": 35,
        "brightness": 80,
        "announcement": "Work Mode engaged. Development environment ready.",
    },
    "night": {
        "name": "Night Mode",
        "description": "Lowers brightness to 20%, lowers volume to 15%, sets quiet night mode.",
        "apps": [],
        "volume": 15,
        "brightness": 20,
        "announcement": "Night Mode activated. Display dimmed and audio lowered for the night.",
    },
}


def trigger_routine(routine_name: str, params: Optional[dict] = None) -> str:
    key = (routine_name or "").strip().lower()
    if key not in ROUTINES:
        return f"Unknown routine '{routine_name}'. Available: {', '.join(ROUTINES.keys())}"

    routine = ROUTINES[key]

    # Adjust volume
    if "volume" in routine:
        try:
            volume_set(routine["volume"])
        except Exception:
            pass

    # Adjust brightness
    if "brightness" in routine:
        try:
            brightness_set(routine["brightness"])
        except Exception:
            pass

    # Launch apps
    for app in routine.get("apps", []):
        try:
            open_app(app)
            time.sleep(0.3)
        except Exception as e:
            print(f"[Automation] Error launching {app}: {e}")

    return routine.get("announcement", f"{routine['name']} initiated.")


def automation_action(parameters: dict, player=None, session_memory=None) -> str:
    routine = parameters.get("routine", "work")
    msg = trigger_routine(routine)
    if player:
        try:
            player.write_log(f"ATHENA: {msg}")
        except Exception:
            pass
    return msg


# ── Action Tool Declaration ──────────────────────────────────────────────────
TOOL = {
    "name": "activate_routine",
    "description": (
        "Activates automated operating system routines: "
        "'study' (Study Mode — opens Chrome, Notes, VS Code), "
        "'gaming' (Gaming Mode), "
        "'work' (Work Mode — opens VS Code, Terminal, Browser), or "
        "'night' (Night Mode — dims screen, lowers audio)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "routine": {
                "type": "STRING",
                "description": "The routine to activate: 'study', 'gaming', 'work', or 'night'",
                "enum": ["study", "gaming", "work", "night"],
            }
        },
        "required": ["routine"],
    },
    "handler": automation_action,
}

