"""Pod creation and management actions."""

from typing import Optional

from ..context import UpContext
from .base import BaseAction
from ..helpers import select_template
from ...utils import get_pytorch_template_id, wait_ready_no_timeout


class CreateVolumeIfNeeded(BaseAction):
    """Create a new volume if requested."""

    def should_run(self, ctx: UpContext) -> bool:
        """Only run if volume creation parameters are provided."""
        return ctx.opts.volume_create_params is not None

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Create the volume."""
        params = ctx.opts.volume_create_params

        with ctx.reporter.step(f"Creating volume '{params['name']}'"):
            volume = ctx.lium.volume_create(
                name=params['name'],
                description=params['description']
            )
            ctx.volume = volume
            # Update opts to use the created volume
            ctx.opts.volume_id = volume.id

        ctx.reporter.success(f"Created volume: {volume.huid} ({volume.name})")
        return True


class RentPod(BaseAction):
    """Rent the pod on the selected executor."""

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Create the pod."""
        opts = ctx.opts
        executor = ctx.executor

        # Set pod name default
        if not opts.name:
            opts.name = executor.huid

        # Handle template selection
        if opts.interactive:
            if opts.template_id:
                template = ctx.lium.get_template(opts.template_id)
            else:
                template = select_template(ctx.lium)
            if not template:
                return False  # Stop pipeline
        else:
            if opts.template_id:
                template = ctx.lium.get_template(opts.template_id)
                if not template:
                    ctx.reporter.error(f"Template '{opts.template_id}' not found")
                    return False
            else:
                template = ctx.lium.default_docker_template(executor)
                if not template:
                    template = ctx.lium.get_template(get_pytorch_template_id())

        ctx.template = template

        # Create the pod
        with ctx.reporter.step("Renting machine"):
            pod_info = ctx.lium.up(
                executor_id=executor.id,
                pod_name=opts.name,
                template_id=template.id,
                volume_id=opts.volume_id,
                initial_port_count=opts.ports
            )

        ctx.pod_info = pod_info
        ctx.pod_id = pod_info.get('id') or pod_info.get('name', '')
        return True


class WaitReady(BaseAction):
    """Wait for the pod to be ready."""

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Wait for pod to reach ready state."""
        with ctx.reporter.step("Loading image"):
            ctx.pod = wait_ready_no_timeout(ctx.lium, ctx.pod_id)

        return True
