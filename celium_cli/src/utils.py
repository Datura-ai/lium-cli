import typer
from rich.console import Console as RichConsole # Keep for type hinting if necessary elsewhere
from rich.text import Text
# from rich.theme import Theme # No longer needed here
# from bittensor_config.config_impl import CONFIG_THEME # No longer needed here

# --- CONSOLE REMOVED --- 
# The global `console` instance previously defined here has been removed.
# Modules that need a console for printing should now import the 
# theme-aware `console` instance from `celium_cli.src.styles`.
# Example: from celium_cli.src.styles import console
# --- END CONSOLE REMOVED ---

# Existing utility functions like pretty_seconds, pretty_minutes, find_machine_from_keyword should remain.
# If they used the old `console`, they would need to be updated to import the new one as shown above.

def pretty_seconds(seconds: int, short: bool = True) -> str:
    if seconds is None:
        return "N/A"
    if seconds < 60:
        return f"{seconds}s" if short else f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m" if short else f"{minutes} minutes"
    else:
        hours = seconds // 3600
        return f"{hours}h" if short else f"{hours} hours"

def pretty_minutes(minutes: int, short: bool = True) -> str:
    if minutes is None:
        return "N/A"
    if minutes < 60:
        return f"{minutes}m" if short else f"{minutes} minutes"
    else:
        hours = minutes // 60
        return f"{hours}h" if short else f"{hours} hours"


def find_machine_from_keyword(machine_keyword: str) -> str | None:
    # This function's dependency on MACHINE_PRICES remains.
    # For it to work, MACHINE_PRICES must be resolvable in its scope.
    # This change does not address that, only the console removal.
    try:
        from celium_cli.src.const import MACHINE_PRICES 
        machines = list(MACHINE_PRICES.keys())
        return next((machine for machine in machines if machine_keyword.lower() in machine.lower()), None)
    except ImportError:
        return None 
    
    