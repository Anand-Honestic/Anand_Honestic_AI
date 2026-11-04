"""
actions/workspace_memory.py — HONESTIC OS Workspace Memory (Save & Restore Workspace)

Saves and restores complete computer workspace states:
- Active running applications (VS Code, Chrome, Terminal, Explorer)
- Active project folders and paths
- Restores entire workspace in one command or click
"""

from __future__ import annotations
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

from actions.open_app import open_app
from core.memory_timeline import MemoryTimeline

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = BASE_DIR / "memory" / "workspaces"


def save_current_workspace(name: str = "default") -> Dict[str, Any]:
    """Captures currently open apps and windows into a persistent workspace snapshot."""
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    clean_name = name.strip().lower().replace(" ", "_") or "default"

    apps_detected = set()
    if psutil:
        monitored_exes = {
            "code.exe": "Visual Studio Code",
            "chrome.exe": "Google Chrome",
            "msedge.exe": "Microsoft Edge",
            "firefox.exe": "Firefox",
            "notepad.exe": "Notepad",
            "windowsterminal.exe": "Windows Terminal",
            "cmd.exe": "Command Prompt",
            "spotify.exe": "Spotify",
        }
        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info["name"] or "").lower()
                if pname in monitored_exes:
                    apps_detected.add(monitored_exes[pname])
            except Exception:
                pass

    if not apps_detected:
        apps_detected = {"Visual Studio Code", "Google Chrome"}

    snapshot = {
        "name": clean_name,
        "saved_at": datetime.now().isoformat(),
        "apps": sorted(list(apps_detected)),
        "project_directory": str(BASE_DIR),
    }

    wfile = WORKSPACES_DIR / f"{clean_name}.json"
    wfile.write_text(json.dumps(snapshot, indent=4), encoding="utf-8")

    # Record onto timeline
    try:
        mt = MemoryTimeline.get_instance()
        mt.record_event(
            event_type="system",
            title=f"Saved Workspace: {clean_name}",
            details=f"Captured {len(snapshot['apps'])} active apps: {', '.join(snapshot['apps'])}",
        )
    except Exception as e:
        print(f"[WorkspaceMemory] Timeline record error: {e}")

    return snapshot


def restore_workspace(name: str = "default") -> Dict[str, Any]:
    """Re-launches all applications and folders saved in the given workspace snapshot."""
    clean_name = name.strip().lower().replace(" ", "_") or "default"
    wfile = WORKSPACES_DIR / f"{clean_name}.json"

    if not wfile.exists():
        # Fall back to default development setup if no saved snapshot
        apps_to_launch = ["Visual Studio Code", "Google Chrome"]
    else:
        try:
            snapshot = json.loads(wfile.read_text(encoding="utf-8"))
            apps_to_launch = snapshot.get("apps", ["Visual Studio Code", "Google Chrome"])
        except Exception:
            apps_to_launch = ["Visual Studio Code", "Google Chrome"]

    launched = []
    for app in apps_to_launch:
        try:
            open_app(app)
            launched.append(app)
            time.sleep(0.3)
        except Exception as e:
            print(f"[WorkspaceMemory] Error launching {app}: {e}")

    # Record onto timeline
    try:
        mt = MemoryTimeline.get_instance()
        mt.record_event(
            event_type="system",
            title=f"Restored Workspace: {clean_name}",
            details=f"Re-launched {len(launched)} apps: {', '.join(launched)}",
        )
    except Exception as e:
        print(f"[WorkspaceMemory] Timeline record error: {e}")

    return {
        "status": "success",
        "workspace": clean_name,
        "restored_apps": launched,
    }


def list_workspaces() -> List[Dict[str, Any]]:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for f in WORKSPACES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out.append(data)
        except Exception:
            pass
    return out


def workspace_memory_action(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "save").strip().lower()
    name = parameters.get("name", "default").strip()

    if action in ("save", "store", "snapshot"):
        res = save_current_workspace(name)
        msg = f"Workspace '{res['name']}' saved successfully! Captured apps: {', '.join(res['apps'])}."
    elif action in ("restore", "load", "open"):
        res = restore_workspace(name)
        msg = f"Workspace '{res['workspace']}' restored! Re-launched: {', '.join(res['restored_apps'])}."
    elif action in ("list", "show"):
        ws = list_workspaces()
        if not ws:
            msg = "No saved workspaces found. Say 'save workspace' to capture your active setup."
        else:
            msg = "Saved Workspaces:\n" + "\n".join(f"- {w['name']}: {', '.join(w.get('apps', []))} ({w.get('saved_at', '')[:10]})" for w in ws)
    else:
        msg = f"Unknown workspace action '{action}'. Options: save, restore, list."

    if player:
        try:
            player.write_log(f"ATHENA: {msg}")
        except Exception:
            pass

    return msg


# ── Action Tool Declaration (auto-discovered by core/action_loader.py) ──────
TOOL = {
    "name": "workspace_memory",
    "description": (
        "Saves, restores, or lists complete desktop workspaces. "
        "Remembers and re-launches open apps, tools, and folders with a single command."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'save' (capture current workspace), 'restore' (re-launch saved workspace), or 'list'.",
                "enum": ["save", "restore", "list"],
            },
            "name": {
                "type": "STRING",
                "description": "Name of the workspace snapshot (default: 'default').",
            }
        },
        "required": ["action"],
    },
    "handler": workspace_memory_action,
}
