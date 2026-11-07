# HONESTIC OS / ATHENA — Sovereign Voice AI & Cross-Platform Dual-AI System

> **Windows 11 PC (ATHENA) + Redmi 14C 5G / Phone AI Companion (Android/iOS)**  
> Production-grade, zero-trust, real-time voice and automation system with seamless offline resilience and hardware-backed device synchronization.

---

## 🏛️ Project Architecture & Repository Structure

The repository is strictly structured into modular components:

```
Anand_Honestic_AI/
├── core/                  # PC Python Engine & Services
│   ├── remote_security/   # Ed25519 identity, AES-256-GCM cipher, DPAPI registry, Replay defense
│   ├── remote_companion_server.py # WSS / LAN companion server & session lifecycle
│   ├── remote_intent_router.py    # DualAIIntentRouter with DistributedActionLock
│   ├── remote_push_gateway.py     # FCM / APNs zero-payload wake notification gateway
│   ├── remote_clipboard.py        # Cross-device clipboard sync with sensitive token scrubbing
│   ├── natural_speech_engine.py   # Multi-engine TTS (Edge TTS, Windows SAPI/OneCore fallback)
│   ├── brain_router.py            # Sovereign offline/online brain & language sticky routing
│   └── offline_engine.py          # Local model fallback & connectivity state machine
├── android/               # Android Companion App (Kotlin, Gradle)
│   ├── app/src/main/
│   │   ├── java/com/honestic/athena/
│   │   │   ├── AthenaAccessibilityService.kt # A11y UI automation & password field rejection
│   │   │   ├── AthenaForegroundService.kt    # Sticky foreground service & Keep-Alive WSS
│   │   │   ├── KeystoreCryptoManager.kt      # Android Keystore hardware-backed Ed25519/AES-GCM
│   │   │   ├── OnboardingActivity.kt         # Camera QR pairing & security pin UI
│   │   │   └── WhitelistManagerActivity.kt   # App control whitelist management
│   │   ├── res/
│   │   └── AndroidManifest.xml               # Foreground service types & permissions
│   ├── build.gradle.kts   # Root & app build specifications (SDK 34)
│   └── settings.gradle.kts
├── ios/                   # iOS Companion Bridge (Swift)
│   └── AthenaCompanion/
│       └── AthenaIOSBridge.swift             # CryptoKit Ed25519, Keychain, WSS, PushKit
├── tools/                 # Test Harnesses & Device Diagnostics
│   └── verify_redmi_14c_e2e.py # 10-phase end-to-end device verification harness
├── tests/                 # Full Automated Test Suite (169 Tests, 17 Suites)
│   ├── __init__.py
│   ├── test_phase1_security.py       # Ed25519, AES-256-GCM, DPAPI, Replay defenses
│   ├── test_phase2_lan_routing.py    # Intent classifier, routing, distributed lock
│   ├── test_phase3_push_gateway.py   # Zero-payload push dispatch & token registry
│   ├── test_phase4_android_a11y.py   # Android A11y policy, HyperOS compliance
│   ├── test_phase5_relay_webrtc.py   # Remote relay protocol & token auth
│   ├── test_phase8_top3_features.py  # Notification mirror, clipboard, camera feed
│   ├── test_rc4_athena_sovereign.py  # Sovereign identity & command lockdown
│   ├── test_rc5_runtime_lockdown.py  # Unified pipeline & sticky language routing
│   ├── test_rc6_audio_bugs.py        # Audio pipeline, queue overflow, SAPI fallback
│   └── test_rc7_offline_resilience.py# Offline/online recovery state machine
├── docs/                  # Engineering Reports & Specifications
│   ├── real_device_validation_and_latency_guide.md
│   ├── dual_ai_production_system_report.md
│   ├── dual_ai_system_architecture_and_security_plan.md
│   ├── rc7_speaker_playback_recovery_report.md
│   ├── rc7_offline_recovery_report.md
│   ├── rc7_offline_resilience_report.md
│   └── rc6_audio_bug_report.md
├── relay/                 # WebRTC / WebSocket Remote Relay
│   ├── server.py          # Asyncio relay server with room-based routing
│   ├── Dockerfile         # Production container spec
│   ├── docker-compose.yml # Compose config with Caddy reverse proxy
│   └── Caddyfile          # TLS termination & Let's Encrypt config
├── actions/               # PC System Actions & Automation Handlers
├── config/                # Configuration and API credential templates
├── main.py                # ATHENA PC Application Entrypoint
├── ui.py                  # ATHENA Desktop UI (PyQt / CustomTkinter)
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation

```

---

## 🚀 Setup Instructions

### 1. ATHENA PC (Windows 11) Setup

#### Prerequisites:
- Python 3.10 - 3.12 (or compatible 3.15)
- Windows 11 with microphone and speaker access
- Git (optional, for cloning)

#### Step 1.1: Clone and Create Virtual Environment
```powershell
cd Anand_Honestic_AI
python -m venv .venv
.venv\Scripts\activate
```

#### Step 1.2: Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 1.3: Configure API Keys & Secrets
Create `config/api_keys.json` with your Gemini API key (or run `python main.py` to use the interactive onboarding UI):
```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE"
}
```

#### Step 1.4: Launch ATHENA PC
```powershell
python main.py
```
ATHENA will boot into Online Gemini Live mode. If no internet connection is detected, ATHENA automatically shifts to Offline Local Intelligence Mode.

---

### 2. Android Phone Companion Setup (Redmi 14C 5G / Xiaomi HyperOS)

The Android companion connects securely to ATHENA over the local Wi-Fi network (or remote relay) to execute phone automations, forward notifications, and sync clipboards.

#### Xiaomi HyperOS / Redmi 14C 5G Specific Configuration:
Xiaomi HyperOS enforces aggressive background restrictions and security sandboxing. Apply the following settings on the Redmi 14C 5G:

1. **Allow Restricted Settings (Android 13/14+ Requirement)**:
   - Go to `Settings` -> `Apps` -> `Manage apps` -> `ATHENA Companion`.
   - Tap the top-right 3 dots `⋮` and select **"Allow restricted settings"**.
   - Authenticate with fingerprint or screen lock.
2. **Enable Accessibility Service**:
   - Go to `Settings` -> `Additional settings` -> `Accessibility` -> `Downloaded apps`.
   - Select **ATHENA Automation Service** and toggle it **ON**.
   - Accept the HyperOS 10-second security confirmation dialog.
3. **Exempt from Battery Optimization**:
   - In `ATHENA Companion` App Info:
   - `Battery saver` -> Select **"No restrictions"** (prevents background process termination).
4. **Grant Autostart Permission**:
   - In `ATHENA Companion` App Info -> Enable **Autostart** (allows reconnecting after device reboot).
5. **Display Over Other Apps**:
   - Allow "Display pop-up windows while running in the background".

---

## 🛠️ How to Build the Android APK

You can build the debug or release APK using Gradle directly from the command line or Android Studio:

### Option A: Command Line (Windows PowerShell)
```powershell
cd android

# Ensure gradlew has execution rights
# Run Gradle assembleDebug:
.\gradlew.bat assembleDebug
```

### Option B: Command Line (Linux / macOS)
```bash
cd android
chmod +x ./gradlew
./gradlew assembleDebug
```

### Output APK Location:
The compiled APK will be generated at:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

### Installing on Redmi 14C 5G via ADB:
```powershell
adb devices
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 🧪 How to Run Tests

The test suite covers cryptographic security, LAN routing, push notification dispatch, Android accessibility compliance, remote relay WebRTC negotiation, and audio resilience.

### Run All 169 Tests (17 Test Suites):
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### Run Specific Test Suites:
```powershell
# Phase 1: Cryptographic Security & DPAPI Storage
python -m unittest tests/test_phase1_security.py

# Phase 2: LAN Intent Routing & Distributed Action Lock
python -m unittest tests/test_phase2_lan_routing.py

# Phase 3: Zero-Payload Push Gateway
python -m unittest tests/test_phase3_push_gateway.py

# Phase 4: Android Accessibility Compliance & Policy
python -m unittest tests/test_phase4_android_a11y.py

# Phase 5: Remote Relay & Room Routing
python -m unittest tests/test_phase5_relay_webrtc.py

# Phase 8: Notification Mirroring & Clipboard Scrubbing
python -m unittest tests/test_phase8_top3_features.py

# Audio Resilience & Offline Recovery
python -m unittest tests/test_rc6_audio_bugs.py
python -m unittest tests/test_rc7_offline_resilience.py
```

### Run the Redmi 14C End-to-End Verification Harness:
```powershell
python tools/verify_redmi_14c_e2e.py
```
This harness executes a complete 10-phase verification:
1. PC Ed25519 key generation and QR payload creation
2. Phone QR scanning and mutual cryptographic handshake
3. Secure WSS session establishment
4. LAN RTT ping/pong benchmark (< 50ms)
5. Tier 1 command dispatch and execution
6. Replay attack rejection test
7. Bidirectional clipboard sync with sensitive credential scrubbing
8. FCM/APNs zero-payload wake ping dispatch
9. Emergency Kill-Switch instant session termination
10. Cryptographic audit log chaining verification

---

## 🔒 Security Architecture Highlights

- **Hardware-Backed Device Registry**:
  - PC: Master identity stored in Windows Data Protection API (DPAPI) with machine-level encryption.
  - Android: Keys backed by hardware `AndroidKeyStore` StrongBox/TEE.
- **Mutual Authentication**:
  - QR Code exchange provides Ed25519 public keys, session nonce, and network coordinates.
  - `PAIR_CONFIRM` messages are cryptographically signed; unauthorized pairing attempts are rejected.
- **Replay Protection**:
  - Timestamp verification window (±30s) and random nonce tracking prevent intercepted message replays.
- **Three-Tier Authorization**:
  - **Tier 1 (Instant)**: Low-risk queries (read status, media control).
  - **Tier 2 (Confirmed)**: High-risk actions (send message, place call, open app) require user voice confirmation.
  - **Tier 3 (Blocked)**: Critical actions (financial apps, passwords, settings modifications) are permanently forbidden.
- **Zero-Payload Push**:
  - Cloud push notifications (FCM/APNs) contain only transient session hints (`SYNC_PING`). Zero message content or sensitive data traverses third-party push servers.

---

## 📄 License & Documentation

Detailed architectural reports, latency benchmarks, and disaster recovery procedures are available in the [`docs/`](file:///docs/) directory.

*HONESTIC OS / ATHENA — Built for Sovereign Digital Autonomy.*
