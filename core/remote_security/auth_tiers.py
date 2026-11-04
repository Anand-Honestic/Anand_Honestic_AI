"""
core/remote_security/auth_tiers.py — Command Authorization Tiers & Whitelisting

Stratifies all cross-device actions into 3 strict tiers:
- Tier 1 (Low): Auto-execute (telemetry, whitelisted app launch, battery query, notification read).
- Tier 2 (Medium): Interactive confirm (send message, settings toggle, file transfer).
- Tier 3 (High): Biometric + double-confirmation (delete data, payment, location stream, terminal shell).
"""

from enum import IntEnum
from typing import Dict, List, Optional, Tuple, Any


class AuthTier(IntEnum):
    TIER_1_LOW = 1
    TIER_2_MEDIUM = 2
    TIER_3_HIGH = 3


# Action to Default Tier Mapping
_ACTION_TIER_MAP: Dict[str, AuthTier] = {
    # Tier 1: Informational / Read-Only / Safe Whitelist Launches
    "GET_BATTERY_STATUS": AuthTier.TIER_1_LOW,
    "GET_DEVICE_INFO": AuthTier.TIER_1_LOW,
    "GET_CLIPBOARD": AuthTier.TIER_1_LOW,
    "SET_CLIPBOARD": AuthTier.TIER_1_LOW,
    "OPEN_APP": AuthTier.TIER_1_LOW,
    "PING": AuthTier.TIER_1_LOW,
    "READ_NOTIFICATION": AuthTier.TIER_1_LOW,

    # Tier 2: State Mutation / Outbound Communication / Settings Toggle
    "SEND_MESSAGE": AuthTier.TIER_2_MEDIUM,
    "AUTOMATE_APP_UI": AuthTier.TIER_2_MEDIUM,
    "TOGGLE_WIFI": AuthTier.TIER_2_MEDIUM,
    "TOGGLE_BLUETOOTH": AuthTier.TIER_2_MEDIUM,
    "FILE_PUSH": AuthTier.TIER_2_MEDIUM,
    "TAKE_PHOTO": AuthTier.TIER_2_MEDIUM,

    # Tier 3: High Impact / Sensitive Data / Financial / System Shell
    "DELETE_FILE": AuthTier.TIER_3_HIGH,
    "WIPE_DATA": AuthTier.TIER_3_HIGH,
    "SHARE_LIVE_LOCATION": AuthTier.TIER_3_HIGH,
    "EXECUTE_SHELL": AuthTier.TIER_3_HIGH,
    "PAYMENT_ACTION": AuthTier.TIER_3_HIGH,
    "KILL_SWITCH": AuthTier.TIER_3_HIGH,
}

# Whitelist of apps permitted for automated UI inspection / clicks on Android
DEFAULT_ALLOWED_PACKAGES: List[str] = [
    "com.whatsapp",
    "com.google.android.apps.messaging",
    "com.google.android.youtube",
    "com.google.android.calculator",
    "com.miui.calculator",
    "com.android.chrome",
]


class CommandAuthorizer:
    """Evaluates whether an incoming cross-device command is permissible and under what auth level."""

    def __init__(self, allowed_packages: Optional[List[str]] = None):
        self.allowed_packages = set(allowed_packages or DEFAULT_ALLOWED_PACKAGES)

    def evaluate_action_tier(self, action_name: str) -> AuthTier:
        """Returns the requisite AuthTier for the specified action."""
        return _ACTION_TIER_MAP.get(action_name.upper(), AuthTier.TIER_3_HIGH)

    def is_package_whitelisted(self, package_name: str) -> bool:
        """Verifies if an Android app package is whitelisted for UI automation."""
        if not package_name:
            return False
        return package_name.lower().strip() in self.allowed_packages

    def validate_command_intent(
        self,
        action_name: str,
        params: Dict[str, Any],
        declared_tier: int,
        has_biometric_proof: bool = False,
        has_user_confirmation: bool = False
    ) -> Tuple[bool, str]:
        """
        Validates whether the command meets all necessary requirements for execution.
        Returns: (allowed: bool, reason: str)
        """
        required_tier = self.evaluate_action_tier(action_name)

        # Check declared tier matches required tier
        if declared_tier < int(required_tier):
            return False, f"Insufficient tier: {action_name} requires Tier {int(required_tier)}, got Tier {declared_tier}"

        # If action controls an app, check app whitelist
        if action_name in ("OPEN_APP", "AUTOMATE_APP_UI"):
            pkg = params.get("package", "")
            if pkg and not self.is_package_whitelisted(pkg):
                return False, f"Package '{pkg}' is not in the approved app whitelist"

        # Tier 3 requires biometric authentication
        if required_tier == AuthTier.TIER_3_HIGH:
            if not has_biometric_proof:
                return False, f"Tier 3 action '{action_name}' requires hardware biometric verification (Fingerprint / Face ID)"

        # Tier 2 requires user confirmation
        if required_tier == AuthTier.TIER_2_MEDIUM:
            if not has_user_confirmation and not has_biometric_proof:
                return False, f"Tier 2 action '{action_name}' requires explicit user confirmation"

        return True, "Authorized"

