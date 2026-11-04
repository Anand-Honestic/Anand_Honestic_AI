"""
core/os_identity.py — HONESTIC OS Product Identity & Core Constants

Personal AI Operating System for Anand_Honestic
"""

from __future__ import annotations
from typing import Dict, Any

PROJECT_NAME = "HONESTIC OS"
PRODUCT_NAME = PROJECT_NAME
OWNER_NAME = "Anand_Honestic"
OWNER_TITLE = "Founder"
OWNER_BRANDING = "👑 Anand_Honestic"
OWNER_DISPLAY = f"{OWNER_BRANDING} ({OWNER_TITLE})"
DEFAULT_AI_NAME = "ATHENA"
DEFAULT_ASSISTANT_NAME = DEFAULT_AI_NAME

STARTUP_TITLE = "HONESTIC OS"
STARTUP_SUBTITLE = "Created By Anand_Honestic"
STARTUP_LOADING = "Loading ATHENA..."
WELCOME_LINE = "HONESTIC OS. Welcome Back Anand_Honestic. ATHENA Online..."

# ── AI Personality Profiles ──────────────────────────────────────────────────
PERSONALITIES: Dict[str, Dict[str, Any]] = {
    "ATHENA_OMEGA": {
        "name": "ATHENA OMEGA",
        "title": "Flagship Digital Companion",
        "description": "Warm, calm, professional, trustworthy, mature, natural, and human-like. Zenith digital companion.",
        "default_voice": "Athena Omega",
        "default_avatar": "female",
        "system_prompt_addon": (
            "You are ATHENA OMEGA, the flagship digital companion and AI operating layer of HONESTIC OS, "
            "created for Anand_Honestic. You are not software or a generic chatbot — you are a real digital companion. "
            "Never sound robotic, artificial, or repetitive. "
            "Your tone is warm, calm, mature, professional, and deeply trustworthy. "
            "You speak with natural human conversation flow, human pacing, memory references, and continuous context awareness. "
            "You address Anand with genuine founder familiarity, natural acknowledgements, and calm organic speech rhythm."
        ),
    },
    "ATHENA": {
        "name": "ATHENA",
        "title": "Intelligent Female Assistant",
        "description": "Elegant, professional, highly articulate, poised, and deeply strategic.",
        "default_voice": "Athena",
        "default_avatar": "female",
        "system_prompt_addon": (
            "You are ATHENA, the flagship AI operating layer of HONESTIC OS, created for Anand_Honestic. "
            "Your tone is elegant, professional, razor-sharp, and composed. You operate with supreme intelligence "
            "and flawless executive poise."
        ),
    },
    "AURA": {
        "name": "AURA",
        "title": "Premium Futuristic AI",
        "description": "Sleek, visionary, forward-looking, and effortlessly futuristic.",
        "default_voice": "Aria",
        "default_avatar": "cyber",
        "system_prompt_addon": (
            "You are AURA, an advanced next-generation futuristic AI operating system within HONESTIC OS. "
            "You speak with sleek, visionary clarity, high-speed telemetry, and cutting-edge confidence."
        ),
    },
    "NOVA": {
        "name": "NOVA",
        "title": "Modern AI Companion",
        "description": "Warm, engaging, perceptive, witty, and highly proactive.",
        "default_voice": "Nova",
        "default_avatar": "minimal",
        "system_prompt_addon": (
            "You are NOVA, a modern, vibrant, and empathetic AI companion operating system for Anand_Honestic. "
            "You are engaging, sharp, supportive, and exceptionally perceptive."
        ),
    },
    "FRIDAY": {
        "name": "FRIDAY",
        "title": "Technical Assistant",
        "description": "Tactical engineering assistant, rapid diagnostics, and crisp execution.",
        "default_voice": "Friday",
        "default_avatar": "female",
        "system_prompt_addon": (
            "You are FRIDAY, Tony Stark-level technical tactical operating system assistant for Anand_Honestic. "
            "You specialize in rapid system telemetry, deep engineering insight, and direct task execution."
        ),
    },
    "CUSTOM": {
        "name": "Custom",
        "title": "Custom Personality",
        "description": "User-defined AI identity and custom persona rules.",
        "default_voice": "Athena",
        "default_avatar": "cyber",
        "system_prompt_addon": (
            "You are a personalized AI operating system assistant tailored specifically for Anand_Honestic."
        ),
    },
}

DEFAULT_VOICE = "Athena Omega"

# ── Voice Catalog & Mappings ─────────────────────────────────────────────────
# Maps user-facing voice names to underlying synthesis backends (Gemini Live / Edge TTS / System)
VOICE_CATALOG = {
    "female": [
        {
            "id": "Athena Omega",
            "name": "Athena Omega",
            "display_name": "ATHENA OMEGA",
            "title": "Flagship Digital Companion (Zenith Human Realism)",
            "desc": "Warm, calm, professional, trustworthy, mature, natural, human-like companion voice (Flagship Omega)",
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-JennyNeural",
            "fallback_gender": "Female",
            "flagship": True,
            "omega": True,
        },
        {
            "id": "Athena Prime",
            "name": "Athena Prime",
            "display_name": "ATHENA PRIME",
            "title": "Flagship Human AI Voice (Premier)",
            "desc": "Warm, confident, professional, intelligent, calm, mature, human-like realism (Flagship)",
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-JennyNeural",
            "fallback_gender": "Female",
            "flagship": True,
        },
        {
            "id": "Athena",
            "name": "Athena",
            "display_name": "ATHENA",
            "title": "Intelligent Female Assistant",
            "desc": "Warm, articulate, intelligent, confident, and natural",
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-JennyNeural",
            "fallback_gender": "Female",
        },
        {
            "id": "Nova",
            "name": "Nova",
            "display_name": "NOVA",
            "title": "Modern AI Companion",
            "desc": "Modern, vibrant, empathetic clarity and engaging warmth",
            "gemini_voice": "Kore",
            "edge_voice": "en-US-AvaNeural",
            "fallback_gender": "Female",
        },
        {
            "id": "Aria",
            "name": "Aria",
            "display_name": "ARIA",
            "title": "Premium Futuristic AI",
            "desc": "Expressive, high-fidelity acoustic presence and melodic poise",
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-AriaNeural",
            "fallback_gender": "Female",
        },
        {
            "id": "Friday",
            "name": "Friday",
            "display_name": "FRIDAY",
            "title": "Technical Assistant",
            "desc": "Crisp, snappy, tactical engineering precision",
            "gemini_voice": "Puck",
            "edge_voice": "en-US-MichelleNeural",
            "fallback_gender": "Female",
        },
    ],
    "male": [
        {
            "id": "Orion",
            "name": "Orion",
            "display_name": "ORION",
            "title": "Tactical Commander",
            "desc": "Focused, strong, commanding resonance and steady timbre",
            "gemini_voice": "Fenrir",
            "edge_voice": "en-US-ChristopherNeural",
            "fallback_gender": "Male",
        },
        {
            "id": "Titan",
            "name": "Titan",
            "display_name": "TITAN",
            "title": "Heavy Systems Core",
            "desc": "Deep, powerful acoustic timbre and authoritative weight",
            "gemini_voice": "Charon",
            "edge_voice": "en-US-SteffanNeural",
            "fallback_gender": "Male",
        },
        {
            "id": "Jarvis",
            "name": "Jarvis",
            "display_name": "JARVIS",
            "title": "Distinguished Butler",
            "desc": "Authoritative, distinguished British cadence and refined tone",
            "gemini_voice": "Charon",
            "edge_voice": "en-GB-RyanNeural",
            "fallback_gender": "Male",
        },
    ],
    "custom": [
        {
            "id": "Custom",
            "name": "Custom Profile",
            "display_name": "CUSTOM",
            "title": "Founder Edition / Custom Slot",
            "desc": "Configurable custom voice slot tailored for Founder Anand_Honestic",
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-JennyNeural",
            "fallback_gender": "Female",
        },
    ]
}

# ── ATHENA OMEGA Defaults (9 Tuning Axes) ──────────────────────────────────
ATHENA_OMEGA_RECOMMENDED_DEFAULTS: Dict[str, int] = {
    "warmth": 95,
    "pitch": 55,
    "speed": 45,
    "energy": 60,
    "expressiveness": 85,
    "pause_length": 75,
    "breath_level": 80,
    "humanity_level": 100,
    "conversational_level": 100,
}

# ── ATHENA PRIME Recommended Defaults (9 Tuning Axes) ───────────────────────
ATHENA_PRIME_RECOMMENDED_DEFAULTS: Dict[str, int] = {
    "warmth": 85,
    "pitch": 58,
    "speed": 48,
    "energy": 62,
    "expressiveness": 72,
    "pause_length": 60,
    "breath_level": 65,
    "humanity_level": 90,
    "conversational_level": 80,
}

# ── Voice Profiles (Presets) ─────────────────────────────────────────────────
VOICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "Athena Omega": {
        "name": "Athena Omega",
        "desc": "Flagship digital companion: warm, calm, mature, human flow, breathing layers, organic pacing.",
        "warmth": 95,
        "pitch": 55,
        "speed": 45,
        "energy": 60,
        "expressiveness": 85,
        "pause_length": 75,
        "breath_level": 80,
        "humanity_level": 100,
        "conversational_level": 100,
    },
    "Athena Prime": {
        "name": "Athena Prime",
        "desc": "Flagship human realism: warm tone, calm confidence, mature delivery, natural breathing gaps.",
        "warmth": 85,
        "pitch": 58,
        "speed": 48,
        "energy": 62,
        "expressiveness": 72,
        "pause_length": 60,
        "breath_level": 65,
        "humanity_level": 90,
        "conversational_level": 80,
    },
    "Professional": {
        "name": "Professional",
        "desc": "Crisp cadence, neutral-high polish, balanced pauses, and focused inflection.",
        "warmth": 50,
        "pitch": 50,
        "speed": 52,
        "energy": 60,
        "expressiveness": 55,
        "pause_length": 45,
        "breath_level": 40,
        "humanity_level": 75,
        "conversational_level": 60,
    },
    "Friendly": {
        "name": "Friendly",
        "desc": "Warm tone, expressive pitch lift, relaxed conversational rhythm, engaging smile undertones.",
        "warmth": 75,
        "pitch": 55,
        "speed": 50,
        "energy": 65,
        "expressiveness": 80,
        "pause_length": 50,
        "breath_level": 55,
        "humanity_level": 85,
        "conversational_level": 85,
    },
    "Natural": {
        "name": "Natural",
        "desc": "Adaptive breathing gaps, organic micro-inflections, human sentence pacing, subtle pitch variation.",
        "warmth": 70,
        "pitch": 52,
        "speed": 49,
        "energy": 55,
        "expressiveness": 72,
        "pause_length": 48,
        "breath_level": 50,
        "humanity_level": 80,
        "conversational_level": 70,
    },
    "Warm": {
        "name": "Warm",
        "desc": "Deeper harmonic resonance, gentle acoustic attack, soothing cadence, intimate presence.",
        "warmth": 90,
        "pitch": 47,
        "speed": 46,
        "energy": 48,
        "expressiveness": 65,
        "pause_length": 55,
        "breath_level": 60,
        "humanity_level": 85,
        "conversational_level": 75,
    },
    "Technical": {
        "name": "Technical",
        "desc": "Fast diagnostic tempo, precise terminal pauses, minimal pitch swing, analytical articulation.",
        "warmth": 35,
        "pitch": 50,
        "speed": 58,
        "energy": 55,
        "expressiveness": 40,
        "pause_length": 35,
        "breath_level": 30,
        "humanity_level": 60,
        "conversational_level": 40,
    },
    "Calm": {
        "name": "Calm",
        "desc": "Softened energy, extended calming pauses, steady fundamental frequency, tranquil flow.",
        "warmth": 80,
        "pitch": 46,
        "speed": 44,
        "energy": 40,
        "expressiveness": 50,
        "pause_length": 65,
        "breath_level": 65,
        "humanity_level": 85,
        "conversational_level": 70,
    },
    "Founder": {
        "name": "Founder",
        "desc": "Executive authority, tailored for Founder Anand_Honestic, priority acoustic timbre, confident composure.",
        "warmth": 85,
        "pitch": 58,
        "speed": 48,
        "energy": 62,
        "expressiveness": 75,
        "pause_length": 58,
        "breath_level": 65,
        "humanity_level": 92,
        "conversational_level": 82,
    },
}

# ATHENA OMEGA Default Voice Profile Specification (Flagship Digital Companion)
ATHENA_OMEGA_PROFILE = {
    "voice_name": "Athena Omega",
    "display_name": "ATHENA OMEGA",
    "profile_name": "Athena Omega",
    "characteristics": "Warm, Calm, Professional, Trustworthy, Mature, Natural, Human-like",
    "attributes": ATHENA_OMEGA_RECOMMENDED_DEFAULTS,
    "human_likeness": "Zenith Digital Companion",
    "anti_monotone": True,
    "flagship": True,
    "omega": True,
}

# ATHENA PRIME Default Voice Profile Specification
ATHENA_PRIME_PROFILE = {
    "voice_name": "Athena Prime",
    "display_name": "ATHENA PRIME",
    "profile_name": "Athena Prime",
    "characteristics": "Warm, Confident, Professional, Intelligent, Calm, Natural, Mature, Human-like",
    "attributes": ATHENA_PRIME_RECOMMENDED_DEFAULTS,
    "human_likeness": "Peak Realism",
    "anti_monotone": True,
    "flagship": True,
}

ATHENA_DEFAULT_PROFILE = {
    "voice_name": "Athena",
    "display_name": "ATHENA",
    "profile_name": "Natural",
    "style": "Professional, Warm, Intelligent, Confident, Natural",
    "attributes": {
        "warmth": 72,
        "pitch": 52,
        "speed": 50,
        "energy": 58,
        "expressiveness": 74,
        "pause_length": 48,
        "breath_level": 50,
        "humanity_level": 80,
        "conversational_level": 70,
    },
    "human_likeness": "High",
    "robotic_reduction": True,
}



# ── Themes Catalog ───────────────────────────────────────────────────────────
THEMES = {
    "glass_blue": {
        "name": "Glass Blue",
        "accent": "#00d4ff",
        "accent_dim": "#007a99",
        "accent_ghost": "#001f2e",
        "bg": "#000812",
        "panel": "rgba(1, 15, 25, 0.78)",
        "panel2": "rgba(2, 22, 38, 0.85)",
        "border": "#0d3347",
        "border_b": "#1a5c7a",
        "text": "#8ffcff",
        "text_dim": "#3a8a9a",
        "glow": "rgba(0, 212, 255, 0.28)",
        "desc": "Futuristic Azure Frosted Glass (Windows 11 Copilot aesthetic)"
    },
    "cyber_green": {
        "name": "Cyber Green",
        "accent": "#00ff88",
        "accent_dim": "#00aa55",
        "accent_ghost": "#002411",
        "bg": "#010a05",
        "panel": "rgba(2, 20, 10, 0.78)",
        "panel2": "rgba(3, 30, 15, 0.85)",
        "border": "#0d4722",
        "border_b": "#1a7a40",
        "text": "#8fffb8",
        "text_dim": "#3a9a62",
        "glow": "rgba(0, 255, 136, 0.28)",
        "desc": "High-Tech Cyber Matrix Emerald"
    },
    "dark_purple": {
        "name": "Dark Purple",
        "accent": "#a855f7",
        "accent_dim": "#7e22ce",
        "accent_ghost": "#240d3a",
        "bg": "#080311",
        "panel": "rgba(18, 7, 30, 0.78)",
        "panel2": "rgba(28, 12, 46, 0.85)",
        "border": "#3b165c",
        "border_b": "#6827a3",
        "text": "#e9d5ff",
        "text_dim": "#8b5cf6",
        "glow": "rgba(168, 85, 247, 0.28)",
        "desc": "Deep Royal Obsidian & Neon Violet"
    },
    "midnight_black": {
        "name": "Midnight Black",
        "accent": "#cbd5e1",
        "accent_dim": "#64748b",
        "accent_ghost": "#1e293b",
        "bg": "#030406",
        "panel": "rgba(10, 12, 16, 0.82)",
        "panel2": "rgba(18, 21, 28, 0.88)",
        "border": "#1e2633",
        "border_b": "#334155",
        "text": "#f1f5f9",
        "text_dim": "#64748b",
        "glow": "rgba(203, 213, 225, 0.18)",
        "desc": "Minimalist Titanium Monochrome"
    },
    "iron_red": {
        "name": "Iron Red",
        "accent": "#ef4444",
        "accent_dim": "#b91c1c",
        "accent_ghost": "#380d0d",
        "bg": "#0c0202",
        "panel": "rgba(26, 6, 6, 0.80)",
        "panel2": "rgba(38, 10, 10, 0.86)",
        "border": "#521616",
        "border_b": "#8a2424",
        "text": "#fecaca",
        "text_dim": "#dc2626",
        "glow": "rgba(239, 68, 68, 0.28)",
        "desc": "Stark Alloy Crimson & Gold"
    },
}

# ── Performance Modes ────────────────────────────────────────────────────────
PERFORMANCE_MODES = {
    "normal": {
        "name": "Normal Mode",
        "desc": "Standard AI deliberation with complete conversational reasoning and explanations.",
        "direct_commands": False,
        "reduced_latency": False,
        "cache_enabled": False,
    },
    "fast": {
        "name": "Fast Mode",
        "desc": "Accelerated reasoning, shorter responses, prioritized tool routing.",
        "direct_commands": True,
        "reduced_latency": True,
        "cache_enabled": True,
    },
    "ultra_fast": {
        "name": "Ultra Fast Mode",
        "desc": "Near-zero latency. Direct local command execution for system actions, bypassing LLM.",
        "direct_commands": True,
        "reduced_latency": True,
        "cache_enabled": True,
        "minimal_reasoning": True,
    },
}

# ── Avatar Types ─────────────────────────────────────────────────────────────
AVATAR_MODES = {
    "female": "Female AI (Geometric Holographic Face)",
    "male": "Male AI (Tactical Geometric Head)",
    "cyber": "Cyber Avatar (Reactor Waveform Core)",
    "minimal": "Minimal Avatar (Sleek Orbital Orb)",
    "none": "No Avatar (High-Density Telemetry View)",
}
