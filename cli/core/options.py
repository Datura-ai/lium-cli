"""Options dataclasses for command configuration."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict


@dataclass
class UpOptions:
    """Configuration options for the 'up' command."""

    # Executor selection
    executor_id: Optional[str] = None
    gpu: Optional[str] = None
    count: Optional[int] = None
    country: Optional[str] = None
    ports: Optional[int] = None

    # Pod configuration
    name: Optional[str] = None
    template_id: Optional[str] = None
    volume_id: Optional[str] = None
    volume_create_params: Optional[Dict[str, str]] = None

    # Behavior flags
    skip_confirm: bool = False
    interactive: bool = False

    # Additional features
    termination_time: Optional[datetime] = None
    jupyter: bool = False
