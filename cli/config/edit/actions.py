"""Actions for config edit command."""

import os
import sys
import subprocess

from cli.config import config


class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class EditConfigAction:
    """Edit config file."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config edit."""
        config_file = config.get_config_path()
        editor = os.environ.get('EDITOR', 'nano' if sys.platform != 'win32' else 'notepad')

        try:
            subprocess.run([editor, str(config_file)], check=True)
            return ActionResult(ok=True)
        except subprocess.CalledProcessError:
            return ActionResult(ok=False, error=f"Failed to open editor: {editor}")
        except FileNotFoundError:
            return ActionResult(ok=False, error=f"Editor not found: {editor}")
