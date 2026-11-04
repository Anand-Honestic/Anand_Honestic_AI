"""
core/settings_hub.py — HONESTIC OS Settings Center & Setup Wizard

Single Settings Hub with 10 sections:
1. Profile
2. AI Personality
3. Voice
4. Memory 2.0
5. Themes
6. Avatar
7. Performance
8. Plugins
9. Automation
10. Dashboard

And 6-Step Setup Wizard for First Run Experience.
"""

from __future__ import annotations
import json
import webbrowser
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QBrush
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QStackedWidget, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QCheckBox, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QGridLayout, QSlider, QTextEdit
)

from core.os_identity import (
    PROJECT_NAME, OWNER_NAME, OWNER_BRANDING, OWNER_TITLE,
    DEFAULT_AI_NAME, DEFAULT_VOICE, PERSONALITIES, THEMES, PERFORMANCE_MODES, AVATAR_MODES,
    VOICE_CATALOG, VOICE_PROFILES, ATHENA_DEFAULT_PROFILE
)
from core.personality_manager import PersonalityManager
from core.voice_manager import VoiceManager
from core.theme_manager import ThemeManager
from core.profile_manager import ProfileManager
from core.plugin_store import list_store_items, install_plugin, uninstall_plugin, toggle_plugin_status
from memory.config_manager import (
    load_api_keys, save_assistant_config, save_voice, get_voice, get_voice_name,
    save_voice_profile, get_voice_profile,
    save_voice_custom_params, get_voice_custom_params,
    save_performance_mode, get_performance_mode,
    save_theme_name, get_theme_name,
    save_avatar_mode, get_avatar_mode,
    save_ai_personality, get_ai_personality,
    save_first_run_completed, get_first_run_completed,
    get_assistant_name, get_user_name
)
from memory.memory_manager import load_memory, save_memory, search_memory



# ─────────────────────────────────────────────────────────────────────────────
#  Setup Wizard (First Run Experience)
# ─────────────────────────────────────────────────────────────────────────────

class SetupWizardDialog(QDialog):
    completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{PROJECT_NAME} — Setup Wizard")
        self.setFixedSize(680, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._theme_mgr = ThemeManager.get_instance()
        self._current_step = 0
        self._build_ui()
        self._apply_style()

    def _apply_style(self):
        td = self._theme_mgr.get_theme_data()
        pri = td["accent"]
        bg = td["bg"]
        border = td["border"]
        text = td["text"]

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel {{
                color: {text};
                background: transparent;
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(0, 212, 255, 0.15);
                border-color: {pri};
                color: #ffffff;
            }}
            QLineEdit {{
                background: rgba(4, 14, 26, 0.85);
                color: #ffffff;
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {pri};
            }}
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        logo_v = QVBoxLayout()
        title = QLabel(f"◈ {PROJECT_NAME} SETUP WIZARD")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        logo_v.addWidget(title)

        subtitle = QLabel(f"Personal AI Operating System for {OWNER_NAME}")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        logo_v.addWidget(subtitle)
        hdr.addLayout(logo_v)
        hdr.addStretch()

        self._step_badge = QLabel("STEP 1 OF 6")
        self._step_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._step_badge.setStyleSheet(
            "background: rgba(0, 212, 255, 0.15); color: #00d4ff; padding: 4px 10px; border-radius: 6px;"
        )
        hdr.addWidget(self._step_badge)
        root.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.1); margin: 4px 0;")
        root.addWidget(sep)

        # Stack of 6 steps
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_step1_owner())
        self._stack.addWidget(self._create_step2_ai())
        self._stack.addWidget(self._create_step3_voice())
        self._stack.addWidget(self._create_step4_theme())
        self._stack.addWidget(self._create_step5_avatar())
        self._stack.addWidget(self._create_step6_mode())
        root.addWidget(self._stack, stretch=1)

        # Bottom navigation
        nav = QHBoxLayout()
        self._back_btn = QPushButton("◀ Back")
        self._back_btn.clicked.connect(self._prev_step)
        self._back_btn.setEnabled(False)
        nav.addWidget(self._back_btn)

        nav.addStretch()

        self._next_btn = QPushButton("Next Step ▶")
        self._next_btn.clicked.connect(self._next_step)
        self._next_btn.setStyleSheet("background: #007a99; color: #fff; font-weight: bold;")
        nav.addWidget(self._next_btn)

        root.addLayout(nav)

    # ── Step 1: Owner Name ──
    def _create_step1_owner(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("1. Owner Configuration")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        desc = QLabel("Confirm the primary owner identity of this AI Operating System.")
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        lay.addWidget(desc)

        lay.addSpacing(10)
        lay.addWidget(QLabel("Owner Name:"))
        self._owner_input = QLineEdit(OWNER_NAME)
        lay.addWidget(self._owner_input)

        badge_box = QFrame()
        badge_box.setStyleSheet("background: rgba(255, 255, 255, 0.04); border-radius: 8px; padding: 12px;")
        b_lay = QVBoxLayout(badge_box)
        b_lbl = QLabel(f"{OWNER_BRANDING} — {OWNER_TITLE}")
        b_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        b_lbl.setStyleSheet("color: #00ff88;")
        b_lay.addWidget(b_lbl)
        b_sub = QLabel("Administrator & Operating System Owner Privileges Activated.")
        b_sub.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        b_lay.addWidget(b_sub)
        lay.addWidget(badge_box)

        lay.addStretch()
        return w

    # ── Step 2: Choose AI Name ──
    def _create_step2_ai(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        lbl = QLabel("2. Choose AI Assistant Profile")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        self._ai_group = QButtonGroup(self)
        self._ai_radios = {}

        for key, p in PERSONALITIES.items():
            rb = QRadioButton(f"{p['name']} — {p['title']}")
            rb.setStyleSheet("font-size: 12px; padding: 4px;")
            if key == "ATHENA":
                rb.setChecked(True)
            self._ai_group.addButton(rb)
            self._ai_radios[key] = rb
            lay.addWidget(rb)

            pdesc = QLabel(f"   {p['description']}")
            pdesc.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; margin-bottom: 6px;")
            lay.addWidget(pdesc)

        lay.addStretch()
        return w

    # ── Step 3: Choose Voice ──
    def _create_step3_voice(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        lbl = QLabel("3. Select Voice Profile")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        voice_row = QHBoxLayout()
        self._voice_combo = QComboBox()
        self._voice_combo.addItems([
            "Athena (Female - Default)",
            "Nova (Female - Modern Companion)",
            "Friday (Female - Tactical Assistant)",
            "Aria (Female - Melodic)",
            "Jarvis (Male - British Resonance)",
            "Orion (Male - Commanding)",
            "Titan (Male - Deep Acoustic)",
            "Custom (Custom Slot)"
        ])
        self._voice_combo.setStyleSheet("background: rgba(4, 14, 26, 0.85); padding: 8px; border-radius: 6px;")
        voice_row.addWidget(self._voice_combo, stretch=1)

        prev_btn = QPushButton("▶ Preview Voice")
        prev_btn.clicked.connect(self._preview_selected_voice)
        voice_row.addWidget(prev_btn)
        lay.addLayout(voice_row)

        desc = QLabel("Voices switch smoothly without requiring an application restart.")
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        lay.addWidget(desc)

        lay.addStretch()
        return w

    def _preview_selected_voice(self):
        text = self._voice_combo.currentText().split()[0]
        VoiceManager.get_instance().preview_voice(text)

    # ── Step 4: Choose Theme ──
    def _create_step4_theme(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        lbl = QLabel("4. Choose Visual Theme")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        self._theme_combo = QComboBox()
        for k, th in THEMES.items():
            self._theme_combo.addItem(f"{th['name']} — {th['desc']}", k)
        self._theme_combo.setStyleSheet("background: rgba(4, 14, 26, 0.85); padding: 8px; border-radius: 6px;")
        lay.addWidget(self._theme_combo)

        info = QLabel("Features Glassmorphism, Windows 11 Fluent blur, and dynamic glowing accents.")
        info.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        lay.addWidget(info)

        lay.addStretch()
        return w

    # ── Step 5: Choose Avatar ──
    def _create_step5_avatar(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        lbl = QLabel("5. Choose Avatar Interface")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        self._avatar_combo = QComboBox()
        for k, desc in AVATAR_MODES.items():
            self._avatar_combo.addItem(desc, k)
        self._avatar_combo.setStyleSheet("background: rgba(4, 14, 26, 0.85); padding: 8px; border-radius: 6px;")
        lay.addWidget(self._avatar_combo)

        info = QLabel("Renders 60 FPS in real-time software without requiring heavy GPU frameworks.")
        info.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        lay.addWidget(info)

        lay.addStretch()
        return w

    # ── Step 6: Choose Performance Mode ──
    def _create_step6_mode(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        lbl = QLabel("6. Choose Performance Mode")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        self._mode_combo = QComboBox()
        for k, m in PERFORMANCE_MODES.items():
            self._mode_combo.addItem(f"{m['name']} — {m['desc']}", k)
        self._mode_combo.setCurrentIndex(2)  # Default: Ultra Fast Mode
        self._mode_combo.setStyleSheet("background: rgba(4, 14, 26, 0.85); padding: 8px; border-radius: 6px;")
        lay.addWidget(self._mode_combo)

        badge = QFrame()
        badge.setStyleSheet("background: rgba(0, 255, 136, 0.08); border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 8px; padding: 12px;")
        b_lay = QVBoxLayout(badge)
        rec = QLabel("⚡ Ultra Fast Mode Recommended")
        rec.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        rec.setStyleSheet("color: #00ff88;")
        b_lay.addWidget(rec)
        rec_desc = QLabel(
            "Executes direct commands (open apps, volume, screenshot, brightness, shutdown) "
            "instantly on device without waiting for LLM roundtrips."
        )
        rec_desc.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px;")
        b_lay.addWidget(rec_desc)
        lay.addWidget(badge)

        lay.addStretch()
        return w

    def _next_step(self):
        if self._current_step < 5:
            self._current_step += 1
            self._stack.setCurrentIndex(self._current_step)
            self._step_badge.setText(f"STEP {self._current_step + 1} OF 6")
            self._back_btn.setEnabled(True)
            if self._current_step == 5:
                self._next_btn.setText("Finish & Launch 🚀")
                self._next_btn.setStyleSheet("background: #00aa55; color: #fff; font-weight: bold;")
        else:
            self._save_wizard()

    def _prev_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._stack.setCurrentIndex(self._current_step)
            self._step_badge.setText(f"STEP {self._current_step + 1} OF 6")
            self._next_btn.setText("Next Step ▶")
            self._next_btn.setStyleSheet("background: #007a99; color: #fff; font-weight: bold;")
            if self._current_step == 0:
                self._back_btn.setEnabled(False)

    def _save_wizard(self):
        # 1. Owner & AI name
        owner = self._owner_input.text().strip() or OWNER_NAME
        selected_ai = "ATHENA"
        for k, rb in self._ai_radios.items():
            if rb.isChecked():
                selected_ai = k
                break
        ai_name = PERSONALITIES.get(selected_ai, {}).get("name", DEFAULT_AI_NAME)
        save_assistant_config(ai_name, owner)
        save_ai_personality(selected_ai)

        # 2. Voice
        vname = self._voice_combo.currentText().split()[0]
        save_voice(vname)
        VoiceManager.get_instance().set_voice(vname)

        # 3. Theme
        tkey = self._theme_combo.currentData()
        save_theme_name(tkey)
        ThemeManager.get_instance().set_theme(tkey)

        # 4. Avatar
        av_key = self._avatar_combo.currentData()
        save_avatar_mode(av_key)

        # 5. Performance mode
        pm_key = self._mode_combo.currentData()
        save_performance_mode(pm_key)

        # Mark completed
        save_first_run_completed(True)
        self.completed.emit()
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  Single Settings Hub (Unified Settings Center)
# ─────────────────────────────────────────────────────────────────────────────

class SettingsHubDialog(QDialog):
    settings_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{PROJECT_NAME} — Settings Center")
        self.resize(880, 620)
        self.setMinimumSize(800, 560)

        self._theme_mgr = ThemeManager.get_instance()
        self._voice_mgr = VoiceManager.get_instance()
        self._persona_mgr = PersonalityManager.get_instance()
        self._profile_mgr = ProfileManager.get_instance()

        self._build_ui()
        self._apply_style()

    def _apply_style(self):
        td = self._theme_mgr.get_theme_data()
        pri = td["accent"]
        bg = td["bg"]
        border = td["border"]
        border_b = td["border_b"]
        text = td["text"]
        text_dim = td["text_dim"]

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg};
                color: {text};
            }}
            QListWidget {{
                background: rgba(1, 10, 18, 0.85);
                border: 1px solid {border};
                border-radius: 8px;
                color: {text};
                padding: 6px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QListWidget::item:selected {{
                background: rgba(0, 212, 255, 0.18);
                color: {pri};
                font-weight: bold;
                border-left: 3px solid {pri};
            }}
            QListWidget::item:hover {{
                background: rgba(255, 255, 255, 0.05);
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.04);
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(0, 212, 255, 0.15);
                border-color: {pri};
                color: #ffffff;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background: rgba(4, 14, 26, 0.85);
                color: #ffffff;
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {pri};
            }}
            QFrame.card {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid {border};
                border-radius: 8px;
                padding: 14px;
            }}
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # Header with Owner Branding
        top_bar = QHBoxLayout()
        title_v = QVBoxLayout()
        title = QLabel(f"◈ {PROJECT_NAME} — SETTINGS CENTER")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_v.addWidget(title)

        owner_lbl = QLabel(f"{OWNER_BRANDING} ({OWNER_TITLE}) • Commercial AI Platform")
        owner_lbl.setFont(QFont("Segoe UI", 9))
        owner_lbl.setStyleSheet("color: #00ff88; font-weight: bold;")
        title_v.addWidget(owner_lbl)
        top_bar.addLayout(title_v)

        top_bar.addStretch()

        reset_btn = QPushButton("↺ Run Setup Wizard")
        reset_btn.clicked.connect(self._rerun_wizard)
        top_bar.addWidget(reset_btn)

        root.addLayout(top_bar)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.1); margin: 2px 0;")
        root.addWidget(sep)

        # Body: Left Sidebar (10 sections) + Right Content Stack
        body = QHBoxLayout()
        body.setSpacing(14)

        self._nav_list = QListWidget()
        self._nav_list.setFixedWidth(200)

        sections = [
            ("👑 Profile", 0),
            ("🧠 AI Personality", 1),
            ("🎙 Voice Center", 2),
            ("💾 Smart Memory 2.0", 3),
            ("🎨 Themes & Glass", 4),
            ("👤 Avatar System", 5),
            ("⚡ Performance", 6),
            ("🧩 Plugin Store", 7),
            ("🤖 Automation", 8),
            ("📊 Dashboard", 9),
        ]
        for label, idx in sections:
            item = QListWidgetItem(label)
            self._nav_list.addItem(item)
        self._nav_list.currentRowChanged.connect(self._on_section_changed)
        body.addWidget(self._nav_list)

        self._pages = QStackedWidget()
        self._pages.addWidget(self._build_page_profile())
        self._pages.addWidget(self._build_page_ai())
        self._pages.addWidget(self._build_page_voice())
        self._pages.addWidget(self._build_page_memory())
        self._pages.addWidget(self._build_page_themes())
        self._pages.addWidget(self._build_page_avatar())
        self._pages.addWidget(self._build_page_performance())
        self._pages.addWidget(self._build_page_plugins())
        self._pages.addWidget(self._build_page_automation())
        self._pages.addWidget(self._build_page_dashboard())
        body.addWidget(self._pages, stretch=1)

        root.addLayout(body, stretch=1)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)

        save_btn = QPushButton("Apply & Save All Settings")
        save_btn.setStyleSheet("background: #007a99; color: #fff; font-weight: bold; padding: 8px 18px;")
        save_btn.clicked.connect(self._save_all_settings)
        footer.addWidget(save_btn)

        root.addLayout(footer)

        self._nav_list.setCurrentRow(0)

    def _on_section_changed(self, idx: int):
        self._pages.setCurrentIndex(idx)

    def _rerun_wizard(self):
        w = SetupWizardDialog(self)
        if w.exec():
            self._load_current_values()
            self.settings_applied.emit()

    # ── Page 1: Profile ──
    def _build_page_profile(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("Profile Management")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        card = QFrame(); card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)
        c_lay.addWidget(QLabel("Active Profile Switcher:"))

        self._profile_combo = QComboBox()
        self._refresh_profiles_list()
        self._profile_combo.currentIndexChanged.connect(self._on_profile_switch)
        c_lay.addWidget(self._profile_combo)

        c_lay.addSpacing(6)
        c_lay.addWidget(QLabel("Owner Display Name:"))
        self._owner_name_edit = QLineEdit(get_user_name())
        c_lay.addWidget(self._owner_name_edit)

        lay.addWidget(card)

        # New profile creation
        n_card = QFrame(); n_card.setProperty("class", "card")
        n_lay = QVBoxLayout(n_card)
        n_lay.addWidget(QLabel("Create New User Profile:"))
        n_row = QHBoxLayout()
        self._new_prof_input = QLineEdit()
        self._new_prof_input.setPlaceholderText("e.g. Guest / Developer")
        n_row.addWidget(self._new_prof_input)
        create_btn = QPushButton("+ Create Profile")
        create_btn.clicked.connect(self._create_profile)
        n_row.addWidget(create_btn)
        n_lay.addLayout(n_row)
        lay.addWidget(n_card)

        lay.addStretch()
        return w

    def _refresh_profiles_list(self):
        self._profile_combo.clear()
        profs = self._profile_mgr.list_profiles()
        active = self._profile_mgr.get_active_profile_data().get("profile_name", OWNER_NAME)
        sel_idx = 0
        for i, p in enumerate(profs):
            pname = p.get("profile_name", "")
            dname = p.get("display_name", pname)
            self._profile_combo.addItem(dname, pname)
            if pname == active:
                sel_idx = i
        self._profile_combo.setCurrentIndex(sel_idx)

    def _on_profile_switch(self, idx: int):
        pname = self._profile_combo.currentData()
        if pname:
            self._profile_mgr.switch_profile(pname)
            self._owner_name_edit.setText(get_user_name())

    def _create_profile(self):
        name = self._new_prof_input.text().strip()
        if name:
            if self._profile_mgr.create_profile(name):
                self._new_prof_input.clear()
                self._refresh_profiles_list()

    # ── Page 2: AI Personality ──
    def _build_page_ai(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("AI Personality Profiles")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        card = QFrame(); card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)

        c_lay.addWidget(QLabel("Select Active AI Personality:"))
        self._ai_combo = QComboBox()
        for k, p in PERSONALITIES.items():
            self._ai_combo.addItem(f"{p['name']} — {p['title']}", k)
        cur_ai = get_ai_personality()
        for i in range(self._ai_combo.count()):
            if self._ai_combo.itemData(i) == cur_ai:
                self._ai_combo.setCurrentIndex(i)
                break
        c_lay.addWidget(self._ai_combo)

        c_lay.addSpacing(6)
        c_lay.addWidget(QLabel("Custom Assistant Name (Optional override):"))
        self._asst_name_edit = QLineEdit(get_assistant_name())
        c_lay.addWidget(self._asst_name_edit)

        c_lay.addSpacing(6)
        c_lay.addWidget(QLabel("Custom Persona Prompt Tuning:"))
        self._custom_prompt_edit = QTextEdit()
        self._custom_prompt_edit.setFixedHeight(90)
        self._custom_prompt_edit.setPlaceholderText("Enter custom instructions for how the AI should address Anand_Honestic...")
        c_lay.addWidget(self._custom_prompt_edit)

        lay.addWidget(card)
        lay.addStretch()
        return w

    # ── Page 3: Voice Center ──
    def _build_page_voice(self) -> QWidget:
        container = QWidget()
        c_root = QVBoxLayout(container)
        c_root.setContentsMargins(0, 0, 0, 0)
        c_root.setSpacing(10)

        # Scroll Area for comprehensive Voice Center
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 12, 12)
        lay.setSpacing(16)

        # 1. Header Banner & Status Telemetry
        hdr_card = QFrame(); hdr_card.setProperty("class", "card")
        hdr_lay = QVBoxLayout(hdr_card)
        hdr_lay.setSpacing(6)

        title_row = QHBoxLayout()
        v_title = QLabel("🎙 VOICE CENTER — ATHENA PRIME HUMAN VOICE EVOLUTION")
        v_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        v_title.setStyleSheet("color: #00d4ff; letter-spacing: 0.5px;")
        title_row.addWidget(v_title)
        title_row.addStretch()

        self._voice_mode_badge = QLabel("● ONLINE (Neural Fidelity)")
        self._voice_mode_badge.setStyleSheet(
            "background: rgba(0, 255, 136, 0.15); color: #00ff88; "
            "padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;"
        )
        title_row.addWidget(self._voice_mode_badge)
        hdr_lay.addLayout(title_row)

        desc = QLabel(
            "HONESTIC OS high-fidelity natural speech engine. ATHENA PRIME delivers flagship human assistant realism: "
            "warm timbre, calm confidence, mature delivery, natural breathing gaps, micro pauses, and conversation pacing."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px;")
        hdr_lay.addWidget(desc)

        # Quick Status Strip
        stat_row = QHBoxLayout()
        self._cur_voice_lbl = QLabel(f"Active Voice: <b>{self._voice_mgr.get_current_voice()}</b> (Flagship Human Assistant)")
        self._cur_voice_lbl.setStyleSheet("color: #ffffff; font-size: 11px;")
        stat_row.addWidget(self._cur_voice_lbl)

        self._cur_profile_lbl = QLabel(f"Active Profile: <b>{self._voice_mgr.get_current_profile()}</b>")
        self._cur_profile_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        stat_row.addWidget(self._cur_profile_lbl)

        stat_row.addStretch()
        instant_note = QLabel("⚡ Instant Switch • Zero Restart Required")
        instant_note.setStyleSheet("color: #00ff88; font-size: 10px; font-weight: 600;")
        stat_row.addWidget(instant_note)
        hdr_lay.addLayout(stat_row)

        lay.addWidget(hdr_card)

        # 2. Voice Selection Panel: Female & Male Voices
        select_card = QFrame(); select_card.setProperty("class", "card")
        sc_lay = QVBoxLayout(select_card)
        sc_lay.setSpacing(12)

        sel_hdr = QLabel("1. VOICE CHOOSER (HONESTIC OS Fleet)")
        sel_hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sel_hdr.setStyleSheet("color: #ffffff;")
        sc_lay.addWidget(sel_hdr)

        # Female Voices Section (ATHENA PRIME Flagship leading)
        f_lbl = QLabel("🌸 FEMALE VOICES (ATHENA Fleet — Premier Flagship & Companions)")
        f_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        f_lbl.setStyleSheet("color: #f472b6;")
        sc_lay.addWidget(f_lbl)

        self._voice_card_widgets: Dict[str, QFrame] = {}
        f_voices = self._voice_mgr.get_female_voices()
        f_grid = QGridLayout()
        f_grid.setSpacing(8)
        for i, vinfo in enumerate(f_voices):
            card = self._create_voice_card(vinfo)
            self._voice_card_widgets[vinfo["name"]] = card
            f_grid.addWidget(card, i // 2, i % 2)
        sc_lay.addLayout(f_grid)

        sc_lay.addSpacing(6)

        # Male Voices Section
        m_lbl = QLabel("⚔️ MALE VOICES (Tactical Fleet)")
        m_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        m_lbl.setStyleSheet("color: #60a5fa;")
        sc_lay.addWidget(m_lbl)

        m_voices = self._voice_mgr.get_male_voices()
        m_grid = QGridLayout()
        m_grid.setSpacing(8)
        for i, vinfo in enumerate(m_voices):
            card = self._create_voice_card(vinfo)
            self._voice_card_widgets[vinfo["name"]] = card
            m_grid.addWidget(card, i // 2, i % 2)
        sc_lay.addLayout(m_grid)

        lay.addWidget(select_card)

        # 3. Side-by-Side Voice Comparison Panel
        compare_card = QFrame(); compare_card.setProperty("class", "card")
        cmp_lay = QVBoxLayout(compare_card)
        cmp_lay.setSpacing(10)

        cmp_hdr = QLabel("2. SIDE-BY-SIDE VOICE COMPARISON (Acoustic Evaluation)")
        cmp_hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        cmp_hdr.setStyleSheet("color: #38bdf8;")
        cmp_lay.addWidget(cmp_hdr)

        cmp_sub = QLabel("Compare acoustic delivery, cadence, and warmth between voices side by side:")
        cmp_sub.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        cmp_lay.addWidget(cmp_sub)

        cmp_grid = QHBoxLayout()
        cmp_grid.setSpacing(8)

        compare_targets = [
            ("ATHENA OMEGA", "Athena Omega", "Flagship Digital Companion • Zenith Realism", "#38bdf8"),
            ("ATHENA PRIME", "Athena Prime", "Flagship Human Realism • Warm & Mature", "#00d4ff"),
            ("ATHENA", "Athena", "Intelligent & Confident Classical", "#f472b6"),
            ("NOVA", "Nova", "Modern Empathetic Clarity", "#a78bfa"),
            ("ARIA", "Aria", "Expressive Melodic Presence", "#34d399"),
        ]

        for title_str, v_id, desc_str, color_hex in compare_targets:
            box = QFrame()
            box.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid {color_hex}44;
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            b_lay = QVBoxLayout(box)
            b_lay.setContentsMargins(8, 8, 8, 8)
            b_lay.setSpacing(4)

            name_l = QLabel(f"<b>{title_str}</b>")
            name_l.setStyleSheet(f"color: {color_hex}; font-size: 11px;")
            b_lay.addWidget(name_l)

            desc_l = QLabel(desc_str)
            desc_l.setStyleSheet("color: #94a3b8; font-size: 9px;")
            desc_l.setWordWrap(True)
            b_lay.addWidget(desc_l)

            p_btn = QPushButton(f"▶ Preview {title_str}")
            p_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            p_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color_hex}22;
                    color: {color_hex};
                    border: 1px solid {color_hex};
                    border-radius: 5px;
                    padding: 5px;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    background: {color_hex}44;
                    color: #ffffff;
                }}
            """)
            p_btn.clicked.connect(lambda _, v=v_id: self._preview_specific_voice(v))
            b_lay.addWidget(p_btn)

            cmp_grid.addWidget(box)

        cmp_lay.addLayout(cmp_grid)
        lay.addWidget(compare_card)

        # 4. Voice Profiles (Selectable Presets)
        prof_card = QFrame(); prof_card.setProperty("class", "card")
        pc_lay = QVBoxLayout(prof_card)
        pc_lay.setSpacing(10)

        p_hdr = QLabel("3. VOICE PROFILES (Acoustic Presets)")
        p_hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p_hdr.setStyleSheet("color: #ffffff;")
        pc_lay.addWidget(p_hdr)

        p_sub = QLabel("Select an acoustic preset tailored for your operational environment:")
        p_sub.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        pc_lay.addWidget(p_sub)

        prof_flow = QHBoxLayout()
        prof_flow.setSpacing(6)
        self._profile_buttons: Dict[str, QPushButton] = {}
        profiles = ["Athena Omega", "Athena Prime", "Professional", "Friendly", "Natural", "Warm", "Technical", "Calm", "Founder"]
        cur_prof = self._voice_mgr.get_current_profile()

        for pname in profiles:
            btn = QPushButton(pname)
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_active = (pname == cur_prof)
            if is_active:
                btn.setStyleSheet(
                    "background: rgba(0, 212, 255, 0.35); color: #ffffff; "
                    "border: 1px solid #00d4ff; border-radius: 6px; padding: 6px 12px;"
                )
            else:
                btn.setStyleSheet(
                    "background: rgba(255, 255, 255, 0.05); color: #cbd5e1; "
                    "border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px;"
                )
            btn.clicked.connect(lambda _, p=pname: self._on_profile_button_clicked(p))
            self._profile_buttons[pname] = btn
            prof_flow.addWidget(btn)
        pc_lay.addLayout(prof_flow)

        lay.addWidget(prof_card)

        # 5. Voice Customization Sliders (9 Axes, 0-100)
        custom_card = QFrame(); custom_card.setProperty("class", "card")
        cc_lay = QVBoxLayout(custom_card)
        cc_lay.setSpacing(10)

        c_hdr_row = QHBoxLayout()
        c_title = QLabel("4. VOICE TUNING (9-Axis Prosody Calibration)")
        c_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        c_title.setStyleSheet("color: #ffffff;")
        c_hdr_row.addWidget(c_title)
        c_hdr_row.addStretch()

        reset_omega_btn = QPushButton("★ Reset to ATHENA OMEGA Defaults")
        reset_omega_btn.setStyleSheet(
            "background: rgba(56, 189, 248, 0.2); color: #38bdf8; "
            "border: 1px solid #38bdf8; padding: 5px 12px; border-radius: 5px; font-weight: bold; font-size: 10px;"
        )
        reset_omega_btn.clicked.connect(self._reset_to_athena_omega_defaults)
        c_hdr_row.addWidget(reset_omega_btn)

        reset_def_btn = QPushButton("★ ATHENA PRIME Defaults")
        reset_def_btn.setStyleSheet(
            "background: rgba(251, 191, 36, 0.15); color: #fbbf24; "
            "border: 1px solid #fbbf24; padding: 5px 12px; border-radius: 5px; font-weight: bold; font-size: 10px;"
        )
        reset_def_btn.clicked.connect(self._reset_to_athena_prime_defaults)
        c_hdr_row.addWidget(reset_def_btn)

        prev_custom_btn = QPushButton("▶ Audition Adjustments")
        prev_custom_btn.setStyleSheet(
            "background: rgba(0, 212, 255, 0.2); color: #00d4ff; "
            "border: 1px solid #00d4ff; padding: 5px 12px; border-radius: 5px; font-weight: bold; font-size: 10px;"
        )
        prev_custom_btn.clicked.connect(self._preview_custom_audio)
        c_hdr_row.addWidget(prev_custom_btn)
        cc_lay.addLayout(c_hdr_row)

        c_sub = QLabel("Fine-tune 9 acoustic prosody parameters (0-100 range) with live audio audition:")
        c_sub.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        cc_lay.addWidget(c_sub)

        # Sliders grid
        slider_grid = QGridLayout()
        slider_grid.setHorizontalSpacing(16)
        slider_grid.setVerticalSpacing(8)

        self._sliders: Dict[str, QSlider] = {}
        self._slider_labels: Dict[str, QLabel] = {}

        cur_params = self._voice_mgr.get_custom_parameters()
        slider_defs = [
            ("warmth", "Warmth (Velvet Acoustic Richness)", cur_params.get("warmth", 85), "Lower formant depth & soothing velvety timbre"),
            ("pitch", "Pitch (Fundamental F0 Frequency)", cur_params.get("pitch", 58), "Fundamental frequency base of vocal cords"),
            ("speed", "Speed (Human Syllabic Tempo)", cur_params.get("speed", 48), "Human deliberate pacing (never rushed or synthetic)"),
            ("energy", "Energy (Projection & Pressure)", cur_params.get("energy", 62), "Vocal authority and dynamic projection"),
            ("expressiveness", "Expressiveness (Emotional Inflection)", cur_params.get("expressiveness", 72), "Natural melodic variation and emphasis"),
            ("pause_length", "Pause Length (Syntactic Intervals)", cur_params.get("pause_length", 60), "Natural sentence boundaries and clause intervals"),
            ("breath_level", "Breath Level (Natural Breathing Intervals)", cur_params.get("breath_level", 65), "Micro respiratory pauses before clauses"),
            ("humanity_level", "Humanity Level (Anti-Robotic Cadence)", cur_params.get("humanity_level", 90), "Calm falling sentence terminals and organic cadence"),
            ("conversational_level", "Conversational Level (Natural Hesitation)", cur_params.get("conversational_level", 80), "Human conversation pacing and dialogue flow"),
        ]

        for idx, (key, label_text, init_val, tooltip) in enumerate(slider_defs):
            row = idx // 2
            col = (idx % 2) * 2

            s_box = QVBoxLayout()
            lbl_row = QHBoxLayout()
            name_lbl = QLabel(label_text)
            name_lbl.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 11px;")
            name_lbl.setToolTip(tooltip)
            lbl_row.addWidget(name_lbl)
            lbl_row.addStretch()

            val_lbl = QLabel(f"{init_val} / 100")
            val_lbl.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 11px;")
            lbl_row.addWidget(val_lbl)
            s_box.addLayout(lbl_row)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(init_val)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    background: rgba(255, 255, 255, 0.1);
                    height: 6px;
                    border-radius: 3px;
                }
                QSlider::sub-page:horizontal {
                    background: #00d4ff;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #ffffff;
                    border: 2px solid #00d4ff;
                    width: 14px;
                    height: 14px;
                    margin: -4px 0;
                    border-radius: 7px;
                }
                QSlider::handle:horizontal:hover {
                    background: #00d4ff;
                }
            """)
            slider.valueChanged.connect(self._on_slider_value_changed)
            s_box.addWidget(slider)

            self._sliders[key] = slider
            self._slider_labels[key] = val_lbl
            slider_grid.addLayout(s_box, row, col, 1, 2)

        cc_lay.addLayout(slider_grid)
        lay.addWidget(custom_card)

        # 6. Founder Profile & Voice Recognition Integration
        founder_card = QFrame(); founder_card.setProperty("class", "card")
        fc_lay = QVBoxLayout(founder_card)
        fc_lay.setSpacing(10)

        f_hdr = QLabel("5. FOUNDER CUSTOM PROFILE & BIOMETRIC RECOGNITION")
        f_hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        f_hdr.setStyleSheet("color: #00ff88;")
        fc_lay.addWidget(f_hdr)

        f_desc = QLabel(
            "Personalize and store a bespoke Founder voice edition for Anand_Honestic. "
            "When your biometric voice print is recognized, ATHENA PRIME instantly executes the greeting in your profile."
        )
        f_desc.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 11px;")
        fc_lay.addWidget(f_desc)

        f_row = QHBoxLayout()
        self._founder_profile_edit = QLineEdit("ATHENA PRIME - Founder Edition")
        self._founder_profile_edit.setPlaceholderText("Profile Name (e.g. ATHENA PRIME - Founder Edition)")
        f_row.addWidget(self._founder_profile_edit, stretch=1)

        save_fp_btn = QPushButton("👑 Save Founder Profile")
        save_fp_btn.setStyleSheet(
            "background: rgba(0, 255, 136, 0.2); color: #00ff88; "
            "border: 1px solid #00ff88; font-weight: bold; padding: 6px 14px;"
        )
        save_fp_btn.clicked.connect(self._save_founder_edition_profile)
        f_row.addWidget(save_fp_btn)

        test_rec_btn = QPushButton("🎙 Test Voice Recognition")
        test_rec_btn.setStyleSheet(
            "background: rgba(56, 189, 248, 0.2); color: #38bdf8; "
            "border: 1px solid #38bdf8; font-weight: bold; padding: 6px 14px;"
        )
        test_rec_btn.clicked.connect(self._test_founder_voice_recognition)
        f_row.addWidget(test_rec_btn)
        fc_lay.addLayout(f_row)

        self._founder_save_status = QLabel("✓ Settings auto-persisted to local HONESTIC OS memory.")
        self._founder_save_status.setStyleSheet("color: rgba(0, 255, 136, 0.8); font-size: 10px;")
        fc_lay.addWidget(self._founder_save_status)

        lay.addWidget(founder_card)
        lay.addStretch()

        scroll.setWidget(w)
        c_root.addWidget(scroll)

        # Initialize active states
        self._active_voice_name = self._voice_mgr.get_current_voice()
        self._active_profile_name = self._voice_mgr.get_current_profile()
        self._refresh_voice_ui_state()

        return container

    def _create_voice_card(self, vinfo: Dict[str, Any]) -> QFrame:
        """Constructs an interactive voice card with instant selection and preview."""
        vname = vinfo["name"]
        is_active = (vname.lower() == self._voice_mgr.get_current_voice().lower())
        is_flagship = bool(vinfo.get("flagship"))

        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setProperty("voice_name", vname)

        if is_flagship:
            bg = "rgba(0, 212, 255, 0.22)" if is_active else "rgba(0, 212, 255, 0.08)"
            border = "#00d4ff" if is_active else "rgba(0, 212, 255, 0.45)"
        else:
            bg = "rgba(0, 212, 255, 0.15)" if is_active else "rgba(255, 255, 255, 0.03)"
            border = "#00d4ff" if is_active else "rgba(255, 255, 255, 0.1)"

        card.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px;
            }}
        """)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 8, 10, 8)
        c_lay.setSpacing(6)

        # Name row with active badge and flagship badge
        name_row = QHBoxLayout()
        name_lbl = QLabel(f"<b>{vname}</b>")
        name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: #00d4ff;" if is_flagship else "color: #ffffff;")
        name_row.addWidget(name_lbl)

        if is_flagship:
            flag_badge = QLabel("★ FLAGSHIP")
            flag_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            flag_badge.setStyleSheet(
                "background: rgba(0, 212, 255, 0.25); color: #00d4ff; "
                "border-radius: 4px; padding: 2px 6px; font-weight: bold;"
            )
            name_row.addWidget(flag_badge)

        badge_lbl = QLabel("ACTIVE" if is_active else "")
        badge_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge_lbl.setStyleSheet("color: #00ff88; font-weight: bold;")
        badge_lbl.setObjectName("badge_lbl")
        name_row.addWidget(badge_lbl)
        name_row.addStretch()

        c_lay.addLayout(name_row)

        title_lbl = QLabel(vinfo.get("title", ""))
        title_lbl.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 600;")
        c_lay.addWidget(title_lbl)

        desc_lbl = QLabel(vinfo.get("desc", ""))
        desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 10px;")
        desc_lbl.setWordWrap(True)
        c_lay.addWidget(desc_lbl)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        sel_btn = QPushButton("Select")
        sel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_btn.setStyleSheet(
            "background: rgba(255, 255, 255, 0.08); color: #ffffff; "
            "padding: 4px 10px; border-radius: 4px; font-size: 10px;"
        )
        sel_btn.clicked.connect(lambda _, vn=vname: self._on_voice_card_selected(vn))
        btn_row.addWidget(sel_btn)

        prev_btn = QPushButton("▶ Preview")
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet(
            "background: rgba(0, 212, 255, 0.2); color: #00d4ff; "
            "border: 1px solid #00d4ff; padding: 4px 10px; border-radius: 4px; font-size: 10px; font-weight: bold;"
        )
        prev_btn.clicked.connect(lambda _, vn=vname: self._preview_specific_voice(vn))
        btn_row.addWidget(prev_btn)

        c_lay.addLayout(btn_row)
        return card

    def _on_voice_card_selected(self, vname: str):
        """Switches active voice instantly without restart."""
        self._active_voice_name = vname
        self._voice_mgr.set_voice(vname)
        self._refresh_voice_ui_state()

    def _preview_specific_voice(self, vname: str):
        """Plays immediate voice preview for target voice."""
        params = self._get_current_slider_values()
        prof = getattr(self, "_active_profile_name", self._voice_mgr.get_current_profile())
        self._voice_mgr.preview_voice(
            voice_name=vname,
            profile_name=prof,
            custom_params=params
        )

    def _on_profile_button_clicked(self, pname: str):
        """Switches voice profile preset and loads preset values into sliders."""
        self._active_profile_name = pname
        self._voice_mgr.set_profile(pname)

        # Update sliders to profile values (all 9 axes)
        p_data = VOICE_PROFILES.get(pname, {})
        for k in ("warmth", "pitch", "speed", "energy", "expressiveness", "pause_length", "breath_level", "humanity_level", "conversational_level"):
            if k in p_data and k in self._sliders:
                self._sliders[k].setValue(p_data[k])

        self._refresh_voice_ui_state()

    def _reset_to_athena_omega_defaults(self):
        """Resets all 9 acoustic sliders to the recommended ATHENA OMEGA flagship companion defaults."""
        from core.os_identity import ATHENA_OMEGA_RECOMMENDED_DEFAULTS
        for k, val in ATHENA_OMEGA_RECOMMENDED_DEFAULTS.items():
            if k in self._sliders:
                self._sliders[k].setValue(val)
        self._on_slider_value_changed()

    def _reset_to_athena_prime_defaults(self):
        """Resets all 9 acoustic sliders to the recommended ATHENA PRIME human defaults."""
        from core.os_identity import ATHENA_PRIME_RECOMMENDED_DEFAULTS
        for k, val in ATHENA_PRIME_RECOMMENDED_DEFAULTS.items():
            if k in self._sliders:
                self._sliders[k].setValue(val)
        self._on_slider_value_changed()

    def _on_slider_value_changed(self):
        """Updates numeric labels and persists slider adjustments."""
        params = self._get_current_slider_values()
        for k, val in params.items():
            if k in self._slider_labels:
                self._slider_labels[k].setText(f"{val} / 100")
        self._voice_mgr.set_custom_parameters(params)

    def _get_current_slider_values(self) -> Dict[str, int]:
        out = {}
        for k, s in getattr(self, "_sliders", {}).items():
            out[k] = s.value()
        return out

    def _preview_custom_audio(self):
        """Auditions current customization parameters immediately."""
        params = self._get_current_slider_values()
        cur_v = getattr(self, "_active_voice_name", self._voice_mgr.get_current_voice())
        cur_p = getattr(self, "_active_profile_name", self._voice_mgr.get_current_profile())
        self._voice_mgr.preview_voice(
            voice_name=cur_v,
            profile_name=cur_p,
            custom_params=params
        )

    def _save_founder_edition_profile(self):
        """Creates and stores custom Founder Voice Profile."""
        name = self._founder_profile_edit.text().strip() or "ATHENA - Founder Edition"
        params = self._get_current_slider_values()
        res = self._voice_mgr.save_founder_profile(name, params)
        if hasattr(self, "_founder_save_status"):
            self._founder_save_status.setText(
                f"✓ Profile '{name}' saved successfully at {datetime.now().strftime('%I:%M:%S %p')}!"
            )
            self._founder_save_status.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 11px;")

    def _test_founder_voice_recognition(self):
        """Tests founder voice detection greeting."""
        self._voice_mgr.speak_founder_welcome()

    def _refresh_voice_ui_state(self):
        """Refreshes visual states of cards and buttons."""
        cur_v = getattr(self, "_active_voice_name", self._voice_mgr.get_current_voice())
        cur_p = getattr(self, "_active_profile_name", self._voice_mgr.get_current_profile())

        if hasattr(self, "_cur_voice_lbl"):
            self._cur_voice_lbl.setText(f"Active Voice: <b>{cur_v}</b>")
        if hasattr(self, "_cur_profile_lbl"):
            self._cur_profile_lbl.setText(f"Active Profile: <b>{cur_p}</b>")

        # Update voice cards
        for vname, card in getattr(self, "_voice_card_widgets", {}).items():
            is_active = (vname.lower() == cur_v.lower())
            bg = "rgba(0, 212, 255, 0.15)" if is_active else "rgba(255, 255, 255, 0.03)"
            border = "#00d4ff" if is_active else "rgba(255, 255, 255, 0.1)"
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg};
                    border: 1px solid {border};
                    border-radius: 8px;
                    padding: 10px;
                }}
            """)
            badge = card.findChild(QLabel, "badge_lbl")
            if badge:
                badge.setText("ACTIVE" if is_active else "")

        # Update profile buttons
        for pname, btn in getattr(self, "_profile_buttons", {}).items():
            if pname == cur_p:
                btn.setStyleSheet(
                    "background: rgba(0, 212, 255, 0.35); color: #ffffff; "
                    "border: 1px solid #00d4ff; border-radius: 6px; padding: 6px 12px; font-weight: bold;"
                )
            else:
                btn.setStyleSheet(
                    "background: rgba(255, 255, 255, 0.05); color: #cbd5e1; "
                    "border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 12px;"
                )

    # ── Page 4: Smart Memory 2.0 ──


    # ── Page 4: Smart Memory 2.0 ──
    def _build_page_memory(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("Smart Memory 2.0")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        card = QFrame(); card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)

        s_row = QHBoxLayout()
        self._mem_search = QLineEdit()
        self._mem_search.setPlaceholderText("Search long-term memory...")
        s_row.addWidget(self._mem_search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._do_mem_search)
        s_row.addWidget(search_btn)
        c_lay.addLayout(s_row)

        self._mem_results = QTextEdit()
        self._mem_results.setReadOnly(True)
        self._mem_results.setFixedHeight(220)
        c_lay.addWidget(self._mem_results)

        lay.addWidget(card)
        self._do_mem_search()
        lay.addStretch()
        return w

    def _do_mem_search(self):
        q = self._mem_search.text().strip()
        res = search_memory(q or "identity")
        self._mem_results.setText(res or "No memory entries matched.")

    # ── Page 5: Themes ──
    def _build_page_themes(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("Themes & Windows 11 Fluent Glass")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        card = QFrame(); card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)

        c_lay.addWidget(QLabel("Select Theme Preset:"))
        self._hub_theme_combo = QComboBox()
        for k, th in THEMES.items():
            self._hub_theme_combo.addItem(f"{th['name']} — {th['desc']}", k)
        cur_t = get_theme_name()
        for i in range(self._hub_theme_combo.count()):
            if self._hub_theme_combo.itemData(i) == cur_t:
                self._hub_theme_combo.setCurrentIndex(i)
                break
        c_lay.addWidget(self._hub_theme_combo)

        c_lay.addSpacing(10)
        c_lay.addWidget(QLabel("Custom Accent Color Hex (#RRGGBB):"))
        self._custom_hex_edit = QLineEdit(self._theme_mgr.get_theme_data().get("accent", "#00d4ff"))
        c_lay.addWidget(self._custom_hex_edit)

        lay.addWidget(card)
        lay.addStretch()
        return w

    # ── Page 6: Avatar ──
    def _build_page_avatar(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("Avatar System")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        card = QFrame(); card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)

        c_lay.addWidget(QLabel("Choose Avatar Visualizer:"))
        self._hub_avatar_combo = QComboBox()
        for k, desc in AVATAR_MODES.items():
            self._hub_avatar_combo.addItem(desc, k)
        cur_av = get_avatar_mode()
        for i in range(self._hub_avatar_combo.count()):
            if self._hub_avatar_combo.itemData(i) == cur_av:
                self._hub_avatar_combo.setCurrentIndex(i)
                break
        c_lay.addWidget(self._hub_avatar_combo)

        lay.addWidget(card)
        lay.addStretch()
        return w

    # ── Page 7: Performance ──
    def _build_page_performance(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("Performance & Latency Modes")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        card = QFrame(); card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)

        c_lay.addWidget(QLabel("Performance Profile:"))
        self._hub_mode_combo = QComboBox()
        for k, m in PERFORMANCE_MODES.items():
            self._hub_mode_combo.addItem(f"{m['name']} — {m['desc']}", k)
        cur_m = get_performance_mode()
        for i in range(self._hub_mode_combo.count()):
            if self._hub_mode_combo.itemData(i) == cur_m:
                self._hub_mode_combo.setCurrentIndex(i)
                break
        c_lay.addWidget(self._hub_mode_combo)

        c_lay.addSpacing(10)
        box = QFrame()
        box.setStyleSheet("background: rgba(0, 212, 255, 0.06); border: 1px solid rgba(0, 212, 255, 0.2); border-radius: 8px; padding: 12px;")
        b_lay = QVBoxLayout(box)
        t_lbl = QLabel("⚡ Ultra Fast Direct Command Engine")
        t_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #00d4ff;")
        b_lay.addWidget(t_lbl)
        b_desc = QLabel(
            "Everyday commands ('open chrome', 'screenshot', 'volume up', 'shutdown') are executed locally "
            "with near 0 ms latency, bypassing the LLM roundtrip completely."
        )
        b_desc.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px;")
        b_lay.addWidget(b_desc)
        c_lay.addWidget(box)

        lay.addWidget(card)
        lay.addStretch()
        return w

    # ── Page 8: Plugin Store ──
    def _build_page_plugins(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        lbl = QLabel("Plugin Store & Catalog")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_w = QWidget()
        self._plugin_list_lay = QVBoxLayout(scroll_w)
        self._plugin_list_lay.setSpacing(8)

        self._refresh_plugin_store_ui()
        scroll.setWidget(scroll_w)
        lay.addWidget(scroll, stretch=1)
        return w

    def _refresh_plugin_store_ui(self):
        # Clear existing
        while self._plugin_list_lay.count():
            item = self._plugin_list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = list_store_items()
        for it in items:
            p_card = QFrame()
            p_card.setStyleSheet("background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 10px;")
            pc_lay = QHBoxLayout(p_card)

            meta_v = QVBoxLayout()
            p_title = QLabel(f"🧩 {it['name']}  v{it['version']}")
            p_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p_title.setStyleSheet("color: #00d4ff;")
            meta_v.addWidget(p_title)

            p_desc = QLabel(it['description'])
            p_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
            meta_v.addWidget(p_desc)
            pc_lay.addLayout(meta_v, stretch=1)

            # Action button
            pid = it["id"]
            if not it["installed"]:
                btn = QPushButton("Install")
                btn.setStyleSheet("background: #007a99; color: #fff;")
                btn.clicked.connect(lambda _, p=pid: self._install_store_plugin(p))
                pc_lay.addWidget(btn)
            else:
                tog_btn = QPushButton("Enabled" if it["enabled"] else "Disabled")
                tog_btn.setStyleSheet("background: #00aa55; color: #fff;" if it["enabled"] else "background: #555;")
                tog_btn.clicked.connect(lambda _, p=pid: self._toggle_store_plugin(p))
                pc_lay.addWidget(tog_btn)

                del_btn = QPushButton("Remove")
                del_btn.setStyleSheet("background: rgba(255, 50, 50, 0.2); color: #ff6666;")
                del_btn.clicked.connect(lambda _, p=pid: self._remove_store_plugin(p))
                pc_lay.addWidget(del_btn)

            self._plugin_list_lay.addWidget(p_card)

    def _install_store_plugin(self, pid: str):
        install_plugin(pid)
        self._refresh_plugin_store_ui()

    def _toggle_store_plugin(self, pid: str):
        toggle_plugin_status(pid)
        self._refresh_plugin_store_ui()

    def _remove_store_plugin(self, pid: str):
        uninstall_plugin(pid)
        self._refresh_plugin_store_ui()

    # ── Page 9: Automation ──
    def _build_page_automation(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("Automation Routines")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        from actions.automation_engine import ROUTINES, trigger_routine

        for k, r in ROUTINES.items():
            card = QFrame(); card.setProperty("class", "card")
            c_lay = QHBoxLayout(card)

            meta = QVBoxLayout()
            rt_title = QLabel(f"🤖 {r['name']}")
            rt_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            meta.addWidget(rt_title)

            rt_desc = QLabel(r['description'])
            rt_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
            meta.addWidget(rt_desc)
            c_lay.addLayout(meta, stretch=1)

            run_btn = QPushButton("▶ Run Routine")
            run_btn.clicked.connect(lambda _, rk=k: trigger_routine(rk))
            c_lay.addWidget(run_btn)

            lay.addWidget(card)

        lay.addStretch()
        return w

    # ── Page 10: Dashboard ──
    def _build_page_dashboard(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lbl = QLabel("Remote Dashboard & Mobile Control")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(lbl)

        card = QFrame(); card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)

        c_lay.addWidget(QLabel("Web Dashboard URL: https://localhost:8001"))
        c_lay.addWidget(QLabel("Encrypted with AES-256-GCM under PBKDF2 pairing code."))

        open_btn = QPushButton("🌐 Open Web Dashboard in Browser")
        open_btn.clicked.connect(lambda: webbrowser.open("https://localhost:8001"))
        c_lay.addWidget(open_btn)

        lay.addWidget(card)
        lay.addStretch()
        return w

    # ── Save All Settings ──
    def _save_all_settings(self):
        # 1. Owner & AI name
        owner = self._owner_name_edit.text().strip() or OWNER_NAME
        ai_key = self._ai_combo.currentData()
        ai_name = self._asst_name_edit.text().strip() or PERSONALITIES.get(ai_key, {}).get("name", DEFAULT_AI_NAME)
        custom_prompt = self._custom_prompt_edit.toPlainText().strip()

        save_assistant_config(ai_name, owner)
        save_ai_personality(ai_key)
        self._persona_mgr.set_personality(ai_key, ai_name, custom_prompt)

        # 2. Voice & Natural Voice Center
        vname = getattr(self, "_active_voice_name", self._voice_mgr.get_current_voice())
        save_voice(vname)
        self._voice_mgr.set_voice(vname)

        prof = getattr(self, "_active_profile_name", self._voice_mgr.get_current_profile())
        save_voice_profile(prof)
        self._voice_mgr.set_profile(prof)

        if hasattr(self, "_get_current_slider_values"):
            params = self._get_current_slider_values()
            self._voice_mgr.set_custom_parameters(params)


        # 3. Theme
        tkey = self._hub_theme_combo.currentData()
        custom_hex = self._custom_hex_edit.text().strip()
        save_theme_name(tkey)
        self._theme_mgr.set_theme(tkey, custom_hex if tkey == "custom" else None)

        # 4. Avatar
        av_key = self._hub_avatar_combo.currentData()
        save_avatar_mode(av_key)

        # 5. Performance
        pm_key = self._hub_mode_combo.currentData()
        save_performance_mode(pm_key)

        self.settings_applied.emit()
        self.accept()

    def _load_current_values(self):
        self._owner_name_edit.setText(get_user_name())
        self._asst_name_edit.setText(get_assistant_name())
        self._hub_voice_combo.setCurrentText(get_voice())
