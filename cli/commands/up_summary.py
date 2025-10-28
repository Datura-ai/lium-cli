"""Summary builder for the up command."""

from typing import Tuple, List
from datetime import datetime

from ..core.summary import SummaryBuilder
from ..core.context import UpContext


def _get_flag(country_code: str) -> str:
    """Get flag emoji for country code."""
    flags = {
        "US": "🇺🇸",
        "CA": "🇨🇦",
        "GB": "🇬🇧",
        "DE": "🇩🇪",
        "FR": "🇫🇷",
        "JP": "🇯🇵",
        "AU": "🇦🇺",
        "SG": "🇸🇬",
    }
    return flags.get(country_code.upper(), "")


def _format_termination_time(termination_time: datetime) -> str:
    """Format termination time with countdown."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    delta = termination_time - now

    # Calculate time left
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)

    if hours > 0:
        time_left = f"{hours}h {minutes}m"
    else:
        time_left = f"{minutes}m"

    formatted = termination_time.strftime("%Y-%m-%d %H:%M UTC")
    return f"{formatted} (in {time_left})"


class UpSummaryBuilder(SummaryBuilder):
    """Summary builder for the up command."""

    def build_preflight(self, ctx: UpContext) -> List[Tuple[str, str]]:
        """Build pre-flight information for up command."""
        items = []
        if ctx.executor is None:
            return items

        # Executor matching info
        executor = ctx.executor
        items.append((f"→ Matched executor for GPU", f"[bold]{executor.gpu_type}[/]"))

        # Executor details
        executor_info = f"[cyan]{executor.huid}[/] ({executor.gpu_count}×{executor.gpu_type})"
        items.append(("", executor_info))

        # Location (extract from location dict)
        country_code = ""
        if executor.location:
            country_code = executor.location.get("country_code", "")

        if country_code:
            flag = _get_flag(country_code)
            location = f"{country_code} {flag}".strip()
            items.append(("Location", location))

        # Cost
        items.append(("Cost", f"${executor.price_per_hour:.2f}/h"))

        # Template (if specified)
        if ctx.template:
            items.append(("Template", ctx.template.name))

        # Volume (if being created or attached)
        if ctx.opts.volume_id:
            items.append(("Volume", ctx.opts.volume_id))
        elif ctx.opts.volume_create_params:
            size = ctx.opts.volume_create_params.get("size", "unknown")
            items.append(("Volume", f"Creating new ({size} GB)"))

        # Jupyter (if enabled)
        if ctx.opts.jupyter:
            items.append(("Jupyter", "Will be installed"))

        # Auto-termination (if set)
        if ctx.opts.termination_time:
            time_str = _format_termination_time(ctx.opts.termination_time)
            items.append(("Auto-terminate", time_str))

        return items

    def build_completion(self, ctx: UpContext) -> Tuple[str, List[Tuple[str, str]]]:
        """Build completion summary for up command."""
        items = []

        # Jupyter URL (if installed)
        if ctx.jupyter_url:
            items.append(("Jupyter", ctx.jupyter_url))

        # SSH command
        if ctx.ssh_cmd:
            items.append(("SSH", ctx.ssh_cmd))

        # Auto-termination reminder
        if ctx.opts.termination_time:
            time_str = _format_termination_time(ctx.opts.termination_time)
            items.append(("Auto-terminate", time_str))

        # Pod name as title
        pod_name = ctx.pod.name if ctx.pod else "unknown"
        title = f"✓ Pod ready: {pod_name}"

        return (title, items)
