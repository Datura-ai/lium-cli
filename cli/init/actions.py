"""Actions for init command."""

import subprocess
from pathlib import Path

from .auth import browser_auth
from cli.settings import config


class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class SetupApiKeyAction:
    """Setup API key using browser authentication."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute API key setup."""
        current_key = config.get('api.api_key')
        if current_key:
            return ActionResult(ok=True, data={"already_configured": True})

        api_key = browser_auth()

        if not api_key:
            return ActionResult(ok=False, error="Authentication failed")

        config.set('api.api_key', api_key)
        return ActionResult(ok=True, data={"already_configured": False})


class SetupSshKeyAction:
    """Setup SSH key path in config."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute SSH key setup."""
        if config.get('ssh.key_path'):
            return ActionResult(ok=True, data={"already_configured": True})

        ssh_dir = Path.home() / ".ssh"
        available_keys = [
            ssh_dir / key_name
            for key_name in ["id_ed25519", "id_rsa", "id_ecdsa"]
            if (ssh_dir / key_name).exists()
        ]

        if not available_keys:
            key_path = ssh_dir / "id_ed25519"
            try:
                subprocess.run(
                    ["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", "", "-q"],
                    check=True, capture_output=True
                )
                selected_key = key_path
            except Exception as e:
                return ActionResult(ok=False, error=f"Failed to generate SSH key: {e}")
        else:
            selected_key = available_keys[0]

        config.set('ssh.key_path', str(selected_key))
        return ActionResult(ok=True, data={"already_configured": False})
