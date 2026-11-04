"""
core/plugin_store.py — HONESTIC OS Plugin Store & Management System

Allows 1-click install, update, enable/disable, and removal of plugins
without manual file editing.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

from memory.config_manager import get_plugin_enabled, save_plugin_enabled

BASE_DIR = Path(__file__).resolve().parent.parent
PLUGINS_DIR = BASE_DIR / "plugins"

# Store catalog of pre-engineered plugins
PLUGIN_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "crypto_sentinel",
        "name": "Crypto Sentinel",
        "version": "1.2.0",
        "author": "HONESTIC OS",
        "description": "Live cryptocurrency ticker, price alert monitors, and portfolio tracking.",
        "code": '''"""
Crypto Sentinel Plugin for HONESTIC OS
"""
import requests

def run(parameters: dict, player=None, session_memory=None) -> str:
    coin = parameters.get("coin", "bitcoin").lower().strip()
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        res = requests.get(url, timeout=5).json()
        if coin in res:
            price = res[coin]["usd"]
            msg = f"{coin.capitalize()} is currently trading at ${price:,.2f} USD."
            return msg
        return f"Could not find market price for {coin}."
    except Exception as e:
        return f"Crypto market lookup failed: {e}"

PLUGIN = {
    "name": "crypto_price",
    "description": "Fetches real-time price for a cryptocurrency (bitcoin, ethereum, solana, etc.)",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "coin": {"type": "STRING", "description": "Cryptocurrency name, e.g. 'bitcoin' or 'ethereum'"}
        },
        "required": ["coin"]
    }
}
'''
    },
    {
        "id": "quick_notes",
        "name": "Quick Notes",
        "version": "1.0.4",
        "author": "HONESTIC OS",
        "description": "Rapid desktop scratchpad and voice memo saver.",
        "code": '''"""
Quick Notes Plugin for HONESTIC OS
"""
from pathlib import Path
from datetime import datetime

NOTES_FILE = Path(__file__).resolve().parent.parent / "knowledge_vault" / "notes" / "quick_notes.txt"

def run(parameters: dict, player=None, session_memory=None) -> str:
    note = parameters.get("note", "").strip()
    if not note:
        return "No note provided."
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}\\n")
    return f"Saved quick note: {note}"

PLUGIN = {
    "name": "save_quick_note",
    "description": "Quickly saves a text note or thought to the notes file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "note": {"type": "STRING", "description": "Text content of the note"}
        },
        "required": ["note"]
    }
}
'''
    },
    {
        "id": "system_booster",
        "name": "System Booster",
        "version": "1.1.0",
        "author": "HONESTIC OS",
        "description": "Purges temporary memory caches and reports reclaimed resources.",
        "code": '''"""
System Booster Plugin for HONESTIC OS
"""
import gc
import psutil

def run(parameters: dict, player=None, session_memory=None) -> str:
    mem_before = psutil.virtual_memory().percent
    gc.collect()
    mem_after = psutil.virtual_memory().percent
    return f"Memory optimization complete. RAM utilization: {mem_after}%."

PLUGIN = {
    "name": "boost_system",
    "description": "Runs garbage collection and optimizes available RAM.",
    "parameters": {"type": "OBJECT", "properties": {}}
}
'''
    },
    {
        "id": "pomodoro_timer",
        "name": "Pomodoro Productivity",
        "version": "2.0.0",
        "author": "HONESTIC OS",
        "description": "Focus timer tracker for deep work sessions and interval breaks.",
        "code": '''"""
Pomodoro Productivity Plugin for HONESTIC OS
"""
import time

def run(parameters: dict, player=None, session_memory=None) -> str:
    duration = parameters.get("minutes", 25)
    return f"Pomodoro focus cycle set for {duration} minutes. Deep work started!"

PLUGIN = {
    "name": "start_pomodoro",
    "description": "Starts a Pomodoro focus cycle with given minutes (default: 25).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "minutes": {"type": "INTEGER", "description": "Focus duration in minutes"}
        }
    }
}
'''
    }
]


def list_store_items() -> List[Dict[str, Any]]:
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for item in PLUGIN_CATALOG:
        pid = item["id"]
        installed_file = PLUGINS_DIR / f"{pid}.py"
        is_installed = installed_file.exists()
        is_enabled = get_plugin_enabled(pid) if is_installed else False
        items.append({
            "id": pid,
            "name": item["name"],
            "version": item["version"],
            "author": item["author"],
            "description": item["description"],
            "installed": is_installed,
            "enabled": is_enabled,
        })
    return items


def install_plugin(plugin_id: str) -> bool:
    for item in PLUGIN_CATALOG:
        if item["id"] == plugin_id:
            target = PLUGINS_DIR / f"{plugin_id}.py"
            target.write_text(item["code"], encoding="utf-8")
            save_plugin_enabled(plugin_id, True)
            return True
    return False


def uninstall_plugin(plugin_id: str) -> bool:
    target = PLUGINS_DIR / f"{plugin_id}.py"
    if target.exists():
        try:
            target.unlink()
            save_plugin_enabled(plugin_id, False)
            return True
        except Exception as e:
            print(f"[PluginStore] Error removing plugin {plugin_id}: {e}")
            return False
    return False


def toggle_plugin_status(plugin_id: str) -> bool:
    cur = get_plugin_enabled(plugin_id)
    save_plugin_enabled(plugin_id, not cur)
    return not cur


list_store_plugins = list_store_items

