import os
import json
from pathlib import Path
from typing import Dict, List, Literal
from rich.console import Console
from rich.theme import Theme

ThemeName = Literal["default_dark", "default_light"]

DEFAULT_THEME: ThemeName = "default_dark"
CELIUM_CONFIG_DIR = Path(os.path.expanduser("~/.celium"))
THEME_CONFIG_FILE = CELIUM_CONFIG_DIR / "theme.json"

# Define basic style keys that can be themed
# Values are Rich style strings
BASE_STYLES: Dict[str, str] = {
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "key": "bold blue",
    "value": "magenta",
    "title": "bold magenta",
    "header": "bold white on blue",
    "dim": "dim",
    "primary": "blue",
    # Pod/Executor specific styles (examples)
    "executor.gpu": "cyan",
    "executor.price": "green",
    "executor.location": "blue",
    "status.running": "green",
    "status.pending": "yellow",
    "status.failed": "red",
}

THEMES: Dict[ThemeName, Dict[str, str]] = {
    "default_dark": {
        **BASE_STYLES,
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "key": "bold bright_blue",
        "value": "bright_magenta",
        "title": "bold magenta",
        "header": "bold white on blue",
        "dim": "dim grey50",
    },
    "default_light": {
        **BASE_STYLES,
        "info": "dark_cyan",
        "warning": "orange3",
        "error": "bold red",
        "success": "bold green",
        "key": "bold blue",
        "value": "magenta",
        "title": "bold dark_magenta",
        "header": "bold black on bright_cyan",
        "dim": "grey70",
        "executor.gpu": "dark_cyan",
        "executor.price": "dark_green",
        "status.running": "dark_green",
        "status.pending": "orange3",
    }
}

class StyleManager:
    def __init__(self):
        self._current_theme_name: ThemeName = DEFAULT_THEME
        self._load_theme_preference()
        self.current_styles: Dict[str, str] = THEMES.get(self._current_theme_name, THEMES[DEFAULT_THEME])
        self.console = Console(theme=Theme(self.current_styles))

    def _load_theme_preference(self):
        CELIUM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if THEME_CONFIG_FILE.exists():
            try:
                with open(THEME_CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    theme_name = data.get("theme")
                    if theme_name in THEMES:
                        self._current_theme_name = theme_name
            except (json.JSONDecodeError, OSError):
                # Invalid file, use default and overwrite later if theme is switched
                pass 

    def _save_theme_preference(self):
        CELIUM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(THEME_CONFIG_FILE, "w") as f:
                json.dump({"theme": self._current_theme_name}, f)
        except OSError:
            # Failed to save, not critical but should be logged if proper logging is set up
            pass

    def switch_theme(self, theme_name: ThemeName):
        if theme_name not in THEMES:
            raise ValueError(f"Theme '{theme_name}' not recognized.")
        self._current_theme_name = theme_name
        self.current_styles = THEMES[self._current_theme_name]
        self._save_theme_preference()
        self.console = Console(theme=Theme(self.current_styles))
        # Update the global console instance that other modules might have imported by reference
        # This is a bit of a workaround for modules that might have imported console directly.
        # Better practice is for them to call a get_console() func or use style_manager.console.
        # global console # Removed
        # console = self.console # Removed

    def get_available_themes(self) -> List[ThemeName]:
        return list(THEMES.keys())

    def get_style(self, style_key: str) -> str:
        return self.current_styles.get(style_key, "") # Return empty string if key not found

# Global style manager instance
style_manager = StyleManager()

# Global theme-aware console instance that modules can import
# This console will be updated by style_manager.switch_theme()
# To ensure modules use the updated console, they should ideally get it at runtime, 
# or style_manager needs to update this specific instance.
# The current StyleManager.__init__ and switch_theme re-initializes its own self.console.
# So, other modules should import 'console' from this module after it's defined.

def get_styled_text(text: str, style_key: str) -> str:
    """Applies a style from the current theme to the given text using Rich markup."""
    style_value = style_manager.get_style(style_key)
    if style_value:
        return f"[{style_value}]{text}[/{style_value}]"
    return text # Return text as is if style_key or style_value is not found/empty

# The primary console for the application
# console: Console = style_manager.console # Removed 