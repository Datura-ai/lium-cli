"""Context object for managing state through the pipeline."""

from typing import Optional, Union

from cli.lium_sdk import Lium, ExecutorInfo, PodInfo, Template, VolumeInfo
from .options import UpOptions
from .reporter import Reporter, NullReporter


class UpContext:
    """Shared context for the 'up' command pipeline.

    This context is passed through all actions and accumulates state
    as the pipeline progresses.
    """

    def __init__(
        self,
        lium: Lium,
        opts: UpOptions,
        reporter: Union[Reporter, NullReporter]
    ):
        self.lium = lium
        self.opts = opts
        self.reporter = reporter

        # State accumulated during pipeline execution
        self.executor: Optional[ExecutorInfo] = None
        self.template: Optional[Template] = None
        self.volume: Optional[VolumeInfo] = None
        self.pod_info: Optional[dict] = None
        self.pod_id: Optional[str] = None
        self.pod: Optional[PodInfo] = None
        self.ssh_cmd: Optional[str] = None
        self.jupyter_url: Optional[str] = None
