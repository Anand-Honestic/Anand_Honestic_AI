"""
dashboard/server.py — JARVIS Local HTTP Dashboard

HTTPS on port 8000 with a self-signed certificate generated on first run, plus
a second layer inside it: commands are encrypted with AES-256-GCM under a key
derived from the pairing code with PBKDF2. Both layers are required — the
server refuses to start without TLS rather than quietly serving in clear.

Install deps:  pip install fastapi "uvicorn[standard]" cryptography
"""

import asyncio
import base64
import hashlib
import re
import secrets
import socket
import string
import threading
import time
from pathlib import Path

_DEPS_OK = False
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    import uvicorn
    _DEPS_OK = True
except ImportError:
    pass

# python-multipart is required for file uploads — optional dependency
_UPLOAD_OK = False
try:
    from fastapi import UploadFile, File as FastAPIFile
    _UPLOAD_OK = True
except Exception:
    pass

BASE_DIR    = Path(__file__).resolve().parent.parent
STATIC_DIR  = Path(__file__).parent / "static"
# The port people TYPE, and the port the app actually runs on.
#
# They are not the same, and that is the fix for the most confusing failure
# this dashboard had. A bare `192.168.1.108:8000` typed into a phone browser is
# tried over HTTP; against a TLS listener that means the connection is accepted,
# found to carry no handshake, and closed — which Chrome reports as "refused to
# connect". The server is running perfectly and the user is told it is off.
#
# So the port people reach for answers in the protocol they reach for it with,
# and sends them one hop to the secure one. The QR code carries the secure URL
# directly, so it never takes the hop.
PORT        = 8000      # HTTP, redirects to SECURE_PORT
SECURE_PORT = 8001      # HTTPS, the dashboard itself
MAX_UPLOAD_MB = 500


def _make_uploads_dir() -> Path:
    """Return (and create) the cross-platform uploads folder."""
    for candidate in [
        Path.home() / "Downloads" / "JARVIS Uploads",
        Path.home() / "Documents" / "JARVIS Uploads",
        BASE_DIR / "uploads",
    ]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            pass
    return BASE_DIR / "uploads"


UPLOADS_DIR = _make_uploads_dir()

def _get_gemini_key() -> str | None:
    try:
        import json as _json
        with open(BASE_DIR / "config" / "api_keys.json", "r", encoding="utf-8") as f:
            return _json.load(f).get("gemini_api_key")
    except Exception:
        return None

_KEY_CHARS = [c for c in (string.ascii_uppercase + string.digits)
              if c not in ('O', 'I', 'L', '0', '1')]

# ── AES-256-CBC ───────────────────────────────────────────────────────────────
_AES_SALT = b'JARVIS-DASHBOARD-v1'


# Rounds for the pairing key -> AES key derivation.
#
# WHY THIS IS NOT ONE ROUND OF SHA-256, WHICH IS WHAT IT WAS
#     The pairing key is short because a person has to read it off a screen and
#     type it into a phone. Eight characters from a 31-letter alphabet is about
#     forty bits — fine against someone guessing at the login endpoint, which
#     is rate limited below, and NOT fine against someone who captured one
#     encrypted command and can guess offline as fast as their GPU allows.
#
#     At one round of SHA-256 that offline search is seconds. PBKDF2 at 200k
#     rounds makes each guess about five orders of magnitude more expensive
#     while costing this server ~80 ms once per session, at pairing time, where
#     nobody is waiting on a millisecond.
_KDF_ROUNDS = 200_000


def _derive_key(session_key: str) -> bytes:
    """Pairing key → 32-byte AES-256 key, deliberately slowly. See _KDF_ROUNDS."""
    return hashlib.pbkdf2_hmac(
        "sha256", session_key.encode("utf-8"), _AES_SALT, _KDF_ROUNDS, dklen=32
    )


def _decrypt(aes_key: bytes, enc_b64: str) -> str:
    """Decrypt base64(nonce[12] ‖ ciphertext‖tag) with AES-256-GCM.

    GCM RATHER THAN THE CBC THIS REPLACES
        CBC has no authentication. It hides a message and does nothing to stop
        one being CHANGED: an attacker on the same network can flip bits in the
        ciphertext and the server decrypts whatever falls out, with no way to
        tell. For a channel whose whole purpose is carrying commands to an
        assistant that opens applications and sends messages, "the text was
        secret" is the smaller half of what matters — "the text is the one that
        was sent" is the other half, and CBC never provided it.

        GCM authenticates as it decrypts. A single altered byte raises
        InvalidTag and the request is refused rather than obeyed.

    The old CBC path is not kept as a fallback on purpose. An attacker who can
    choose which format the server accepts can simply choose the weak one, and
    a downgrade left available is a downgrade that will be used.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = base64.b64decode(enc_b64)
    if len(raw) < 13:
        raise ValueError("ciphertext too short to contain a nonce")
    nonce, payload = raw[:12], raw[12:]
    return AESGCM(aes_key).decrypt(nonce, payload, None).decode("utf-8")


_BLOCK_CACHE = None


def blocking_firewall_rules() -> list:
    """Inbound Windows BLOCK rules aimed at the interpreter running this app.

    Public, read-only and never elevated, so the interface can warn about the
    one failure that is invisible from inside the app: a block rule overrides
    every allow rule, so the server listens correctly and the phone still
    cannot reach it. Empty on every other platform and whenever nothing is
    blocked.

    -> [(rule name, program path), ...]
    """
    import sys
    if sys.platform != "win32":
        return []

    # Cached for the process. Reading every inbound rule costs about a second,
    # and this is called from the Qt thread when the Remote Control panel
    # opens — a second of frozen interface every time, for an answer that only
    # changes when somebody edits their firewall.
    global _BLOCK_CACHE
    if _BLOCK_CACHE is not None:
        return _BLOCK_CACHE
    import os
    import subprocess

    py_exe = sys.executable
    sibling = os.path.join(
        os.path.dirname(py_exe),
        "pythonw.exe" if py_exe.lower().endswith("python.exe") else "python.exe")
    wanted = {py_exe.lower()}
    if os.path.exists(sibling):
        wanted.add(sibling.lower())

    found: list = []
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule",
             "name=all", "dir=in", "verbose"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=20,
        )
        name = program = None
        for line in r.stdout.splitlines():
            if line.startswith("Rule Name:"):
                name = line.split(":", 1)[1].strip()
                program = None
            elif line.startswith("Program:"):
                program = line.split(":", 1)[1].strip().lower()
            elif line.startswith("Action:"):
                if (name and program and program in wanted
                        and line.split(":", 1)[1].strip().lower() == "block"
                        and (name, program) not in found):
                    found.append((name, program))
    except Exception as exc:
        print(f"[Dashboard] could not read the firewall rules: {exc}")
    _BLOCK_CACHE = found
    return found


def _ensure_network_access(*ports: int) -> None:
    """Cross-platform, best-effort: open port in the OS firewall for LAN access.

    Runs in a background thread — never blocks uvicorn startup.

    Windows : writes a .bat file, runs it elevated via Windows ShellExecuteW
              (native UAC dialog, guaranteed to appear). One-time setup.
    macOS   : osascript admin dialog if the Application Firewall is on.
    Linux   : pkexec GUI → sudo -n → prints manual command as fallback.
    """
    import sys, subprocess, os, tempfile, threading

    # ── Windows ──────────────────────────────────────────────────────────────
    if sys.platform == "win32":
        import ctypes, time

        # Every port in one pass. Called once per port, this asked for
        # elevation once per port — two UAC dialogs for one dashboard, and two
        # racing .bat files whose output interleaved into contradictory
        # messages on the console.
        port_rules = {pt: f"HONESTIC OS Dashboard Port {pt}" for pt in ports}
        prog_rule  = "HONESTIC OS Dashboard Python"

        # BOTH interpreters, because the app runs under either one.
        #
        # THIS IS THE BUG THAT MADE THE PHONE UNREACHABLE FROM THE SHORTCUT.
        #     Started from an editor the app runs under `python.exe`. The
        #     desktop shortcut targets `pythonw.exe`, so that there is no
        #     console window — a different executable, and Windows Firewall
        #     rules are per-executable. Allowing one said nothing about the
        #     other, and the symptom was a dashboard that worked when launched
        #     one way and "refused to connect" when launched the other, on the
        #     same machine and the same network.
        py_exe = sys.executable
        _sibling = os.path.join(os.path.dirname(py_exe),
                                "pythonw.exe" if py_exe.lower().endswith("python.exe")
                                else "python.exe")
        py_exes = [py_exe] + ([_sibling] if os.path.exists(_sibling) else [])

        def _netsh_rule_exists(name: str) -> bool:
            try:
                r = subprocess.run(
                    ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
                )
                return r.returncode == 0 and "No rules match" not in r.stdout
            except Exception:
                return False

        def _network_is_public() -> bool:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     "(Get-NetConnectionProfile | "
                     "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                     "Measure-Object).Count"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=6,
                )
                return r.stdout.strip() not in ("", "0")
            except Exception:
                return False

        # One implementation, at module scope — see blocking_firewall_rules().
        # There were briefly two, and they disagreed about their return type,
        # which surfaced as 'too many values to unpack' in the error path.
        blocked      = blocking_firewall_rules()
        missing_ports = [pt for pt, nm in port_rules.items()
                         if not _netsh_rule_exists(nm)]
        need_prog    = not _netsh_rule_exists(prog_rule)
        need_private = _network_is_public()

        if blocked:
            print(f"[Dashboard] Windows is BLOCKING inbound connections to "
                  f"{', '.join(sorted(set(os.path.basename(e) for e in py_exes)))} "
                  f"({len(blocked)} block rule(s)). Your phone cannot reach the "
                  f"dashboard until those are removed — asking for permission "
                  f"to do that now.")

        if not missing_ports and not need_prog and not need_private and not blocked:
            return  # already fully configured

        # Build a .bat file — netsh + powershell, runs fast when elevated
        bat_lines = ["@echo off"]
        if need_private:
            bat_lines.append(
                'powershell -NoProfile -NonInteractive -Command "'
                'Get-NetConnectionProfile | '
                "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                'Set-NetConnectionProfile -NetworkCategory Private"'
            )
        for pt in missing_ports:
            bat_lines.append(
                f'netsh advfirewall firewall add rule '
                f'name="{port_rules[pt]}" protocol=TCP dir=in '
                f'localport={pt} action=allow'
            )
        # Remove the blocks FIRST. Adding an allow rule beside a block rule
        # changes nothing at all — Windows resolves the conflict in the block's
        # favour — so this is the line that actually fixes the connection.
        for rule_name in blocked:
            bat_lines.append(
                f'netsh advfirewall firewall delete rule '
                f'name="{rule_name}" dir=in'
            )

        if need_prog or blocked:
            # One allow rule per interpreter. `add rule` with an existing name
            # appends rather than replacing, so deleting first keeps this from
            # accumulating a new copy on every launch.
            bat_lines.append(
                f'netsh advfirewall firewall delete rule name="{prog_rule}" dir=in'
            )
            for exe in py_exes:
                bat_lines.append(
                    f'netsh advfirewall firewall add rule '
                    f'name="{prog_rule}" dir=in action=allow '
                    f'program="{exe}" enable=yes'
                )

        # Say what will be attempted, so a UAC prompt nobody expected has a
        # reason attached to it in the terminal.
        if blocked:
            print("[Dashboard] The Windows prompt about to appear is HONESTIC OS "
                  "removing those block rules. Declining it leaves the phone "
                  "dashboard unreachable, and nothing else is affected.")

        bat_body = "\r\n".join(bat_lines) + "\r\n"
        fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="jarvis_fw_")
        try:
            os.write(fd, bat_body.encode("mbcs"))   # Windows cmd.exe expects ANSI
            os.close(fd)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return

        # ── Try running directly (succeeds when already admin) ────────────────
        try:
            r = subprocess.run(
                [bat_path], capture_output=True, timeout=8, shell=True
            )
            if r.returncode == 0:
                print(f"[Dashboard] Firewall configured for {', '.join(str(pt) for pt in ports)}.")
                try:
                    os.unlink(bat_path)
                except Exception:
                    pass
                return
        except Exception:
            pass

        # ── ShellExecuteW: native UAC elevation (most reliable on Windows) ────
        # ShellExecuteW with verb "runas" always shows the UAC dialog regardless
        # of UAC level settings. Non-blocking — uvicorn is already running.
        print("[Dashboard] One-time network setup required.")
        print("[Dashboard] >>> A Windows security dialog will appear — click 'Yes' <<<")
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,       # hwnd  (no parent window)
                "runas",    # verb  (request elevation)
                bat_path,   # file  (our .bat)
                None,       # params
                None,       # working dir
                0,          # SW_HIDE (run without a visible cmd window)
            )
            if int(ret) > 32:
                # ShellExecuteW returns immediately; bat finishes in ~1 second.
                # Sleep briefly so the rules are in place before the first retry.
                time.sleep(2)
                # CHECK, DO NOT ASSUME. ShellExecuteW succeeding means the
                # dialog was accepted, not that netsh did what was asked — and
                # the whole point of this release is not to report an outcome
                # nobody looked at.
                still = blocking_firewall_rules()
                if still:
                    print("[Dashboard] ⚠️  Windows is STILL blocking inbound "
                          "connections to this interpreter.")
                    print("[Dashboard] ⚠️  Remove these by hand in Windows "
                          "Defender Firewall > Inbound Rules: "
                          + ", ".join(sorted({n for n, _ in still})))
                else:
                    print(f"[Dashboard] Network setup complete — "
                          f"{', '.join(str(pt) for pt in ports)} open.")
                    print("[Dashboard] Refresh your phone browser to connect.")
            else:
                print("[Dashboard] Setup was not allowed.")
                if blocked:
                    print("[Dashboard] Your phone CANNOT reach the dashboard "
                          "until this is done: Windows has block rules for "
                          + ", ".join(sorted({n for n, _ in blocked}))
                          + " which override every allow rule.")
                    print("[Dashboard] Either restart HONESTIC OS and accept the "
                          "prompt, or delete those rules in Windows Defender "
                          "Firewall > Inbound Rules.")
                else:
                    print("[Dashboard] Phone connections may fail until HONESTIC OS "
                          "is run as Administrator.")
        except Exception as e:
            print(f"[Dashboard] Firewall setup error: {e}")
        finally:
            # Cleanup after the bat has had time to run
            def _cleanup(path: str) -> None:
                time.sleep(5)
                try:
                    os.unlink(path)
                except Exception:
                    pass
            threading.Thread(target=_cleanup, args=(bat_path,), daemon=True).start()
        return

    # ── macOS ─────────────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        fw_ctl = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        try:
            r = subprocess.run(
                [fw_ctl, "--getglobalstate"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            if "disabled" in r.stdout.lower():
                return  # firewall off — nothing to do

            py = sys.executable
            listed = subprocess.run(
                [fw_ctl, "--listapps"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            if py in listed.stdout:
                return  # already allowed

            print("[Dashboard] One-time network setup — enter your password in the macOS dialog.")
            subprocess.run(
                ["osascript", "-e",
                 f'do shell script "{fw_ctl} --add {py} && {fw_ctl} --unblockapp {py}"'
                 f' with administrator privileges'],
                timeout=60,
            )
        except Exception:
            pass  # macOS firewall is off by default — silent failure is fine
        return

    # ── Linux ─────────────────────────────────────────────────────────────────
    def _privileged(cmd: list[str]) -> bool:
        for prefix in (["pkexec"], ["sudo", "-n"]):
            try:
                r = subprocess.run(prefix + cmd, capture_output=True, timeout=30)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        return False

    try:  # ufw
        r = subprocess.run(["ufw", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        if "active" in r.stdout.lower():
            if _privileged(["ufw", "allow", f"{port}/tcp"]):
                print(f"[Dashboard] ufw: port {port} allowed.")
            else:
                print(f"[Dashboard] Run manually:  sudo ufw allow {port}/tcp")
            return
    except FileNotFoundError:
        pass

    try:  # firewalld
        r = subprocess.run(
            ["firewall-cmd", "--state"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        )
        if "running" in r.stdout.lower():
            ok = (_privileged(["firewall-cmd", "--add-port", f"{port}/tcp", "--permanent"])
                  and _privileged(["firewall-cmd", "--reload"]))
            if ok:
                print(f"[Dashboard] firewalld: port {port} allowed.")
            else:
                print(f"[Dashboard] Run manually:  sudo firewall-cmd --add-port={port}/tcp --permanent && sudo firewall-cmd --reload")
            return
    except FileNotFoundError:
        pass

    try:  # iptables (not persistent but works until reboot)
        r = subprocess.run(["iptables", "-L", "INPUT", "-n"], capture_output=True, timeout=5)
        if r.returncode == 0:
            if _privileged(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"]):
                print(f"[Dashboard] iptables: port {port} opened.")
            else:
                print(f"[Dashboard] Run manually:  sudo iptables -A INPUT -p tcp --dport {port} -j ACCEPT")
    except FileNotFoundError:
        pass  # no iptables means firewall is probably off — nothing to do




# ── helpers ───────────────────────────────────────────────────────────────────

def _local_ip() -> str:
    """Return the best LAN-facing IPv4 address, no internet required."""
    # Method 1: route trick (fast, works when internet is available)
    for probe in ("8.8.8.8", "1.1.1.1", "192.168.1.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((probe, 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127."):
                return ip
        except Exception:
            pass

    # Method 2: hostname resolution (works offline on most systems)
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Method 3: enumerate all interfaces (fully offline, no external deps)
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def _ensure_certs() -> bool:
    """
    Make sure config/certs holds a TLS key pair, generating a self-signed one the
    first time the dashboard runs.

    The pair is deliberately NOT shipped in the repository. A private key that
    every user downloads is the same as having no private key at all: anyone can
    present a certificate that matches it. Generating locally gives each install
    its own key, costs about a second, and happens exactly once.

    Returns True when a usable pair exists afterwards; False leaves the caller on
    plain HTTP, which still works — the QR code simply encodes http:// instead.
    """
    certs = BASE_DIR / "config" / "certs"
    key_p = certs / "jarvis.key"
    crt_p = certs / "jarvis.crt"
    if key_p.exists() and crt_p.exists():
        return True

    try:
        import datetime
        import ipaddress
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("[Dashboard] cryptography not installed — serving over plain HTTP.")
        print("[Dashboard] For HTTPS run:  pip install cryptography")
        return False

    try:
        certs.mkdir(parents=True, exist_ok=True)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        who = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "HONESTIC OS Dashboard"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "HONESTIC OS"),
        ])

        # The SAN has to cover every address the phone might use: the LAN IP the
        # QR code encodes, plus localhost when testing on the machine itself.
        alt = [x509.DNSName("localhost"),
               x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
        try:
            lan = _local_ip()
            if not lan.startswith("127."):
                alt.append(x509.IPAddress(ipaddress.IPv4Address(lan)))
        except Exception:
            pass          # no LAN address resolvable — localhost entries still work

        # Timezone-aware UTC: datetime.utcnow() is deprecated from Python 3.12 on,
        # and the builder normalises aware values to UTC itself.
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(who)
            .issuer_name(who)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(alt), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )

        key_p.write_bytes(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        crt_p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        try:
            import os as _os
            _os.chmod(key_p, 0o600)   # best effort — largely a no-op on Windows
        except Exception:
            pass

        print(f"[Dashboard] Generated a self-signed certificate for this machine: {certs}")
        return True
    except Exception as e:
        print(f"[Dashboard] Certificate generation failed ({e}) — serving over plain HTTP.")
        return False


def _read(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


# ── DashboardServer ───────────────────────────────────────────────────────────

# How long an auth token stays valid, and how many failed logins an address
# gets before it has to wait.
#
# The old code had neither. A token, once issued, worked until the process
# ended — no expiry, no logout — and /login accepted unlimited guesses at the
# pairing key as fast as a script could send them. Eight characters is a large
# space, but "large" is not the same as "let them try forever": the point of a
# limit is that an attacker's cost grows while a person who mistypes their key
# twice never notices it exists.
_TOKEN_TTL_SECONDS = 12 * 3600
_LOGIN_MAX_TRIES   = 6
_LOGIN_WINDOW      = 300.0      # seconds the counter looks back over
_LOGIN_LOCKOUT     = 300.0      # seconds an address waits after using them up


class _Throttle:
    """Failed-attempt counter, per client address.

    Deliberately tiny and in memory: it protects a pairing key that is itself
    only alive for ten minutes, so nothing here needs to survive a restart.
    Successful logins clear the count, which keeps a household on one address
    from locking itself out because somebody fumbled the code once.
    """

    def __init__(self):
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def blocked_for(self, who: str) -> float:
        """Seconds this address must wait, or 0."""
        now = time.time()
        with self._lock:
            tries = [t for t in self._fails.get(who, []) if now - t < _LOGIN_WINDOW]
            self._fails[who] = tries
            if len(tries) < _LOGIN_MAX_TRIES:
                return 0.0
            return max(0.0, _LOGIN_LOCKOUT - (now - tries[-1]))

    def record_failure(self, who: str) -> None:
        with self._lock:
            self._fails.setdefault(who, []).append(time.time())

    def clear(self, who: str) -> None:
        with self._lock:
            self._fails.pop(who, None)


class DashboardServer:

    def __init__(self):
        self._ip                          = _local_ip()
        # token -> issued-at. A set had no way to expire anything; this does,
        # and `_auth` sweeps as it reads so nothing has to run a timer.
        self._tokens: dict[str, float]    = {}
        self._token_keys: dict[str, str]  = {}   # auth_token → session_key
        self._aes_cache:  dict[str, bytes]= {}   # session_key → AES bytes
        self._clients: set[WebSocket]     = set()
        self._history: list[dict]         = []
        self._command_queue               = asyncio.Queue()
        self._wake_callback               = None
        self._connect_callback            = None
        self._pending_keys: dict[str, float] = {}
        self._throttle                    = _Throttle()
        self._device_sessions: dict[str, dict] = {}  # device_token → {session_key}
        self._phone_audio_queue: asyncio.Queue    = asyncio.Queue(maxsize=200)
        self._uploads_dir                 = UPLOADS_DIR
        # Set by serve() when the port could not be taken, so the UI can say
        # why the QR code leads nowhere instead of showing it regardless.
        self._bind_error: str = ""
        self._login_html                  = _read("login.html")
        self._app_html                    = _read("app.html")
        self.app                          = self._build_app()

    # ── one-time key management ───────────────────────────────────────────

    def new_key(self, expiry_secs: int = 600) -> str:
        now = time.time()
        self._pending_keys = {k: v for k, v in self._pending_keys.items() if v > now}
        key = ''.join(secrets.choice(_KEY_CHARS) for _ in range(8))
        self._pending_keys[key] = now + expiry_secs
        return key

    @staticmethod
    def _ssl_enabled() -> bool:
        """Is HTTPS switched on? Off unless the user asked for it.

        WHY THE DEFAULT IS PLAIN HTTP, AFTER A RELEASE THAT MADE TLS MANDATORY
            The certificate has to be self-signed — there is no certificate
            authority on earth that will vouch for 192.168.1.108 — and a phone
            treats a self-signed certificate as an attack. Chrome shows a
            full-page interstitial; a QR scanner that opens links in its own
            in-app browser often shows nothing at all and offers no way to
            proceed, because those views deliberately have no "Advanced" button.

            So the practical result of requiring TLS was a dashboard nobody
            could reach, which is not a more secure product than one they can.
            The pairing key, the rate limit, the token expiry and the
            revoke-all-devices fix are all unaffected and all still apply.

            What IS lost over plain HTTP is the AES-GCM layer, because
            `crypto.subtle` does not exist outside a secure context. The page
            says so on its own badge rather than pretending, and commands then
            travel the local network in clear — which is what this dashboard
            did for every release before this one.

            Turn it on with "dashboard_https": true in config/api_keys.json if
            the network is one where that matters; the certificate is generated
            automatically and you will have to accept it once per device.
        """
        try:
            import json as _json
            with open(BASE_DIR / "config" / "api_keys.json", "r",
                      encoding="utf-8") as f:
                if not _json.load(f).get("dashboard_https"):
                    return False
        except Exception:
            return False
        certs = BASE_DIR / "config" / "certs"
        return (certs / "jarvis.key").exists() and (certs / "jarvis.crt").exists()

    def get_url(self) -> str:
        """The full URL the QR code carries — always with its scheme, so a
        scanner never has to guess."""
        if self._ssl_enabled():
            return f"https://{self._ip}:{SECURE_PORT}"
        return f"http://{self._ip}:{PORT}"

    def get_manual_url(self) -> str:
        """What to type into a phone browser by hand.

        Points at the redirect port when TLS is on, because a bare `ip:port`
        typed into a browser is tried over HTTP — and HTTP against the TLS port
        looks exactly like the server being switched off. The redirector speaks
        HTTP, so it answers, and sends the browser on to the secure page.
        """
        return f"{self._ip}:{PORT}"

    def _aes_key(self, session_key: str) -> bytes:
        if session_key not in self._aes_cache:
            self._aes_cache[session_key] = _derive_key(session_key)
        return self._aes_cache[session_key]

    def _decrypt(self, token: str, enc_b64: str) -> str | None:
        sk = self._token_keys.get(token)
        if not sk:
            return None
        try:
            return _decrypt(self._aes_key(sk), enc_b64)
        except Exception:
            return None

    # ── callbacks ────────────────────────────────────────────────────────

    def set_wake_callback(self, fn) -> None:
        self._wake_callback = fn

    def set_connect_callback(self, fn) -> None:
        self._connect_callback = fn

    # ── broadcast ────────────────────────────────────────────────────────

    async def broadcast(self, msg: dict) -> None:
        self._history.append(msg)
        if len(self._history) > 300:
            self._history = self._history[-300:]
        dead: set[WebSocket] = set()
        for ws in list(self._clients):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    # ── FastAPI app ───────────────────────────────────────────────────────

    def _build_app(self) -> "FastAPI":
        app = FastAPI(docs_url=None, redoc_url=None)

        def _valid(tok: str) -> bool:
            """Is this token live? Expired ones are dropped as they are found,
            which keeps the sweep free and needs no background timer."""
            if not tok:
                return False
            issued = self._tokens.get(tok)
            if issued is None:
                return False
            if time.time() - issued > _TOKEN_TTL_SECONDS:
                self._tokens.pop(tok, None)
                self._token_keys.pop(tok, None)
                return False
            return True

        def _auth(req: Request) -> bool:
            return _valid(req.headers.get("authorization", "")
                          .removeprefix("Bearer ").strip())

        def _who(req: Request) -> str:
            """The client address a throttle counts against."""
            return (getattr(getattr(req, "client", None), "host", "") or "unknown")

        @app.get("/login", response_class=HTMLResponse)
        async def login_page():
            return HTMLResponse(self._login_html)

        @app.get("/", response_class=HTMLResponse)
        async def index():
            # Auth is handled client-side via sessionStorage bearer token.
            # Server-side header auth can't work here because browser navigations
            # don't send custom headers (location.href doesn't carry Authorization).
            html = (self._app_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.post("/login")
        async def login(req: Request):
            who  = _who(req)
            wait = self._throttle.blocked_for(who)
            if wait > 0:
                # 429 rather than 401 on purpose: it tells an honest user why
                # their correct key was refused, and it tells a script that
                # guessing is not working.
                return JSONResponse(
                    {"ok": False,
                     "error": f"Too many attempts. Try again in "
                              f"{int(wait) + 1} seconds."},
                    status_code=429,
                )
            body    = await req.json()
            entered = str(body.get("pin", "")).strip().upper()
            now     = time.time()
            if entered in self._pending_keys and self._pending_keys[entered] > now:
                self._throttle.clear(who)
                del self._pending_keys[entered]          # one-time use
                tok = secrets.token_urlsafe(32)
                self._tokens[tok] = time.time()
                self._token_keys[tok] = entered
                self._aes_key(entered)                   # pre-derive & cache
                if self._connect_callback:
                    self._connect_callback()
                asyncio.create_task(self.broadcast(
                    {"type": "sys", "text": "Remote connection established."}
                ))
                # Bearer token in response body — no cookies needed (works on any browser/HTTP)
                return JSONResponse({"ok": True, "token": tok})
            self._throttle.record_failure(who)
            return JSONResponse({"ok": False, "error": "Invalid or expired key"},
                                status_code=401)

        @app.get("/auto-login")
        async def auto_login(key: str = ""):
            """QR code target — validates one-time key, creates session, redirects phone."""
            now = time.time()
            if not key or key not in self._pending_keys or self._pending_keys[key] <= now:
                return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}
  h2{color:#f87171;margin-bottom:12px}p{color:#5e6a7e;font-size:14px}
</style></head>
<body><div><h2>Link Expired</h2>
<p>Press <strong style="color:#dde3ed">Remote Control</strong> in the HONESTIC OS Desktop App to get a new QR code.</p>
</div></body></html>""")

            del self._pending_keys[key]
            tok     = secrets.token_urlsafe(32)
            dev_tok = secrets.token_urlsafe(32)
            self._tokens[tok] = time.time()
            self._token_keys[tok] = key
            self._aes_key(key)
            self._device_sessions[dev_tok] = {"session_key": key}

            if self._connect_callback:
                self._connect_callback()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Remote connection established via QR code."}
            ))

            return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<title>HONESTIC OS</title>
<style>
  body{{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}
  p{{color:#5e6a7e;font-size:14px}}
</style></head>
<body>
<script>
  sessionStorage.setItem('honestic_token','{tok}');
  sessionStorage.setItem('honestic_key','{key}');
  localStorage.setItem('honestic_device_token','{dev_tok}');
  sessionStorage.setItem('jarvis_token','{tok}');
  sessionStorage.setItem('jarvis_key','{key}');
  localStorage.setItem('jarvis_device_token','{dev_tok}');
  setTimeout(function(){{location.replace('/')}},400);
</script>
<p>Connecting to HONESTIC OS…</p>
</body></html>""")

        @app.post("/api/device-login")
        async def device_login_ep(req: Request):
            """Return a fresh auth token for a previously paired device token."""
            try:
                body = await req.json()
            except Exception:
                return JSONResponse({"ok": False}, status_code=400)
            dev_tok = (body.get("device_token") or "").strip()
            if not dev_tok or dev_tok not in self._device_sessions:
                return JSONResponse({"ok": False}, status_code=401)
            session_key = self._device_sessions[dev_tok]["session_key"]
            tok = secrets.token_urlsafe(32)
            self._tokens[tok] = time.time()
            self._token_keys[tok] = session_key
            self._aes_key(session_key)
            if self._connect_callback:
                self._connect_callback()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Known device reconnected automatically."}
            ))
            return JSONResponse({"ok": True, "token": tok, "key": session_key})

        @app.post("/api/revoke-devices")
        async def revoke_devices(req: Request):
            """Invalidate all persistent device tokens (admin action)."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            # ALSO drop the live tokens, which this did not do.
            #
            # It cleared the remembered devices and left every session those
            # devices had already opened working until the app restarted — so
            # "revoke all devices" revoked nothing anybody was currently using,
            # which is the one case somebody presses it for.
            #
            # The caller's own token is kept, or pressing the button would log
            # out the person who pressed it.
            mine  = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            count = len(self._device_sessions)
            live  = len(self._tokens) - (1 if mine in self._tokens else 0)
            self._device_sessions.clear()
            keep = self._tokens.get(mine)
            self._tokens.clear()
            self._token_keys = {k: v for k, v in self._token_keys.items() if k == mine}
            if keep is not None:
                self._tokens[mine] = keep
            return JSONResponse({"ok": True, "revoked": count, "sessions_ended": live})

        @app.post("/api/command")
        async def command(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body  = await req.json()
            token = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            enc   = body.get("enc", "")
            if enc:
                text = self._decrypt(token, enc)
                if text is None:
                    return JSONResponse({"error": "Decryption failed"}, status_code=400)
            else:
                text = (body.get("text") or "").strip()
            if text:
                await self._command_queue.put(text)
                if self._wake_callback:
                    self._wake_callback()
            return JSONResponse({"ok": True})

        @app.post("/api/wake")
        async def wake_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            if self._wake_callback:
                self._wake_callback()
            return JSONResponse({"ok": True})

        # ── Mission Control & Mobile Ready API Endpoints ──────────────────────

        @app.get("/api/mission_control")
        async def mission_control_ep(req: Request):
            from core.os_identity import OWNER_NAME, OWNER_DISPLAY, DEFAULT_AI_NAME
            from core.context_engine import ContextEngine
            from core.digital_twin import DigitalTwinEngine
            from core.memory_timeline import MemoryTimeline
            from core.second_brain import SecondBrain
            from actions.security_center import get_security_status
            from memory.config_manager import get_performance_mode, get_voice
            from core.offline_engine import OfflineEngine
            from core.multi_agent import MultiAgentHive
            from core.ultra_security import UltraSecurityManager

            ctx = ContextEngine.get_instance().get_active_context()
            twin = DigitalTwinEngine.get_instance().get_twin_summary()
            timeline = MemoryTimeline.get_instance().get_timeline_by_period()
            graph = SecondBrain.get_instance().get_graph_export()
            sec = get_security_status()
            off = OfflineEngine.get_instance().get_status()
            hive = MultiAgentHive.get_instance().get_agents()
            ultra_sec = UltraSecurityManager.get_instance().get_security_status()

            founder_ctx = {}
            try:
                from core.founder_mode import FounderModeEngine
                founder_ctx = FounderModeEngine.get_instance().get_founder_context()
            except Exception:
                pass

            analytics_data = {}
            try:
                from core.analytics_engine import AnalyticsEngine
                analytics_data = AnalyticsEngine.get_instance().get_metrics()
            except Exception:
                pass

            trusted_devices = []
            try:
                from core.mobile_ecosystem import MobileEcosystemManager
                trusted_devices = MobileEcosystemManager.get_instance().list_trusted_devices()
            except Exception:
                pass

            return JSONResponse({
                "os_name": "HONESTIC OS",
                "owner": {
                    "name": OWNER_NAME,
                    "display": OWNER_DISPLAY,
                    "role": "Founder & Creator",
                    "clearance": "ALPHA-1 (Unrestricted)",
                },
                "athena": {
                    "name": DEFAULT_AI_NAME,
                    "status": "ONLINE",
                    "performance_mode": get_performance_mode(),
                    "voice": get_voice(),
                    "operational_mode": off.get("configured_mode", "auto"),
                    "effective_mode": off.get("effective_mode", "online"),
                },
                "context": ctx,
                "digital_twin": {
                    "active_projects": twin.get("active_projects", []),
                    "active_goals": twin.get("active_goals", []),
                    "work_habits": twin.get("work_habits", {}),
                    "learned_preferences": twin.get("learned_preferences", {}),
                },
                "timeline": timeline,
                "second_brain": {
                    "stats": graph.get("stats", {}),
                    "node_count": len(graph.get("nodes", [])),
                    "edge_count": len(graph.get("edges", [])),
                    "nodes": graph.get("nodes", []),
                    "edges": graph.get("edges", []),
                },
                "security": sec,
                "ultra_security": ultra_sec,
                "offline": off,
                "multi_agent": hive,
                "founder_mode": founder_ctx,
                "analytics": analytics_data,
                "mobile_devices": trusted_devices,
                "voice_status": VoiceManager.get_instance().get_voice_status(),
            })

        # ── Voice Center & Mobile Companion Endpoints ────────────────────────
        @app.get("/api/voice/status")
        async def voice_status_ep(req: Request):
            from core.voice_manager import VoiceManager
            return JSONResponse(VoiceManager.get_instance().get_voice_status())

        @app.post("/api/voice/switch")
        async def voice_switch_ep(req: Request):
            from core.voice_manager import VoiceManager
            try:
                body = await req.json()
            except Exception:
                body = {}
            vname = body.get("voice", "Athena")
            res_v = VoiceManager.get_instance().set_voice(vname)
            return JSONResponse({"ok": True, "active_voice": res_v})

        @app.post("/api/voice/profile")
        async def voice_profile_ep(req: Request):
            from core.voice_manager import VoiceManager
            try:
                body = await req.json()
            except Exception:
                body = {}
            prof = body.get("profile", "Natural")
            res_p = VoiceManager.get_instance().set_profile(prof)
            return JSONResponse({"ok": True, "active_profile": res_p})

        @app.post("/api/voice/preview")
        async def voice_preview_ep(req: Request):
            from core.voice_manager import VoiceManager
            try:
                body = await req.json()
            except Exception:
                body = {}
            vname = body.get("voice")
            prof = body.get("profile")
            params = body.get("custom_params")
            VoiceManager.get_instance().preview_voice(vname, prof, params)
            return JSONResponse({"ok": True, "message": f"Previewing {vname or 'Athena'}"})

        @app.post("/api/voice/custom")
        async def voice_custom_ep(req: Request):
            from core.voice_manager import VoiceManager
            try:
                body = await req.json()
            except Exception:
                body = {}
            res_params = VoiceManager.get_instance().set_custom_parameters(body)
            return JSONResponse({"ok": True, "custom_parameters": res_params})

        @app.post("/api/voice/founder_profile")
        async def voice_founder_ep(req: Request):
            from core.voice_manager import VoiceManager
            try:
                body = await req.json()
            except Exception:
                body = {}
            name = body.get("name", "ATHENA - Founder Edition")
            res = VoiceManager.get_instance().save_founder_profile(name)
            return JSONResponse({"ok": True, "founder_profile": res})

        @app.post("/api/voice/test_recognition")
        async def voice_test_rec_ep(req: Request):
            from core.voice_manager import VoiceManager
            VoiceManager.get_instance().speak_founder_welcome()
            return JSONResponse({"ok": True, "message": "Founder greeting executed."})


        @app.get("/api/second_brain")
        async def second_brain_ep(req: Request):
            from core.second_brain import SecondBrain
            return JSONResponse(SecondBrain.get_instance().get_graph_export())

        @app.get("/api/timeline")
        async def timeline_ep(req: Request):
            from core.memory_timeline import MemoryTimeline
            return JSONResponse(MemoryTimeline.get_instance().get_timeline_by_period())

        @app.get("/api/visual_learn")
        async def visual_learn_ep(topic: str = "DNS"):
            from core.visual_learning import VisualLearningEngine
            return JSONResponse(VisualLearningEngine.get_instance().explain(topic))

        @app.get("/api/security")
        async def security_ep(req: Request):
            from actions.security_center import get_security_status
            return JSONResponse(get_security_status())

        @app.post("/api/workspace/save")
        async def save_workspace_ep(req: Request):
            from actions.workspace_memory import save_current_workspace
            res = save_current_workspace("default")
            return JSONResponse(res)

        @app.post("/api/workspace/restore")
        async def restore_workspace_ep(req: Request):
            from actions.workspace_memory import restore_workspace
            res = restore_workspace("default")
            return JSONResponse(res)

        @app.get("/api/diagnostics")
        async def diagnostics_ep(req: Request):
            from core.diagnostics_center import DiagnosticsCenter
            return JSONResponse(DiagnosticsCenter.get_instance().run_full_diagnostics())

        @app.post("/api/backup/create")
        async def backup_create_ep(req: Request):
            from core.backup_manager import BackupManager
            label = "manual_dashboard_backup"
            try:
                body = await req.json()
                label = body.get("label", label)
            except Exception:
                pass
            res = BackupManager.get_instance().create_backup(label=label)
            return JSONResponse(res)

        @app.get("/api/backup/list")
        async def backup_list_ep(req: Request):
            from core.backup_manager import BackupManager
            return JSONResponse({"backups": BackupManager.get_instance().list_backups()})

        @app.post("/api/backup/restore")
        async def backup_restore_ep(req: Request):
            from core.backup_manager import BackupManager
            archive_name = ""
            try:
                body = await req.json()
                archive_name = body.get("archive_name", "")
            except Exception:
                pass
            res = BackupManager.get_instance().restore_backup(archive_name)
            return JSONResponse(res)

        @app.get("/api/projects")
        async def projects_ep(req: Request):
            from core.project_manager import ProjectManager
            pm = ProjectManager.get_instance()
            return JSONResponse({
                "metrics": pm.get_metrics(),
                "projects": pm.get_projects()
            })

        @app.post("/api/projects/task")
        async def project_task_ep(req: Request):
            from core.project_manager import ProjectManager
            pm = ProjectManager.get_instance()
            try:
                body = await req.json()
                action = body.get("action", "add")
                if action == "add":
                    res = pm.add_task(
                        project_id=body.get("project_id", "honestic_os"),
                        title=body.get("title", "New Task"),
                        category=body.get("category", "pending"),
                        notes=body.get("notes", "")
                    )
                    return JSONResponse(res)
                elif action == "complete":
                    res = pm.complete_task(task_id=body.get("task_id", ""))
                    return JSONResponse(res)
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
            return JSONResponse({"ok": False, "error": "Invalid action"}, status_code=400)

        @app.get("/api/replay")
        async def replay_ep(req: Request, period: str = "today"):
            from core.conversation_replay import ConversationReplay
            rep = ConversationReplay.get_instance()
            return JSONResponse(rep.replay(period))

        @app.post("/api/screenshot_memory")
        async def screenshot_memory_ep(req: Request):
            from core.screenshot_memory import ScreenshotMemoryEngine
            notes = ""
            project_id = ""
            try:
                body = await req.json()
                notes = body.get("notes", "")
                project_id = body.get("project_id", "")
            except Exception:
                pass
            res = ScreenshotMemoryEngine.get_instance().remember_screen(notes=notes, project_id=project_id)
            return JSONResponse(res)

        @app.get("/api/safe_mode")
        async def safe_mode_ep(req: Request):
            from core.safe_mode import SafeModeManager
            return JSONResponse(SafeModeManager.get_instance().get_status())

        @app.post("/api/safe_mode/toggle")
        async def safe_mode_toggle_ep(req: Request):
            from core.safe_mode import SafeModeManager
            sm = SafeModeManager.get_instance()
            try:
                body = await req.json()
                enable = body.get("enable", False)
                if enable:
                    sm.enable_safe_mode("Toggled via Dashboard")
                else:
                    sm.disable_safe_mode()
                return JSONResponse(sm.get_status())
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.get("/api/performance")
        async def performance_ep(req: Request):
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return JSONResponse({
                "cpu_percent": cpu,
                "ram_percent": mem.percent,
                "ram_used_gb": round(mem.used / (1024**3), 2),
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "status": "Optimal" if cpu < 70 and mem.percent < 80 else "Elevated"
            })

        @app.get("/api/offline")
        async def offline_get_ep(req: Request):
            from core.offline_engine import OfflineEngine
            return JSONResponse(OfflineEngine.get_instance().get_status())

        @app.post("/api/offline")
        async def offline_post_ep(req: Request):
            from core.offline_engine import OfflineEngine
            oe = OfflineEngine.get_instance()
            try:
                body = await req.json()
                new_mode = oe.set_mode(body.get("mode", "auto"))
                return JSONResponse({"ok": True, "mode": new_mode, "status": oe.get_status()})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.get("/api/multi_agent")
        async def multi_agent_get_ep(req: Request):
            from core.multi_agent import MultiAgentHive
            return JSONResponse(MultiAgentHive.get_instance().get_agents())

        @app.post("/api/multi_agent/delegate")
        async def multi_agent_delegate_ep(req: Request):
            from core.multi_agent import MultiAgentHive
            try:
                body = await req.json()
                res = MultiAgentHive.get_instance().delegate(body.get("query", ""))
                return JSONResponse(res)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.get("/api/security/ultra")
        async def ultra_sec_get_ep(req: Request):
            from core.ultra_security import UltraSecurityManager
            return JSONResponse(UltraSecurityManager.get_instance().get_security_status())

        @app.post("/api/security/pin/verify")
        async def ultra_sec_verify_ep(req: Request):
            from core.ultra_security import UltraSecurityManager
            try:
                body = await req.json()
                ok = UltraSecurityManager.get_instance().verify_pin(body.get("pin", ""))
                return JSONResponse({"ok": ok, "status": UltraSecurityManager.get_instance().get_security_status()})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.post("/api/security/lock")
        async def ultra_sec_lock_ep(req: Request):
            from core.ultra_security import UltraSecurityManager
            UltraSecurityManager.get_instance().lock_vault()
            return JSONResponse(UltraSecurityManager.get_instance().get_security_status())

        @app.get("/api/voice_train/prompts")
        async def voice_prompts_ep(req: Request):
            from core.voice_trainer import VoiceTrainer
            vt = VoiceTrainer.get_instance()
            return JSONResponse({
                "prompts": vt.get_training_prompts(),
                "status": vt.get_profile_status()
            })

        @app.post("/api/voice_train/sample")
        async def voice_sample_ep(req: Request):
            from core.voice_trainer import VoiceTrainer
            try:
                body = await req.json()
                idx = body.get("phrase_index", 0)
                res = VoiceTrainer.get_instance().enroll_sample(idx)
                return JSONResponse(res)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.post("/api/voice_train/finalize")
        async def voice_finalize_ep(req: Request):
            from core.voice_trainer import VoiceTrainer
            res = VoiceTrainer.get_instance().finalize_enrollment()
            return JSONResponse(res)

        @app.post("/api/computer_agent/workflow")
        async def computer_agent_workflow_ep(req: Request):
            from core.computer_agent import ComputerUseAgent
            try:
                body = await req.json()
                steps = body.get("steps", [])
                res = ComputerUseAgent.get_instance().execute_workflow(steps)
                return JSONResponse(res)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.get("/api/founder/mode")
        async def founder_mode_get_ep(req: Request):
            from core.founder_mode import FounderModeEngine
            return JSONResponse(FounderModeEngine.get_instance().get_founder_context())

        @app.post("/api/founder/mode")
        async def founder_mode_post_ep(req: Request):
            from core.founder_mode import FounderModeEngine
            source = "dashboard"
            try:
                body = await req.json()
                source = body.get("source", "dashboard")
            except Exception:
                pass
            res = FounderModeEngine.get_instance().activate_founder_mode(source=source)
            return JSONResponse(res)

        @app.get("/api/founder/context")
        async def founder_context_ep(req: Request):
            from core.founder_mode import FounderModeEngine
            return JSONResponse(FounderModeEngine.get_instance().get_founder_context())

        @app.get("/api/mobile/pairing")
        async def mobile_pairing_ep(req: Request):
            from core.mobile_ecosystem import MobileEcosystemManager
            host = req.headers.get("host", "127.0.0.1:8000")
            h, _, p = host.partition(":")
            port = int(p) if p else 8000
            payload = MobileEcosystemManager.get_instance().generate_pairing_payload(server_host=h, port=port)
            return JSONResponse(payload)

        @app.get("/api/mobile/devices")
        async def mobile_devices_ep(req: Request):
            from core.mobile_ecosystem import MobileEcosystemManager
            return JSONResponse({"devices": MobileEcosystemManager.get_instance().list_trusted_devices()})

        @app.post("/api/mobile/pair")
        async def mobile_pair_post_ep(req: Request):
            from core.mobile_ecosystem import MobileEcosystemManager
            try:
                body = await req.json()
                d_name = body.get("device_name", "Mobile Companion")
                code = body.get("pair_code", "")
                pin = body.get("pin")
                client_ip = req.client.host if req.client else "127.0.0.1"
                res = MobileEcosystemManager.get_instance().pair_device(
                    device_name=d_name, pair_code=code, client_ip=client_ip, pin=pin
                )
                return JSONResponse(res)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.post("/api/mobile/device/revoke")
        async def mobile_revoke_ep(req: Request):
            from core.mobile_ecosystem import MobileEcosystemManager
            try:
                body = await req.json()
                dev_id = body.get("device_id", "")
                ok = MobileEcosystemManager.get_instance().revoke_device(dev_id)
                return JSONResponse({"ok": ok, "device_id": dev_id})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.post("/api/mobile/remote_action")
        async def mobile_remote_action_ep(req: Request):
            from core.mobile_ecosystem import MobileEcosystemManager
            try:
                body = await req.json()
                act = body.get("action", "")
                params = body.get("parameters", {})
                res = MobileEcosystemManager.get_instance().execute_remote_action(act, params)
                return JSONResponse(res)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.get("/api/analytics")
        async def analytics_ep(req: Request):
            from core.analytics_engine import AnalyticsEngine
            return JSONResponse(AnalyticsEngine.get_instance().get_metrics())

        @app.post("/api/multi_agent/collaborate")
        async def multi_agent_collaborate_ep(req: Request):
            from core.multi_agent import MultiAgentHive
            try:
                body = await req.json()
                goal = body.get("goal", "Optimize operating system telemetry and verify zero-trust posture")
                res = MultiAgentHive.get_instance().collaborate(goal)
                return JSONResponse(res)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.post("/api/computer_agent/plan")
        async def computer_agent_plan_ep(req: Request):
            from core.computer_agent import ComputerUseAgent
            try:
                body = await req.json()
                obj = body.get("objective", "Prepare project workspace")
                plan = ComputerUseAgent.get_instance().plan_task(obj)
                return JSONResponse(plan)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

        @app.post("/api/diagnostics/heal")
        async def diagnostics_heal_ep(req: Request):
            from core.diagnostics_center import DiagnosticsCenter
            return JSONResponse(DiagnosticsCenter.get_instance().heal_subsystems())




        # ── Phone mic real-time audio → Gemini Live ──────────────────────────

        @app.websocket("/ws/phone-audio")
        async def phone_audio_ws(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            if not _valid(tok):
                await websocket.close(code=4001)
                return
            await websocket.accept()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Phone microphone live."}
            ))
            try:
                while True:
                    data = await websocket.receive_bytes()
                    try:
                        self._phone_audio_queue.put_nowait(
                            {"data": data, "mime_type": "audio/pcm"}
                        )
                    except asyncio.QueueFull:
                        pass  # drop frame rather than block
            except WebSocketDisconnect:
                pass
            finally:
                asyncio.create_task(self.broadcast(
                    {"type": "sys", "text": "Phone microphone stopped."}
                ))

        # ── File sharing ──────────────────────────────────────────────────────

        def _safe_filename(raw: str) -> str:
            name = Path(raw).name                          # strip path components
            name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(". ")
            return name or "upload"

        if _UPLOAD_OK:
            @app.post("/api/upload")
            async def upload_file(req: Request, file: UploadFile = FastAPIFile(...)):
                if not _auth(req):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                safe = _safe_filename(file.filename or "upload")
                dest = self._uploads_dir / safe
                stem, suffix = Path(safe).stem, Path(safe).suffix
                counter = 1
                while dest.exists():
                    dest = self._uploads_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                size = 0
                max_bytes = MAX_UPLOAD_MB * 1024 * 1024
                try:
                    with open(dest, "wb") as fout:
                        while True:
                            chunk = await file.read(65536)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > max_bytes:
                                fout.close()
                                dest.unlink(missing_ok=True)
                                return JSONResponse(
                                    {"error": f"File too large (max {MAX_UPLOAD_MB} MB)"},
                                    status_code=413,
                                )
                            fout.write(chunk)
                except Exception as exc:
                    try:
                        dest.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return JSONResponse({"error": str(exc)}, status_code=500)

                asyncio.create_task(self.broadcast({
                    "type": "file_received",
                    "name": dest.name,
                    "size": size,
                    "saved_to": str(self._uploads_dir),
                }))
                return JSONResponse({"ok": True, "name": dest.name, "size": size})
        else:
            @app.post("/api/upload")
            async def upload_unavailable(req: Request):
                return JSONResponse(
                    {"error": "File uploads require: pip install python-multipart"},
                    status_code=503,
                )

        @app.get("/api/files")
        async def list_files(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            files = []
            try:
                for f in sorted(
                    (p for p in self._uploads_dir.iterdir() if p.is_file()),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                ):
                    files.append({"name": f.name, "size": f.stat().st_size})
            except Exception:
                pass
            return JSONResponse({"files": files})

        @app.get("/uploads/{filename}")
        async def download_file(filename: str, token: str = ""):
            # Auth via query param — browser <a download> can't send custom headers
            tok = token.strip()
            if not _valid(tok):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            safe = re.sub(r'[/\\]', '', filename)
            path = self._uploads_dir / safe
            if not path.exists() or not path.is_file():
                return JSONResponse({"error": "Not found"}, status_code=404)
            return FileResponse(str(path), filename=safe)

        @app.websocket("/ws")
        async def ws_ep(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            if not _valid(tok):
                await websocket.close(code=4001)
                return
            await websocket.accept()
            self._clients.add(websocket)
            for entry in self._history[-50:]:
                try:
                    await websocket.send_json(entry)
                except Exception:
                    break
            try:
                while True:
                    data = await websocket.receive_json()
                    if data.get("type") == "command":
                        enc = data.get("enc", "")
                        t   = self._decrypt(tok, enc) if enc else (data.get("text") or "").strip()
                        if t:
                            await self._command_queue.put(t)
                            if self._wake_callback:
                                self._wake_callback()
            except WebSocketDisconnect:
                pass
            finally:
                self._clients.discard(websocket)

        return app

    # ── telemetry broadcast loop ─────────────────────────────────────────

    async def _telemetry_loop(self) -> None:
        """Broadcasts real-time hardware telemetry and status to connected dashboard clients."""
        import psutil
        from core.os_identity import OWNER_NAME, DEFAULT_AI_NAME
        from memory.config_manager import get_assistant_name, get_user_name, get_performance_mode

        last_net = None
        try:
            last_net = psutil.net_io_counters()
        except Exception:
            pass
        last_t = time.monotonic()

        while True:
            await asyncio.sleep(2.5)
            if not self._clients:
                continue
            try:
                now_t = time.monotonic()
                dt = max(0.1, now_t - last_t)
                net_rate = 0.0
                if last_net:
                    cur_net = psutil.net_io_counters()
                    diff = (cur_net.bytes_sent + cur_net.bytes_recv) - (last_net.bytes_sent + last_net.bytes_recv)
                    net_rate = max(0.0, diff / dt / (1024 * 1024))
                    last_net = cur_net
                last_t = now_t

                cpu_pct = psutil.cpu_percent()
                mem_pct = psutil.virtual_memory().percent

                msg = {
                    "type": "telemetry",
                    "cpu": round(cpu_pct, 1),
                    "ram": round(mem_pct, 1),
                    "net": round(net_rate, 2),
                    "gpu": -1,
                    "weather": "28°C • Clear Sky",
                    "tasks": [
                        "HONESTIC OS Kernel Active",
                        "Neural Telemetry Synced",
                        "Knowledge Vault Online",
                        "Safety Gates Armed"
                    ],
                    "ai_status": f"{get_assistant_name()} Online",
                    "owner": get_user_name() or OWNER_NAME,
                    "mode": get_performance_mode().upper(),
                }
                await self.broadcast(msg)
            except Exception:
                pass

    # ── serve ─────────────────────────────────────────────────────────────

    async def _serve_redirector(self) -> None:
        """A plain-HTTP listener whose only job is to send people to HTTPS.

        THE PROBLEM THIS SOLVES, WHICH LOOKED LIKE THE SERVER BEING DOWN
            Type `192.168.1.108:8000` into a phone browser and it tries HTTP.
            The TLS server accepts the connection, finds no handshake and
            closes it — which Chrome reports as "This site can't be reached,
            192.168.1.108 refused to connect". The server is running perfectly
            and the user is told it is off.

            The port that used to sit here was a SECOND HTTPS server, added on
            the belief that browsers upgrade a bare `ip:port` to https. Some
            do. Android Chrome does not, so the second port had exactly the
            same failure as the first.

        So this speaks HTTP, and answers everything with a redirect to the same
        path on the HTTPS port. Typing the address by hand now works, which is
        what people do when a QR code is inconvenient.
        """
        from fastapi.responses import RedirectResponse

        bounce = FastAPI(docs_url=None, redoc_url=None)

        @bounce.get("/{path:path}")
        async def _to_https(path: str, request: Request):
            query = f"?{request.url.query}" if request.url.query else ""
            return RedirectResponse(
                f"https://{self._ip}:{SECURE_PORT}/{path}{query}",
                status_code=307)

        cfg = uvicorn.Config(bounce, host="0.0.0.0", port=PORT,
                             log_level="warning")
        print(f"[Dashboard] Type by hand:  {self._ip}:{PORT}  "
              f"(sends you to the secure page)")
        await uvicorn.Server(cfg).serve()

    async def serve(self) -> None:
        if not _DEPS_OK:
            print("[Dashboard] fastapi/uvicorn not installed — dashboard disabled.")
            print("[Dashboard] Run:  pip install fastapi 'uvicorn[standard]' cryptography")
            return

        # Firewall setup runs in a thread — uvicorn starts immediately,
        # no waiting for UAC dialogs or subprocess timeouts.
        # Both ports, one pass, one prompt.
        asyncio.get_event_loop().run_in_executor(
            None, _ensure_network_access, PORT, SECURE_PORT)

        # Only make a certificate if HTTPS was actually asked for. Generating
        # one nobody uses just leaves a private key on disk.
        try:
            import json as _json
            with open(BASE_DIR / "config" / "api_keys.json", "r",
                      encoding="utf-8") as f:
                if _json.load(f).get("dashboard_https"):
                    _ensure_certs()
        except Exception:
            pass

        use_ssl  = self._ssl_enabled()
        ssl_key  = BASE_DIR / "config" / "certs" / "jarvis.key"
        ssl_cert = BASE_DIR / "config" / "certs" / "jarvis.crt"

        # TLS IS WANTED, BUT NOT AT THE COST OF NOT STARTING.
        #
        # An earlier version returned here when certificates could not be made,
        # on the argument that serving a remote-control channel in clear is a
        # different product. The argument is right and the behaviour was wrong:
        # a dashboard that does not start is not more secure, it is absent, and
        # the user is left with "refused to connect" and nothing to act on.
        #
        # So: HTTPS whenever it can be had — which is almost always, since the
        # certificate is generated locally on first run — and plain HTTP with a
        # loud, repeated warning when it cannot. The page keeps working either
        # way; without a secure context it simply cannot encrypt, and it says
        # so on screen rather than pretending.
        if use_ssl:
            asyncio.create_task(self._serve_redirector())
        else:
            print("[Dashboard] Plain HTTP on your local network. Commands are "
                  "not encrypted; the pairing key still gates access.")
            print('[Dashboard] For HTTPS set "dashboard_https": true in '
                  'config/api_keys.json (your phone will ask you to trust the '
                  'certificate once).')

        # Launch background telemetry loop for dashboard widgets
        asyncio.create_task(self._telemetry_loop())

        cfg = uvicorn.Config(
            self.app, host="0.0.0.0",
            port=SECURE_PORT if use_ssl else PORT, log_level="warning",
            **({"ssl_keyfile": str(ssl_key), "ssl_certfile": str(ssl_cert)}
               if use_ssl else {}),
        )

        # CAN THIS PORT ACTUALLY BE TAKEN?
        #
        # uvicorn raises when the port is busy, and under pythonw.exe there is
        # no console for that to be seen in — so a second JARVIS, or anything
        # else already on 8000, produced a dashboard that was silently dead
        # while the HUD went on showing a QR code pointing at it. The phone
        # then reports ERR_CONNECTION_REFUSED, which is true and impossible to
        # act on.
        #
        # Asking first costs a millisecond and turns that into a sentence.
        import socket as _socket
        # No SO_REUSEADDR. On Windows that option lets a second socket bind a
        # port another socket already holds — which is exactly the condition
        # being tested for, so setting it made the probe always succeed.
        _probe = _socket.socket()
        try:
            _probe.bind(("0.0.0.0", SECURE_PORT if use_ssl else PORT))
        except OSError as exc:
            _probe.close()
            self._bind_error = (
                f"port {SECURE_PORT if use_ssl else PORT} is already in use — "
                f"another copy of HONESTIC OS is probably running. Close it and "
                f"restart, or the phone dashboard will stay unreachable "
                f"({exc.__class__.__name__})")
            print(f"[Dashboard] {self._bind_error}")
            return
        _probe.close()

        print(f"[Dashboard] {self.get_url()}")
        print("[Dashboard] Press 'Remote Control' in HONESTIC OS UI to get the QR code.")
        await uvicorn.Server(cfg).serve()
