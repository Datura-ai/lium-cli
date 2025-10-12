# mine.py
"""Mine command for setting up a compute subnet executor/miner."""
import os
import re
import sys
import json
import time
import socket
import shutil
import platform
from pathlib import Path

from typing import Optional, Tuple

import click
from rich import box
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..utils import console, handle_errors, timed_step_status


class PrerequisiteError(Exception):
    """Raised when prerequisite checks fail."""
    pass


# --------------------------
# Helpers
# --------------------------
def _get_gpu_info() -> dict:
    """Get GPU information using nvidia-smi."""
    # Query only the GPU name field to get clean output
    code, out, err = _run("nvidia-smi --query-gpu=name --format=csv,noheader", capture=True)
    if code != 0:
        return {"gpu_count": 0, "gpu_type": None}
    
    lines = out.strip().split('\n')
    if lines and lines[0]:
        # Get the first GPU's name (all GPUs in a system are typically the same model)
        gpu_name = lines[0].strip()
        # Count the number of GPUs
        gpu_count = len(lines)
        return {"gpu_count": gpu_count, "gpu_type": gpu_name}
    
    return {"gpu_count": 0, "gpu_type": None}


def _get_public_ip() -> str:
    """Get the public IP address."""
    # Try multiple services for redundancy
    services = [
        "https://api.ipify.org",
        "https://icanhazip.com", 
        "https://ifconfig.me/ip"
    ]
    
    for service in services:
        code, out, err = _run(f"curl -s {service}", capture=True)
        if code == 0 and out.strip():
            ip = out.strip()
            # Basic IP validation
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                return ip
    
    return "Unable to determine"
def _run(cmd: list | str, check=False, capture=False, cwd: Optional[str] = None) -> Tuple[int, str, str]:
    import subprocess
    if isinstance(cmd, list):
        cmd_str = " ".join(cmd)
    else:
        cmd_str = cmd
    result = subprocess.run(
        cmd_str,
        shell=True,
        cwd=cwd,
        text=True,
        capture_output=capture,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {cmd_str}\n{result.stderr}")
    return result.returncode, (result.stdout or ""), (result.stderr or "")


def _exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _port_is_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            return s.connect_ex(("127.0.0.1", port)) != 0
    except Exception:
        return True  # if we cannot check, assume free


def _validate_hotkey(hotkey: str) -> bool:
    # Very light sanity: SS58 are typically 47–49 chars base58 with prefixes; don’t overfit.
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{40,60}", hotkey))


def _show_setup_summary():
    table = Table(title="Executor Setup Plan", show_header=False, box=box.SIMPLE_HEAVY)
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("What happens")
    table.add_row("1", "Clone or update compute-subnet repo")
    table.add_row("2", "Prerequisite check (Docker, NVIDIA GPU)")
    table.add_row("3", "Install executor dependencies")
    table.add_row("4", "Configure executor .env (ports, hotkey)")
    table.add_row("5", "Start executor with docker compose")
    table.add_row("6", "Validate executor configuration")
    console.print(table)
    console.print()


# --------------------------
# Actions
# --------------------------
def _clone_or_update_repo(target_dir: Path, branch: str, allow_update: bool) -> bool:
    if target_dir.exists():
        if (target_dir / ".git").exists():
            if allow_update:
                # Don't print during spinner - just do the work
                code, out, err = _run("git fetch --all", capture=True, cwd=str(target_dir))
                if code != 0:
                    return False
                _run(f"git checkout {branch}", capture=True, cwd=str(target_dir))
                code, out, err = _run(f"git pull origin {branch}", capture=True, cwd=str(target_dir))
                if code != 0:
                    return False
                return True
            else:
                # Directory exists, just return true
                return True
        else:
            # Not a git repo
            return False

    # Clone new repo
    code, out, err = _run(
        f"git clone --branch {branch} https://github.com/Datura-ai/lium-io.git {target_dir}",
        capture=True,
    )
    if code != 0:
        return False
    return True


def _check_prereqs(interactive: bool) -> bool:
    # GPU is REQUIRED - check first
    if not _exists("nvidia-smi"):
        # The timed_step_status will handle line clearing when it exits
        return False
    
    # Verify GPU is working
    code, out, err = _run("nvidia-smi --query-gpu=name --format=csv,noheader", capture=True)
    if code != 0 or not out.strip():
        return False
    
    if not _exists("nvidia-container-cli"):
        return False
    
    # Check Docker
    if not _exists("docker"):
        return False
    
    # test docker can talk to daemon
    code, out, err = _run("docker info", capture=True)
    if code != 0:
        return False
    
    return True


def _install_executor_tools(compute_dir: Path, noninteractive: bool) -> bool:
    script = compute_dir / "scripts" / "install_executor_on_ubuntu.sh"
    if not script.exists():
        # Skip silently if script not found
        return True

    _run(f"chmod +x {script}", capture=True)
    code, out, err = _run(str(script), capture=True)
    # Don't print anything - let the spinner handle the output
    return code == 0


def _setup_executor_env(
    executor_dir: str | Path,
    *,
    hotkey: str,
    internal_port: int = 8080,
    external_port: int = 8080,
    ssh_port: int = 2200,
    ssh_public_port: str = "",
    port_range: str = "",
) -> bool:
    """
    Render neur ons/executor/.env from .env.template with provided values.

    - Never prompts.
    - Preserves unknown lines/keys from the template.
    - Ensures required keys exist even if missing in template.
    """
    executor_dir = Path(executor_dir)
    env_t = executor_dir / ".env.template"
    env_f = executor_dir / ".env"

    if not env_t.exists():
        console.error(f".env.template not found at {env_t}")
        return False

    # light sanity checks (don't be strict)
    def _valid_port(p: int) -> bool:
        return isinstance(p, int) and 1 <= p <= 65535

    if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{40,60}", hotkey or ""):
        console.warning("Hotkey format looks unusual; continuing anyway.")

    for p, name in [(internal_port, "INTERNAL_PORT"),
                    (external_port, "EXTERNAL_PORT"),
                    (ssh_port, "SSH_PORT")]:
        if not _valid_port(p):
            console.error(f"{name} must be in 1–65535.")
            return False

    # read, rewrite, preserve
    src_lines = env_t.read_text().splitlines()
    out_lines = []
    seen = set()

    def put(k: str, v: str | int):
        nonlocal out_lines, seen
        out_lines.append(f"{k}={v}")
        seen.add(k)

    for line in src_lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            out_lines.append(line)
            continue

        k, _ = line.split("=", 1)
        if k == "MINER_HOTKEY_SS58_ADDRESS":
            put(k, hotkey)
        elif k == "INTERNAL_PORT":
            put(k, internal_port)
        elif k == "EXTERNAL_PORT":
            put(k, external_port)
        elif k == "SSH_PORT":
            put(k, ssh_port)
        elif k == "SSH_PUBLIC_PORT":
            # only write if provided; otherwise keep template as-is or blank it
            if ssh_public_port:
                put(k, ssh_public_port)
            else:
                out_lines.append(line)  # preserve whatever template had
        elif k == "RENTING_PORT_RANGE":
            if port_range:
                put(k, port_range)
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)  # unknown key: preserve

    # ensure required keys exist even if template lacked them
    required = {
        "MINER_HOTKEY_SS58_ADDRESS": hotkey,
        "INTERNAL_PORT": internal_port,
        "EXTERNAL_PORT": external_port,
        "SSH_PORT": ssh_port,
    }
    for k, v in required.items():
        if k not in seen and not any(l.startswith(f"{k}=") for l in out_lines):
            out_lines.append(f"{k}={v}")

    env_f.write_text("\n".join(map(str, out_lines)) + "\n")
    # Don't print anything - let the spinner handle the output
    return True


def _start_executor(executor_dir: Path, wait_secs: int = 180) -> bool:
    # Start using the default docker-compose.yml
    code, out, err = _run("docker compose up -d", capture=True, cwd=str(executor_dir))
    if code != 0:
        return False

    # Wait for the executor service to be fully healthy
    start = time.time()
    
    while time.time() - start < wait_secs:
        # Get the container name/ID for the executor service
        code, out, _ = _run("docker compose -f docker-compose.app.yml ps -q executor", capture=True, cwd=str(executor_dir))
        if code != 0 or not out.strip():
            time.sleep(2)
            continue
            
        container_id = out.strip()
        
        # Check the health status directly using docker inspect
        code, out, _ = _run(f"docker inspect --format='{{{{.State.Health.Status}}}}' {container_id}", capture=True)
        
        if code == 0 and out.strip():
            health_status = out.strip()
            # Only return true if explicitly healthy
            if health_status == "healthy":
                return True
            # If there's no healthcheck defined, check if container is at least running
            elif health_status == "<no value>":
                code2, out2, _ = _run(f"docker inspect --format='{{{{.State.Status}}}}' {container_id}", capture=True)
                if code2 == 0 and out2.strip() == "running":
                    # No healthcheck defined, but container is running - consider it ready
                    return True
        
        time.sleep(3)
    
    return False

def _apply_env_overrides(
    executor_dir: Path,
    internal: str, external: str, ssh: str, ssh_pub: str, rng: str
):
    env_f = executor_dir / ".env"
    content = env_f.read_text().splitlines()
    def set_or_append(key, val):
        nonlocal content
        pat = f"{key}="
        for i, line in enumerate(content):
            if line.startswith(pat):
                content[i] = f"{pat}{val}"
                break
        else:
            content.append(f"{pat}{val}")
    set_or_append("INTERNAL_PORT", internal)
    set_or_append("EXTERNAL_PORT", external)
    set_or_append("SSH_PORT", ssh)
    if ssh_pub:
        set_or_append("SSH_PUBLIC_PORT", ssh_pub)
    if rng:
        set_or_append("RENTING_PORT_RANGE", rng)
    env_f.write_text("\n".join(content) + "\n")

def _gather_inputs(
    hotkey: Optional[str],
    auto: bool,
    yes: bool,
) -> dict:
    """Ask everything up-front; return a dict of resolved inputs."""
    answers = {}

    # Always install dependencies and start - that's the point of the command
    answers["run_installer"] = True
    answers["start_now"] = True

    if auto:
        # Auto mode - use all defaults
        answers["hotkey"] = hotkey or ""
        answers.update(dict(
            internal_port="8080",
            external_port="8080",
            ssh_port="2200",
            ssh_public_port="",
            port_range=""
        ))
    else:
        # Show informative header about port configuration
        console.print("\n[bold]We're setting up how your executor can be reached.[/bold]\n")
        console.print("• [cyan]Service port[/cyan] → where the executor's HTTP API listens (default 8080).")
        console.print("• [cyan]Executor SSH port[/cyan] → used by validators to SSH into the container (default 2200).")
        console.print("• [cyan]Public SSH port[/cyan] → only if your server is behind NAT and you forward a different public port.")
        console.print("• [cyan]Renting port range[/cyan] → optional, used only if your firewall limits outbound ports.\n")
        
        if not hotkey:
            hotkey = Prompt.ask("Miner hotkey SS58 address")
        else:
            console.print(f"Miner hotkey SS58 address: [yellow]{hotkey}[/yellow]\n")
        answers["hotkey"] = hotkey or ""

        def ask_port(label, default):
            while True:
                v = Prompt.ask(label, default=str(default))
                if not v:  # Allow empty for optional ports
                    return ""
                if v.isdigit() and 1 <= int(v) <= 65535:
                    return v
                console.warning("Port must be an integer between 1 and 65535.")
        
        # Service ports
        service_port = ask_port("Service port (where the executor API will be reachable)", 8080)
        answers["internal_port"] = service_port
        answers["external_port"] = service_port  # Set external same as internal
        answers["ssh_port"] = ask_port("Executor SSH port (used by validator to SSH into the container)", 2200)
        
        # Optional ports
        ssh_public = Prompt.ask("Public SSH port (optional, only if behind NAT and forwarding a different port)", default="")
        answers["ssh_public_port"] = ssh_public if ssh_public and ssh_public.isdigit() else ""
        
        answers["port_range"] = Prompt.ask("Renting port range (optional, e.g. 2000-2005 or 2000,2001). Leave empty if all ports open", default="")

    return answers


def _validate_executor() -> tuple[bool, str]:
    """
    Validate the executor using the Lium validator Docker image.
    Returns (passed, message) tuple.
    """
    try:
        code, out, err = _run(
            "docker run --rm --gpus all daturaai/lium-validator:latest",
            capture=True
        )

        if code != 0:
            return False, f"Validator failed to run: {err}"

        # Parse JSON output
        result = json.loads(out.strip())
        passed = result.get("passed", False)
        message = result.get("message", "")

        return passed, message

    except json.JSONDecodeError as e:
        return False, f"Failed to parse validator output: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"


# --------------------------
# CLI
# --------------------------
@click.command("mine")
@click.option("--hotkey", "-k", help="Miner hotkey SS58 address")
@click.option("--dir", "-d", "dir_", default="compute-subnet", help="Target directory")
@click.option("--branch", "-b", default="main")
@click.option("--update/--no-update", default=True)
@click.option("--no-start", is_flag=True)
@click.option("--auto", "-a", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--verbose", "-v", is_flag=True, help="Show the plan banner")
@handle_errors
def mine_command(hotkey, dir_, branch, update, no_start, auto, yes, verbose):
    # No need for ensure_config() - this command doesn't use Lium API

    if verbose:
        _show_setup_summary()   # keep the banner only when asked

    # 👉 All questions happen here, before spinners:
    answers = _gather_inputs(hotkey, auto, yes)

    # Steps below are non-interactive:
    target_dir = Path(dir_).absolute()

    with timed_step_status(1, 5, "Ensuring repository"):
        if not _clone_or_update_repo(target_dir, branch, allow_update=update):
            return

    try:
        with timed_step_status(2, 5, "Checking prerequisites"):
            if not _check_prereqs(interactive=False):
                # Determine the specific error
                if not _exists("nvidia-smi"):
                    raise PrerequisiteError("nvidia-smi not found. GPU driver is required for mining.")
                elif not _run("nvidia-smi --query-gpu=name --format=csv,noheader", capture=True)[1].strip():
                    raise PrerequisiteError("No GPU detected. A working NVIDIA GPU is required for mining.")
                elif not _exists("nvidia-container-cli"):
                    raise PrerequisiteError("nvidia-container-toolkit not found. Required for GPU passthrough.")
                elif not _exists("docker"):
                    raise PrerequisiteError("Docker is not installed or not on PATH.")
                else:
                    raise PrerequisiteError("Docker daemon not reachable. Is the service running?")
    except PrerequisiteError as e:
        # The timed_step_status will show "failed" in red
        console.error(f"❌ {e}")
        return

    if answers["run_installer"]:
        with timed_step_status(3, 5, "Installing executor tools"):
            if not _install_executor_tools(target_dir, noninteractive=True):
                console.error("Installer failed."); return

    executor_dir = target_dir / "neurons" / "executor"
    if not executor_dir.exists():
        console.error(f"Executor directory not found at {executor_dir}")
        return

    with timed_step_status(4, 5, "Configuring environment"):
        if not _setup_executor_env(
            str(executor_dir),
            hotkey=answers["hotkey"],
            # pass ports so _setup_executor_env doesn't prompt:
        ):
            return
        # write ports directly after reading template:
        _apply_env_overrides(
            executor_dir,
            internal=answers["internal_port"],
            external=answers["external_port"],
            ssh=answers["ssh_port"],
            ssh_pub=answers["ssh_public_port"],
            rng=answers["port_range"],
        )

    if no_start:
        console.info("Skipping start (--no-start).")
    else:
        with timed_step_status(5, 6, "Starting executor"):
            started = _start_executor(executor_dir)

        if not started:
            console.warning("⚠️  Executor started but health check failed")
            console.info("\nTroubleshooting:")
            console.info(f"  cd {executor_dir}")
            console.info("  docker compose logs -f  # View logs")
            console.info("  docker compose ps       # Check status")
            return

        # Step 6: Validate executor configuration
        with timed_step_status(6, 6, "Validating executor"):
            validation_passed, validation_message = _validate_executor()

        if not validation_passed:
            console.warning(f"⚠️  Executor validation failed: {validation_message}")
        else:
            console.success("✓ Executor validation passed")

    # Get executor details for summary
    gpu_info = _get_gpu_info()
    public_ip = _get_public_ip()
    
    # Get the external port from answers
    external_port = answers.get("external_port", "8080")
    
    console.success("\n✨ Executor setup complete!")
    console.print()
    
    # Show executor details
    from rich.table import Table
    
    details_table = Table(show_header=False, box=None)
    details_table.add_column("Key", style="cyan")
    details_table.add_column("Value", style="white")
    
    details_table.add_row("📍 Endpoint", f"{public_ip}:{external_port}")
    details_table.add_row("🎮 GPU", f"{gpu_info['gpu_count']}×{gpu_info['gpu_type']}")
    details_table.add_row("📂 Directory", str(executor_dir))
    details_table.add_row("🔑 Hotkey", answers.get("hotkey", "Not set")[:20] + "..." if len(answers.get("hotkey", "")) > 20 else answers.get("hotkey", "Not set"))
    
    console.print(Panel(details_table, title="[bold]Executor Details[/bold]", border_style="green"))
    
    # Generate URL for adding executor via web interface
    from urllib.parse import urlencode
    
    # Build query parameters
    params = {
        'action': 'add',
        'gpu_type': gpu_info.get('gpu_type', 'Unknown'),
        'ip_address': public_ip,
        'port': external_port,
        'gpu_count': gpu_info.get('gpu_count', 0)
    }
    
    # Build full URL with proper encoding
    add_url = f"https://provider.lium.io/executors?{urlencode(params)}"
    
    console.print("\n[bold cyan]Add this executor via web interface:[/bold cyan]")
    console.print(f"[yellow]{add_url}[/yellow]\n")
