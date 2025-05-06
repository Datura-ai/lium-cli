from rich.console import Console

console = Console()
json_console = Console()
err_console = Console(stderr=True)
verbose_console = Console(quiet=True)

MACHINE_PRICES = {
    # Latest Gen NVIDIA GPUs (Averaged if applicable)
    "NVIDIA B200": 12.99 / 2,
    "NVIDIA H200": 9.79 / 2,
    "NVIDIA H100 80GB HBM3": 6.50 / 2,
    "NVIDIA H100 NVL": 5.20 / 2,
    "NVIDIA H100 PCIe": 5.00 / 2,
    "NVIDIA H800 80GB HBM3": 2.61 / 2,
    "NVIDIA H800 NVL": 2.09 / 2,
    "NVIDIA H800 PCIe": 2.01 / 2,
    "NVIDIA GeForce RTX 5090": 0.98 / 2,
    "NVIDIA GeForce RTX 4090": 0.38 / 2,
    "NVIDIA GeForce RTX 4090 D": 0.26 / 2,
    "NVIDIA RTX 4000 Ada Generation": 0.38 / 2,
    "NVIDIA RTX 6000 Ada Generation": 1.03 / 2,
    "NVIDIA L4": 0.43 / 2,
    "NVIDIA L40S": 1.03 / 2,
    "NVIDIA L40": 0.99 / 2,
    "NVIDIA RTX 2000 Ada Generation": 0.28 / 2,
    # Previous Gen NVIDIA GPUs (Averaged if applicable)
    "NVIDIA A100 80GB PCIe": 1.64 / 2,
    "NVIDIA A100-SXM4-80GB": 1.89 / 2,
    "NVIDIA RTX A6000": 0.87 / 2,
    "NVIDIA RTX A5000": 0.43 / 2,
    "NVIDIA RTX A4500": 0.35 / 2,
    "NVIDIA RTX A4000": 0.32 / 2,
    "NVIDIA A40": 0.39 / 2,
    "NVIDIA GeForce RTX 3090": 0.21 / 2,
}


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


def pretty_seconds(seconds: int) -> str:
    days, rem_seconds = divmod(seconds, 86400)
    hours, rem_seconds = divmod(rem_seconds, 3600)
    minutes, rem_seconds = divmod(rem_seconds, 60)
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if rem_seconds:
        parts.append(f"{rem_seconds} second{'s' if rem_seconds != 1 else ''}")
    return ", ".join(parts)


def find_machine_from_keyword(machine_keyword: str) -> str | None:
    machines = list(MACHINE_PRICES.keys())
    return next((machine for machine in machines if machine_keyword.lower() in machine.lower()), None)
    
    