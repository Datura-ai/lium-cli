from rich.console import Console

console = Console()
json_console = Console()
err_console = Console(stderr=True)
verbose_console = Console(quiet=True)


def pretty_minutes(minutes: int) -> str:
    days, rem_minutes = divmod(minutes, 1440)  # 1440 minutes in a day
    hours, rem_minutes = divmod(rem_minutes, 60)
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if rem_minutes or not parts:
        parts.append(f"{rem_minutes} minute{'s' if rem_minutes != 1 else ''}")
    return ", ".join(parts)

