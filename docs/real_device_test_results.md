# Redmi 14C 5G (HyperOS) Real-Device Validation Checklist

**Device:** Xiaomi Redmi 14C 5G  
**OS Version:** Xiaomi HyperOS (Android 14)  
**Host PC:** Windows 11 (ATHENA Sovereign OS)  
**Date:** 2026-10-29  
**Status Key:** `[ ] PENDING` | `[x] PASS` | `[!] FAIL`

---

## Validation Matrix

| Phase | Test Item | Target / Requirement | Status | Notes / Latency Measured |
|---|---|---|---|---|
| **1. Build & Install** | 1.1 APK Build | Gradle / Android Studio produces `app-debug.apk` without errors | `[ ] PENDING` | |
| | 1.2 ADB Connection | `adb devices` lists Redmi 14C 5G in `device` state | `[ ] PENDING` | |
| | 1.3 APK Installation | `adb install` finishes with `Success` | `[ ] PENDING` | |
| **2. HyperOS Config** | 2.1 Restricted Settings | "Allow restricted settings" granted in App Info | `[ ] PENDING` | |
| | 2.2 Accessibility Service | ATHENA Automation Service enabled in Accessibility menu | `[ ] PENDING` | |
| | 2.3 Battery Optimization | Set to "No restrictions" under Battery Saver | `[ ] PENDING` | |
| | 2.4 Autostart Permission | Autostart toggled ON | `[ ] PENDING` | |
| **3. Pairing (LAN)** | 3.1 PC QR Display | ATHENA PC displays pairing QR code on screen | `[ ] PENDING` | |
| | 3.2 Phone QR Scan | Phone app scans QR, extracts Ed25519 key & LAN IP | `[ ] PENDING` | |
| | 3.3 Cryptographic Handshake | Ed25519 mutual authentication & AES-256-GCM session key established | `[ ] PENDING` | |
| | 3.4 LAN Keep-Alive Ping | Ping/Pong RTT < 50ms over local Wi-Fi | `[ ] PENDING` | RTT: _____ ms |
| **4. Tier 1 Commands** | 4.1 Battery Status Query | "Check phone battery" returns real phone battery level | `[ ] PENDING` | Battery: _____ % |
| | 4.2 Open App (WhatsApp) | "Open WhatsApp on phone" launches WhatsApp on Redmi 14C | `[ ] PENDING` | |
| **5. Tier 2 Confirmation** | 5.1 Send Message Trigger | ATHENA requires spoken confirmation ("Confirm send") | `[ ] PENDING` | |
| | 5.2 Confirmation Approval | Confirmed message executes automation on phone | `[ ] PENDING` | |
| | 5.3 Rejection / Cancellation | "Cancel" halts execution immediately without action | `[ ] PENDING` | |
| **6. Security & Defense** | 6.1 Replay Attack Guard | Replayed frame rejected via timestamp/nonce check | `[ ] PENDING` | |
| | 6.2 Emergency Kill Switch | ATHENA UI or voice "Kill Switch" severs session instantly | `[ ] PENDING` | |

---

## Incident & Debug Log
*Record any runtime errors or unexpected behavior below:*

| Timestamp | Step | Observation / Error Message | Resolution / Code Fix |
|---|---|---|---|
| | | | |

---
**Verification Engineer:** Anand  
**Target Completion:** Real-device hardware verified on Redmi 14C 5G.

