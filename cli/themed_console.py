"""Themed console with automatic dark/light detection."""

import json
import os
import configparser
from pathlib import Path
from typing import Dict, Any
from rich.console import Console as RichConsole


class ThemedConsole(RichConsole):
    """Console with theme support and semantic color methods."""
    
    def __init__(self):
        super().__init__()
        self.themes = self._load_themes()
        self.current_theme_name = self._get_theme_from_config()
        self.theme = self._resolve_theme()
    
    def _load_themes(self) -> Dict[str, Dict[str, str]]:
        """Load themes from themes.json."""
        themes_file = Path(__file__).parent / "themes.json"
        try:
            with open(themes_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to basic themes
            return {
                "dark": {"success": "green", "error": "red", "warning": "yellow", "info": "cyan", "dim": "dim"},
                "light": {"success": "green", "error": "red", "warning": "yellow", "info": "blue", "dim": "dim"}
            }
    
    def _get_theme_from_config(self) -> str:
        """Get theme from config, default to auto."""
        config_file = Path.home() / ".lium" / "config.ini"
        if not config_file.exists():
            return "auto"
        
        config = configparser.ConfigParser()
        try:
            config.read(config_file)
            return config.get('ui', 'theme', fallback='auto')
        except (configparser.Error, KeyError):
            return "auto"
    
    def _resolve_theme(self) -> Dict[str, str]:
        """Resolve theme name to actual theme dict."""
        if self.current_theme_name == "auto":
            detected = "dark" if self._is_dark_terminal() else "light"
            return self.themes.get(detected, self.themes["dark"])
        return self.themes.get(self.current_theme_name, self.themes["dark"])
    
    def _is_dark_terminal(self) -> bool:
        """Detect if terminal has dark background."""
        import platform
        import subprocess
        
        # Try macOS system theme detection first
        if platform.system() == 'Darwin':
            try:
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                # If AppleInterfaceStyle exists and equals "Dark", it's dark mode
                if result.returncode == 0 and result.stdout.strip() == "Dark":
                    return True
                elif result.returncode != 0:
                    # Key doesn't exist = light mode
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                # Fall through to other detection methods
                pass
        
        # Check COLORFGBG environment variable (works in some terminals)
        colorfgbg = os.environ.get('COLORFGBG', '')
        if colorfgbg and ';' in colorfgbg:
            try:
                bg = colorfgbg.split(';')[-1]
                if bg.isdigit():
                    # Background colors 0-7 are typically dark
                    return int(bg) <= 7
            except (ValueError, IndexError):
                pass
        
        # Check for dark mode hints in environment
        if os.environ.get('THEME', '').lower() in ['dark', 'dracula', 'monokai', 'nord']:
            return True
        
        # Default to light for better safety (less eye strain if wrong)
        return False
    
    def _colorized_print(self, text: str, style_key: str) -> None:
        """Print text with color from current theme."""
        styled_text = self.get_styled(text, style_key)
        self.print(styled_text)
    
    def _save_theme_to_config(self, theme_name: str) -> None:
        """Save theme to config file."""
        config_dir = Path.home() / ".lium"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.ini"
        
        config = configparser.ConfigParser()
        if config_file.exists():
            config.read(config_file)
        
        if not config.has_section('ui'):
            config.add_section('ui')
        config.set('ui', 'theme', theme_name)
        
        with open(config_file, 'w') as f:
            config.write(f)
    
    # Semantic color methods
    def success(self, text: str) -> None:
        """Print success message."""
        self._colorized_print(text, 'success')
    
    def error(self, text: str) -> None:
        """Print error message."""
        self._colorized_print(text, 'error')
    
    def warning(self, text: str) -> None:
        """Print warning message."""
        self._colorized_print(text, 'warning')
    
    def info(self, text: str) -> None:
        """Print info message."""
        self._colorized_print(text, 'info')
    
    def pending(self, text: str) -> None:
        """Print pending status message."""
        self._colorized_print(text, 'pending')
    
    def dim(self, text: str) -> None:
        """Print dimmed text."""
        self._colorized_print(text, 'dim')
    
    def pod_status_color(self, status: str) -> str:
        """Get color for pod status."""
        status_key = status.lower()
        return self.theme.get(status_key, self.theme.get('dim', 'dim'))
    
    def get_styled(self, text: str, style_key: str) -> str:
        """Get styled text without printing."""
        color = self.theme.get(style_key, self.theme.get('dim', 'dim'))
        return f"[{color}]{text}[/{color}]"
    
    def switch_theme(self, theme_name: str) -> None:
        """Switch to a different theme and save to config."""
        if theme_name not in ['auto', 'dark', 'light']:
            raise ValueError(f"Unknown theme: {theme_name}")
        
        self.current_theme_name = theme_name
        self.theme = self._resolve_theme()
        self._save_theme_to_config(theme_name)
    
    def get_current_theme_name(self) -> str:
        """Get current theme name."""
        return self.current_theme_name
    
    def get_resolved_theme_name(self) -> str:
        """Get the actual resolved theme name (useful for 'auto' mode)."""
        if self.current_theme_name == "auto":
            return "dark" if self._is_dark_terminal() else "light"
        return self.current_theme_name
