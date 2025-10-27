"""Jupyter installation action."""

import os
import time
from typing import Optional

from ..context import UpContext
from .base import BaseAction


class InstallJupyterIfNeeded(BaseAction):
    """Install Jupyter Notebook on the pod if requested."""

    def should_run(self, ctx: UpContext) -> bool:
        """Only run if Jupyter installation was requested."""
        return ctx.opts.jupyter

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Install Jupyter and wait for completion."""
        # Check for debug mode
        debug = os.getenv('LIUM_DEBUG', '').lower() in ('1', 'true', 'yes')

        # Get the pod's allocated ports
        all_pods = ctx.lium.ps()
        pod = next((p for p in all_pods if p.id == ctx.pod_id or p.huid == ctx.pod_id or p.name == ctx.pod_id), None)

        if not pod:
            ctx.reporter.error("Could not find pod to install Jupyter")
            return True  # Continue pipeline despite failure

        if not pod.ports:
            ctx.reporter.error("No ports allocated to pod for Jupyter installation")
            return True  # Continue pipeline despite failure

        # Filter out SSH port (22) and use the first available port
        available_ports = [int(port) for port in pod.ports.keys() if int(port) != 22]

        if debug:
            ctx.reporter.dim(f"[DEBUG] Pod ports: {pod.ports}")
            ctx.reporter.dim(f"[DEBUG] Available ports (excluding SSH): {available_ports}")

        if not available_ports:
            ctx.reporter.error("No suitable ports available for Jupyter (only SSH port 22 found)")
            return True  # Continue pipeline despite failure

        jupyter_port = available_ports[0]

        if debug:
            ctx.reporter.dim(f"[DEBUG] Calling install_jupyter with pod_id={ctx.pod_id}, port={jupyter_port}")

        try:
            # Start installation with proper step reporting
            with ctx.reporter.step("Installing Jupyter"):
                ctx.lium.install_jupyter(ctx.pod_id, jupyter_port)

                # Poll for completion
                max_wait = 120  # 2 minutes
                wait_interval = 3  # Check every 3 seconds
                elapsed = 0

                while elapsed < max_wait:
                    time.sleep(wait_interval)
                    elapsed += wait_interval

                    all_pods = ctx.lium.ps()
                    updated_pod = next((p for p in all_pods if p.id == ctx.pod_id or p.huid == ctx.pod_id or p.name == ctx.pod_id), None)

                    if updated_pod and hasattr(updated_pod, 'jupyter_installation_status'):
                        if debug:
                            ctx.reporter.dim(f"[DEBUG] Jupyter status: {updated_pod.jupyter_installation_status}")

                        if updated_pod.jupyter_installation_status == "SUCCESS":
                            break
                        elif updated_pod.jupyter_installation_status == "FAILED":
                            # Try to get more error details
                            error_details = ""
                            if hasattr(updated_pod, 'jupyter_error') and updated_pod.jupyter_error:
                                error_details = f": {updated_pod.jupyter_error}"

                            ctx.reporter.error(f"Jupyter installation failed{error_details}")

                            if debug:
                                ctx.reporter.dim(f"[DEBUG] Full pod info: {updated_pod}")
                            else:
                                ctx.reporter.dim("Tip: Run with LIUM_DEBUG=1 for more details")
                            return True  # Continue despite failure

            # Get final pod info and save Jupyter URL
            all_pods = ctx.lium.ps()
            updated_pod = next((p for p in all_pods if p.id == ctx.pod_id or p.huid == ctx.pod_id or p.name == ctx.pod_id), None)

            if updated_pod and hasattr(updated_pod, 'jupyter_url') and updated_pod.jupyter_url:
                ctx.jupyter_url = updated_pod.jupyter_url
            else:
                ctx.reporter.warning("Jupyter installation timed out. Run 'lium ps' to check status")

        except Exception as e:
            # Handle errors but continue pipeline
            import json
            import re

            error_msg = str(e)

            if debug:
                import traceback
                ctx.reporter.dim("[DEBUG] Exception during Jupyter installation:")
                ctx.reporter.dim(traceback.format_exc())

            try:
                error_json = json.loads(error_msg)
                if isinstance(error_json, dict) and 'message' in error_json:
                    ctx.reporter.error(error_json['message'])
                else:
                    ctx.reporter.error("Failed to install Jupyter Notebook")
                    if debug:
                        ctx.reporter.dim(f"[DEBUG] Raw error: {error_msg}")
            except (json.JSONDecodeError, TypeError):
                json_match = re.search(r'"message"\s*:\s*"([^"]+)"', error_msg)
                if json_match:
                    ctx.reporter.error(json_match.group(1))
                else:
                    ctx.reporter.error("Failed to install Jupyter Notebook")
                    if debug:
                        ctx.reporter.dim(f"[DEBUG] Raw error: {error_msg}")

            if not debug:
                ctx.reporter.dim("Tip: Run with LIUM_DEBUG=1 for more details")

        return True  # Continue pipeline even if Jupyter fails
