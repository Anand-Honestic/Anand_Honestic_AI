"""
core/context_engine.py — HONESTIC OS Context Awareness & Screen Intelligence

Gives ATHENA real-time awareness of the user's computer:
- Current Foreground Application
- Current Window Title & File
- Current Project & Workspace
- Current Website / Browser Tab
- Activity Classification (Coding, Research, Documentation, Admin)
"""

from __future__ import annotations
import os
import re
import time
import platform
import ctypes
from typing import Dict, Any, Optional
from pathlib import Path

_OS = platform.system()

try:
    import psutil
except ImportError:
    psutil = None


class ContextEngine:
    _instance: Optional["ContextEngine"] = None

    def __init__(self):
        self._last_context: Dict[str, Any] = {}
        self._last_query_time: float = 0.0
        self._cache_ttl_sec: float = 1.2

    @classmethod
    def get_instance(cls) -> "ContextEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_active_context(self) -> Dict[str, Any]:
        """Inspects foreground window and process to establish real-time context with debounce caching."""
        now = time.time()
        if self._last_context and (now - self._last_query_time) < self._cache_ttl_sec:
            return self._last_context

        context = {
            "app_name": "HONESTIC OS",
            "process_name": "python.exe",
            "window_title": "HONESTIC OS Desktop",
            "clean_title": "HONESTIC OS",
            "activity": "General Operations",
            "project": "HONESTIC OS",
            "file": "",
            "url_or_domain": "",
            "is_coding": False,
            "is_browser": False,
            "is_terminal": False,
        }

        if _OS == "Windows":
            try:
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                if hwnd:
                    length = user32.GetWindowTextLengthW(hwnd)
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    raw_title = (buf.value or "").strip()

                    # Strip dirty status dot in editors (e.g. "● main.py")
                    if raw_title.startswith("● "):
                        raw_title = raw_title[2:].strip()

                    # Get process name
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    pname = ""
                    if psutil and pid.value:
                        try:
                            proc = psutil.Process(pid.value)
                            pname = proc.name().lower()
                        except Exception:
                            pass

                    context["window_title"] = raw_title or "Active Window"
                    context["clean_title"] = raw_title
                    context["process_name"] = pname

                    # Map process to friendly application name & clean titles
                    if "code" in pname:
                        context["app_name"] = "Visual Studio Code"
                        context["is_coding"] = True
                        context["activity"] = "Coding & Software Engineering"
                        clean = re.sub(r"\s*-\s*Visual Studio Code.*$", "", raw_title).strip()
                        context["clean_title"] = clean
                        parts = clean.split(" - ")
                        if len(parts) >= 2:
                            context["file"] = parts[0].strip()
                            context["project"] = parts[1].strip()
                        elif len(parts) == 1:
                            context["file"] = parts[0].strip()

                    elif any(b in pname for b in ("chrome", "msedge", "firefox", "brave", "opera")):
                        browser_names = {
                            "chrome": "Google Chrome",
                            "msedge": "Microsoft Edge",
                            "firefox": "Mozilla Firefox",
                            "brave": "Brave Browser",
                            "opera": "Opera",
                        }
                        matched_b = next((k for k in browser_names if k in pname), "Browser")
                        context["app_name"] = browser_names.get(matched_b, "Web Browser")
                        context["is_browser"] = True
                        context["activity"] = "Web Research & Browsing"

                        # Clean browser title
                        clean = re.sub(r"\s*-\s*(Google Chrome|Microsoft Edge|Mozilla Firefox|Brave).*$", "", raw_title).strip()
                        context["clean_title"] = clean

                        # Detect popular domains or search queries
                        lower_title = raw_title.lower()
                        known_domains = [
                            "github.com", "stackoverflow.com", "youtube.com", "google.com",
                            "reddit.com", "medium.com", "docs.python.org", "wikipedia.org",
                            "chatgpt.com", "claude.ai", "gemini.google.com", "twitter.com", "x.com"
                        ]
                        for domain in known_domains:
                            if domain in lower_title or domain.split(".")[0] in lower_title:
                                context["url_or_domain"] = domain
                                break

                        if "youtube" in lower_title:
                            context["activity"] = "Video Research & Streaming"
                        elif "github" in lower_title or "stack overflow" in lower_title:
                            context["activity"] = "Technical Research & Documentation"

                    elif pname in ("cmd.exe", "powershell.exe", "windowsterminal.exe"):
                        context["app_name"] = "Windows Terminal"
                        context["is_terminal"] = True
                        context["activity"] = "System Administration & CLI"
                        context["clean_title"] = re.sub(r"^Administrator:\s*", "", raw_title).strip()

                    elif "notepad" in pname:
                        context["app_name"] = "Notepad"
                        context["activity"] = "Notes & Text Editing"
                        context["clean_title"] = re.sub(r"\s*-\s*Notepad.*$", "", raw_title).strip()

                    elif "explorer" in pname:
                        context["app_name"] = "File Explorer"
                        context["activity"] = "File Management"

                    elif "spotify" in pname:
                        context["app_name"] = "Spotify"
                        context["activity"] = "Music Playback"

                    elif "slack" in pname or "discord" in pname or "telegram" in pname:
                        context["app_name"] = pname.replace(".exe", "").capitalize()
                        context["activity"] = "Team Communication & Collaboration"

                    else:
                        clean_name = pname.replace(".exe", "").capitalize() if pname else "System Window"
                        context["app_name"] = clean_name

            except Exception as e:
                pass

        self._last_context = context
        self._last_query_time = now
        return context

    def get_prompt_context(self) -> str:
        """Compact string injected into Gemini Live session for real-time situational awareness."""
        ctx = self.get_active_context()
        lines = [
            "[REAL-TIME SYSTEM SITUATION AWARENESS]",
            f"- Foreground App: {ctx['app_name']}",
            f"- Current Window: {ctx['window_title'][:120]}",
            f"- Current Activity: {ctx['activity']}",
        ]
        if ctx.get("file"):
            lines.append(f"- Active Document/File: {ctx['file']}")
        if ctx.get("project"):
            lines.append(f"- Active Project: {ctx['project']}")
        if ctx.get("url_or_domain"):
            lines.append(f"- Active Domain: {ctx['url_or_domain']}")
        lines.append("- Use this context to answer questions about the current task without forcing the user to re-explain.")
        lines.append("")
        return "\n".join(lines)
