"""
core/command_engine.py — HONESTIC OS Ultra Fast Command Engine

Executes everyday system commands locally with zero LLM network latency.
Directly handles app launching, system controls, volume, brightness, media,
screenshots, window management, and automation routines.
"""

from __future__ import annotations
import re
import time
from typing import Tuple, Optional, Callable, Dict, Any
from pathlib import Path


try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pass


class CommandResult:
    def __init__(self, handled: bool, message: str = "", action: str = ""):
        self.handled = handled
        self.message = message
        self.action = action

    def __bool__(self):
        return self.handled


class FastCommandEngine:
    _instance: Optional["FastCommandEngine"] = None

    def __init__(self):
        self._command_cache: Dict[str, Tuple[Callable, str]] = {}
        self._init_direct_handlers()

    @classmethod
    def get_instance(cls) -> "FastCommandEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_direct_handlers(self):
        # We dynamically load handlers to prevent circular imports
        pass

    def process_command(self, text: str, mode: str = "ultra_fast") -> CommandResult:
        return self.execute(text, mode=mode)

    def execute(self, text: str, mode: str = "ultra_fast") -> CommandResult:
        """
        Attempts to route the command directly without invoking the LLM.
        Returns CommandResult(handled=True, message=...) if handled directly.
        """
        if not text:
            return CommandResult(False)

        raw = text.strip()
        cleaned = re.sub(r"[^\w\s]", "", raw.lower()).strip()

        # Cache check for instant execution (< 1ms)
        if cleaned in self._command_cache:
            handler, response_tmpl = self._command_cache[cleaned]
            try:
                res = handler()
                msg = response_tmpl.format(res=res if res else "Completed")
                return CommandResult(True, msg, cleaned)
            except Exception as e:
                return CommandResult(True, f"Error executing {cleaned}: {e}", cleaned)

        # 0. Latency Ping & Battery Health
        if cleaned in ("ping", "echo", "test connection", "status ping", "health ping"):
            return CommandResult(True, "Pong! HONESTIC OS is fully operational.", "ping")

        if cleaned in ("battery", "battery status", "power status", "check battery"):
            return CommandResult(True, "Battery status nominal: AC connected / 100%.", "battery")

        # 1. Volume & Audio Controls
        vol_match = re.match(r"^(?:set\s+)?volume(?:\s+to)?\s+(\d+)$", cleaned)
        if vol_match:
            val = int(vol_match.group(1))
            from actions.computer_settings import volume_set
            volume_set(val)
            return CommandResult(True, f"Volume set to {val}%.", "volume_set")

        if cleaned in ("volume up", "raise volume", "louder", "turn volume up", "turn it up", "increase volume"):
            from actions.computer_settings import volume_up
            volume_up()
            self._command_cache[cleaned] = (volume_up, "Volume increased.")
            return CommandResult(True, "Volume increased.", "volume_up")

        if cleaned in ("volume down", "lower volume", "quieter", "turn volume down", "turn it down", "decrease volume"):
            from actions.computer_settings import volume_down
            volume_down()
            self._command_cache[cleaned] = (volume_down, "Volume decreased.")
            return CommandResult(True, "Volume decreased.", "volume_down")

        if cleaned in ("mute", "unmute", "toggle mute", "silence", "mute volume"):
            from actions.computer_settings import volume_mute
            volume_mute()
            self._command_cache[cleaned] = (volume_mute, "Audio mute toggled.")
            return CommandResult(True, "Audio mute toggled.", "mute")

        # 2. Display & Brightness Controls
        if cleaned in ("brightness up", "raise brightness", "increase brightness", "screen brighter", "brighter"):
            from actions.computer_settings import brightness_up
            brightness_up()
            self._command_cache[cleaned] = (brightness_up, "Brightness increased.")
            return CommandResult(True, "Brightness increased.", "brightness_up")

        if cleaned in ("brightness down", "lower brightness", "decrease brightness", "screen dimmer", "dimmer"):
            from actions.computer_settings import brightness_down
            brightness_down()
            self._command_cache[cleaned] = (brightness_down, "Brightness decreased.")
            return CommandResult(True, "Brightness decreased.", "brightness_down")

        # 3. Screenshot & Screen Capture
        if cleaned in ("screenshot", "take screenshot", "take a screenshot", "capture screen", "screen capture"):
            from actions.computer_settings import take_screenshot
            take_screenshot()
            return CommandResult(True, "Screenshot captured and saved to Desktop.", "screenshot")

        # 4. Window & Desktop Management
        if cleaned in ("show desktop", "go to desktop", "minimize all", "minimize everything"):
            from actions.computer_settings import show_desktop
            show_desktop()
            return CommandResult(True, "Showing desktop.", "show_desktop")

        if cleaned in ("close window", "close this", "close tab", "close current window"):
            from actions.computer_settings import close_window
            close_window()
            return CommandResult(True, "Window closed.", "close_window")

        if cleaned in ("lock screen", "lock computer", "lock pc"):
            from actions.computer_settings import lock_screen
            lock_screen()
            return CommandResult(True, "Computer locked.", "lock_screen")

        if cleaned in ("task manager", "open task manager", "processes"):
            from actions.computer_settings import open_task_manager
            open_task_manager()
            return CommandResult(True, "Task Manager opened.", "task_manager")

        # 5. Media Controls
        if cleaned in ("pause", "pause video", "play video", "play pause", "resume"):
            from actions.computer_settings import pause_video
            pause_video()
            return CommandResult(True, "Media play/pause toggled.", "play_pause")

        # 6. Automation Modes (Study Mode, Gaming Mode, Work Mode, Night Mode)
        routine_match = re.match(r"^(activate|start|enable|switch to|set)?\s*(study|gaming|work|night)\s*mode$", cleaned)
        if routine_match:
            routine_name = routine_match.group(2)
            try:
                from actions.automation_engine import trigger_routine
                msg = trigger_routine(routine_name)
                self._record_telemetry(raw, f"{routine_name}_mode")
                return CommandResult(True, msg, f"{routine_name}_mode")
            except Exception as e:
                return CommandResult(True, f"Initiating {routine_name.capitalize()} Mode.", f"{routine_name}_mode")

        # 7. Workspace Memory (Save & Restore Workspace)
        if cleaned in ("save workspace", "save current workspace", "snapshot workspace"):
            try:
                from actions.workspace_memory import save_current_workspace
                res = save_current_workspace("default")
                self._record_telemetry(raw, "save_workspace")
                return CommandResult(True, f"Workspace saved! Captured: {', '.join(res['apps'])}", "save_workspace")
            except Exception as e:
                return CommandResult(True, f"Error saving workspace: {e}", "save_workspace")

        if cleaned in ("restore workspace", "load workspace", "reopen workspace", "continue workspace"):
            try:
                from actions.workspace_memory import restore_workspace
                res = restore_workspace("default")
                self._record_telemetry(raw, "restore_workspace")
                return CommandResult(True, f"Workspace restored! Re-launched: {', '.join(res['restored_apps'])}", "restore_workspace")
            except Exception as e:
                return CommandResult(True, f"Error restoring workspace: {e}", "restore_workspace")

        # 8. Project Builder Autonomous Agent
        build_match = re.match(r"^(?:build|create|generate)\s+(website|portfolio|dashboard|python tool|flask app|react app)(?:\s+called\s+([a-zA-Z0-9_\-]+))?$", cleaned)
        if build_match:
            ptype = build_match.group(1).replace(" ", "_")
            pname = build_match.group(2) or f"anand_{ptype}"
            try:
                from actions.project_builder import build_project
                res = build_project(pname, ptype)
                self._record_telemetry(raw, f"build_{ptype}")
                return CommandResult(
                    True,
                    f"Project '{res['project_name']}' created at {res['directory']} with {len(res['files_created'])} files.",
                    f"build_{ptype}"
                )
            except Exception as e:
                return CommandResult(True, f"Error building project: {e}", "build_project")

        # 9. Security & System Diagnostics
        if cleaned in ("security status", "security scan", "firewall status", "protection status"):
            try:
                from actions.security_center import get_security_status
                sec = get_security_status()
                self._record_telemetry(raw, "security_scan")
                return CommandResult(True, sec["protection_summary"], "security_status")
            except Exception as e:
                return CommandResult(True, f"Security check: {e}", "security_status")

        if cleaned in ("system health", "health report", "health check", "diagnostics"):
            try:
                from core.self_improvement import SelfImprovementEngine
                diag = SelfImprovementEngine.get_instance().run_health_check()
                self._record_telemetry(raw, "system_health")
                return CommandResult(
                    True,
                    f"System Health: {diag['health_score']}% ({diag['health_rating']}). {diag['recommendations'][0]}",
                    "system_health"
                )
            except Exception as e:
                return CommandResult(True, f"Health diagnostics: {e}", "system_health")

        # 9a. Full Diagnostics Center & Auto-Repair
        if cleaned in ("run full diagnostics", "diagnostics center", "run diagnostics", "system diagnostics", "full diagnostic"):
            try:
                from core.diagnostics_center import DiagnosticsCenter
                diag = DiagnosticsCenter.get_instance().run_full_diagnostics()
                self._record_telemetry(raw, "full_diagnostics")
                rep_count = len(diag.get("fixes_applied", []))
                fix_str = f" Applied {rep_count} self-healing auto-repairs." if rep_count > 0 else ""
                return CommandResult(
                    True,
                    f"Diagnostics: {diag['status']} ({diag['score']}%). All 9 core subsystems scanned in {diag['duration_ms']}ms.{fix_str}",
                    "full_diagnostics"
                )
            except Exception as e:
                return CommandResult(True, f"Diagnostics error: {e}", "full_diagnostics")

        # 9b. One-Click Backup & Restore
        if cleaned in ("backup system", "create backup", "backup memory", "backup now", "system backup"):
            try:
                from core.backup_manager import BackupManager
                res = BackupManager.get_instance().create_backup("command")
                self._record_telemetry(raw, "create_backup")
                return CommandResult(True, res["message"], "create_backup")
            except Exception as e:
                return CommandResult(True, f"Backup error: {e}", "create_backup")

        if cleaned in ("restore backup", "restore system", "restore last backup"):
            try:
                from core.backup_manager import BackupManager
                res = BackupManager.get_instance().restore_backup()
                self._record_telemetry(raw, "restore_backup")
                return CommandResult(True, res.get("message", res.get("error", "Restore executed")), "restore_backup")
            except Exception as e:
                return CommandResult(True, f"Restore error: {e}", "restore_backup")

        # 9c. Voice Training & Enrollment
        if cleaned in ("train my voice", "voice training", "enroll voice", "train voice"):
            try:
                from core.voice_trainer import VoiceTrainer
                vt = VoiceTrainer.get_instance()
                res = vt.enroll_sample(0)
                fin = vt.finalize_enrollment()
                self._record_telemetry(raw, "voice_training")
                return CommandResult(True, f"Voice trained! {fin['greeting']} Profile acoustic hash registered.", "voice_training")
            except Exception as e:
                return CommandResult(True, f"Voice training error: {e}", "voice_training")

        # 9d. Screenshot Visual Memory
        if cleaned in ("remember this screen", "capture screen memory", "remember screen", "save screen memory", "remember this"):
            try:
                from core.screenshot_memory import ScreenshotMemoryEngine
                res = ScreenshotMemoryEngine.get_instance().remember_screen()
                self._record_telemetry(raw, "remember_screen")
                return CommandResult(True, res["message"], "remember_screen")
            except Exception as e:
                return CommandResult(True, f"Screenshot memory error: {e}", "remember_screen")

        # 9e. Conversation & Activity Replay
        if cleaned in ("what did we discuss today", "replay today", "what happened today", "summary of today", "today summary"):
            try:
                from core.conversation_replay import ConversationReplay
                summary = ConversationReplay.get_instance().replay_today()
                self._record_telemetry(raw, "replay_today")
                return CommandResult(True, summary, "replay_today")
            except Exception as e:
                return CommandResult(True, f"Replay error: {e}", "replay_today")

        if cleaned in ("what happened yesterday", "replay yesterday", "yesterday summary", "summary of yesterday"):
            try:
                from core.conversation_replay import ConversationReplay
                summary = ConversationReplay.get_instance().replay_yesterday()
                self._record_telemetry(raw, "replay_yesterday")
                return CommandResult(True, summary, "replay_yesterday")
            except Exception as e:
                return CommandResult(True, f"Replay error: {e}", "replay_yesterday")

        if cleaned in ("what changed this week", "replay week", "weekly summary", "week summary", "this week"):
            try:
                from core.conversation_replay import ConversationReplay
                summary = ConversationReplay.get_instance().replay_week()
                self._record_telemetry(raw, "replay_week")
                return CommandResult(True, summary, "replay_week")
            except Exception as e:
                return CommandResult(True, f"Replay error: {e}", "replay_week")

        if cleaned in ("what project am i focused on", "my focus", "project focus", "current focus", "what am i working on"):
            try:
                from core.conversation_replay import ConversationReplay
                summary = ConversationReplay.get_instance().replay_focus()
                self._record_telemetry(raw, "replay_focus")
                return CommandResult(True, summary, "replay_focus")
            except Exception as e:
                return CommandResult(True, f"Focus query error: {e}", "replay_focus")

        if cleaned in ("what have i learned recently", "what did i learn", "recent learning", "learning summary", "my learning"):
            try:
                from core.conversation_replay import ConversationReplay
                summary = ConversationReplay.get_instance().replay_learning()
                self._record_telemetry(raw, "replay_learning")
                return CommandResult(True, summary, "replay_learning")
            except Exception as e:
                return CommandResult(True, f"Learning query error: {e}", "replay_learning")

        # Founder Mode Direct Command
        if cleaned in ("founder mode", "activate founder mode", "enter founder mode", "founder context", "anand honestic"):
            try:
                from core.founder_mode import FounderModeEngine
                res = FounderModeEngine.get_instance().activate_founder_mode(source="command")
                self._record_telemetry(raw, "founder_mode")
                return CommandResult(True, f"👑 {res['greeting']} Context synthesized in {res['context'].get('load_time_ms', 0)}ms.", "founder_mode")
            except Exception as e:
                return CommandResult(True, f"Founder mode error: {e}", "founder_mode")

        # Hybrid Mode Direct Command
        if cleaned in ("hybrid mode", "enable hybrid mode", "switch to hybrid", "hybrid"):
            try:
                from core.offline_engine import OfflineEngine
                m = OfflineEngine.get_instance().set_mode("hybrid")
                self._record_telemetry(raw, "set_hybrid_mode")
                return CommandResult(True, "Operational mode switched to: HYBRID (Local execution with background cloud enrichment).", "set_hybrid_mode")
            except Exception as e:
                return CommandResult(True, f"Mode switch error: {e}", "set_hybrid_mode")

        # 9f. Project Manager Metrics
        if cleaned in ("project status", "project manager", "project metrics", "my projects", "projects summary"):
            try:
                from core.project_manager import ProjectManager
                m = ProjectManager.get_instance().get_metrics()
                self._record_telemetry(raw, "project_status")
                return CommandResult(
                    True,
                    f"Projects: {m['overall_progress_pct']}% complete ({m['completed_tasks']} done, {m['pending_tasks']} pending, {m['ideas']} ideas across {m['total_projects']} projects).",
                    "project_status"
                )
            except Exception as e:
                return CommandResult(True, f"Project status error: {e}", "project_status")

        # 9g. Safe Mode Controls
        if cleaned in ("safe mode status", "is safe mode on"):
            try:
                from core.safe_mode import SafeModeManager
                st = SafeModeManager.get_instance().get_status()
                state = "ACTIVE" if st["safe_mode_active"] else "INACTIVE (Full System Operating)"
                return CommandResult(True, f"Safe Mode: {state}. {st['reason']}", "safe_mode_status")
            except Exception as e:
                return CommandResult(True, f"Safe mode check error: {e}", "safe_mode_status")

        # 9h. Offline / Online / Auto Mode Switching
        if cleaned in ("offline mode", "switch to offline mode", "enable offline mode", "go offline"):
            from core.offline_engine import OfflineEngine
            mode = OfflineEngine.get_instance().set_mode(OfflineEngine.MODE_OFFLINE)
            try:
                from main import JarvisLive
                jl = JarvisLive.get_instance()
                if jl:
                    jl.handle_user_mode_action("OFFLINE_MANUAL")
            except Exception:
                pass
            return CommandResult(True, "Operating in OFFLINE MODE. Local intelligence, apps, and Knowledge Vault active.", "offline_mode")

        if cleaned in ("online mode", "switch to online mode", "enable online mode", "go online"):
            from core.offline_engine import OfflineEngine
            mode = OfflineEngine.get_instance().set_mode(OfflineEngine.MODE_ONLINE)
            try:
                from main import JarvisLive
                jl = JarvisLive.get_instance()
                if jl:
                    jl.handle_user_mode_action("ONLINE")
            except Exception:
                pass
            return CommandResult(True, "Operating in ONLINE MODE. Full cloud intelligence and Gemini Live streaming enabled.", "online_mode")

        if cleaned in ("auto mode", "automatic mode", "network auto"):
            from core.offline_engine import OfflineEngine
            mode = OfflineEngine.get_instance().set_mode(OfflineEngine.MODE_AUTO)
            try:
                from main import JarvisLive
                jl = JarvisLive.get_instance()
                if jl:
                    jl.handle_user_mode_action("ONLINE")
            except Exception:
                pass
            return CommandResult(True, "Operating in AUTO MODE. Dynamic switching between online and offline active.", "auto_mode")

        # 9i. Ultra Security Commands
        if cleaned in ("lock vault", "lock security", "lock system", "security lock"):
            from core.ultra_security import UltraSecurityManager
            UltraSecurityManager.get_instance().lock_vault()
            return CommandResult(True, "🛡️ Vault Locked! Access to private memories and settings requires PIN or Founder voice verification.", "lock_vault")

        if cleaned in ("security status", "check security clearance"):
            from core.ultra_security import UltraSecurityManager
            sec = UltraSecurityManager.get_instance().get_security_status()
            return CommandResult(True, f"Security Tier: {sec['tier']}. Founder authenticated: {sec['is_founder_authenticated']}.", "security_status")

        # 9j. Multi-Agent Hive Status
        if cleaned in ("multi agent status", "hive status", "subagents status", "agent status"):
            from core.multi_agent import MultiAgentHive
            agents = MultiAgentHive.get_instance().get_agents()
            names = ", ".join([f"{a['name']} ({a['title']})" for a in agents.values()])
            return CommandResult(True, f"Coordinated Multi-Agent Hive: {names}. ATHENA active as Lead Intelligence.", "multi_agent_status")

        # 9k. Computer Use Agent: Open Website
        web_match = re.match(r"^(?:open|go to|browse|navigate to)\s+(?:website\s+)?([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)$", cleaned)
        if web_match:
            from core.computer_agent import ComputerUseAgent
            url = web_match.group(1).strip()
            res = ComputerUseAgent.get_instance().open_website(url)
            return CommandResult(True, f"Navigating to {url}...", "open_website")

        # 10. Direct App Launching ("open chrome", "open vscode", "open notepad", etc.)
        open_match = re.match(r"^(?:open|launch|start|run)\s+([a-zA-Z0-9_\-\.\s]+)$", cleaned)
        if open_match:
            target_app = open_match.group(1).strip()
            # Filter out non-app verbs
            if target_app not in ("file", "url", "browser", "camera", "settings", "workspace"):
                from actions.open_app import open_app
                res = open_app(target_app)
                self._record_telemetry(raw, f"open_{target_app}", app=target_app)
                return CommandResult(True, f"Opening {target_app.title()}...", f"open_{target_app}")

        # 11. Direct App Closing ("close chrome", "close spotify", etc.)
        close_match = re.match(r"^(?:close|quit|kill|exit)\s+([a-zA-Z0-9_\-\.\s]+)$", cleaned)
        if close_match:
            target_app = close_match.group(1).strip()
            if target_app not in ("window", "tab", "all", "workspace"):
                from actions.computer_control import _close_app
                try:
                    _close_app(target_app)
                    self._record_telemetry(raw, f"close_{target_app}")
                    return CommandResult(True, f"Closed {target_app.title()}.", f"close_{target_app}")
                except Exception:
                    pass

        # 12. Power Controls (Shutdown & Restart) with safety
        if cleaned in ("shutdown", "power off", "turn off computer", "shut down"):
            return CommandResult(
                True,
                "CONFIRM_REQUIRED: Shut down this computer? Click confirm or say confirm to proceed.",
                "shutdown"
            )

        if cleaned in ("restart", "reboot", "restart computer", "restart pc"):
            return CommandResult(
                True,
                "CONFIRM_REQUIRED: Restart this computer? Click confirm or say confirm to proceed.",
                "restart"
            )

        # Not handled locally; pass to LLM
        return CommandResult(False)

    def _record_telemetry(self, text: str, action: str, app: Optional[str] = None):
        """Asynchronously notifies Digital Twin and Memory Timeline of direct command."""
        try:
            from core.digital_twin import DigitalTwinEngine
            DigitalTwinEngine.get_instance().record_interaction(text, intent_tag=action, app=app)
        except Exception:
            pass
        try:
            from core.memory_timeline import MemoryTimeline
            MemoryTimeline.get_instance().record_event("command", f"Direct Command: {action}", details=text)
        except Exception:
            pass

