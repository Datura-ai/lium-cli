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
    table = Table(title="Miner Setup Plan", show_header=False, box=box.SIMPLE_HEAVY)
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("What happens")
    table.add_row("1", "Clone or update compute-subnet repo")
    table.add_row("2", "Prerequisite check (Docker, NVIDIA GPU)")
    table.add_row("3", "Install executor dependencies")
    table.add_row("4", "Configure executor .env (ports, hotkey)")
    table.add_row("5", "Start executor with docker compose")
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
    script = compute_dir / "scripts" / "install_executor_on_ubuntu_tight.sh"
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
    internal_port: int = 4000,
    external_port: int = 4000,
    ssh_port: int = 4122,
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


def _start_executor(executor_dir: Path, wait_secs: int = 45) -> bool:
    # Use the app compose file if it exists
    compose_file = executor_dir / "docker-compose.app.yml"
    if compose_file.exists():
        compose_cmd = "docker compose -f docker-compose.app.yml"
    else:
        compose_cmd = "docker compose"
    
    # Bring up
    code, out, err = _run(f"{compose_cmd} up -d", capture=True, cwd=str(executor_dir))
    if code != 0:
        return False

    # Wait specifically for the executor service to be healthy
    start = time.time()
    
    while time.time() - start < wait_secs:
        # Check the executor service specifically
        code, out, _ = _run(f"{compose_cmd} ps executor --format json", capture=True, cwd=str(executor_dir))
        
        if code == 0 and out.strip():
            try:
                # Parse the JSON output
                service_info = json.loads(out.strip())
                # Check if it's a list (newer docker) or single object
                if isinstance(service_info, list) and service_info:
                    service_info = service_info[0]
                
                # Check status - looking for "Up" and optionally "(healthy)"
                status = service_info.get("Status", "").lower()
                state = service_info.get("State", "").lower()
                
                # Service is considered ready if it's running/up
                # Some versions use "Status" others use "State"
                if "running" in state or "up" in status or "healthy" in status:
                    return True
            except Exception:
                # Fallback to checking if container is at least running
                code2, out2, _ = _run(f"{compose_cmd} ps executor", capture=True, cwd=str(executor_dir))
                if code2 == 0 and "running" in out2.lower():
                    return True
        
        time.sleep(2)
    
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

    # Always proceed with setup - no need to ask
    # Always install dependencies and start - that's the point of the command
    answers["run_installer"] = True
    answers["start_now"] = True

    if not hotkey and not auto:
        hotkey = Prompt.ask("Miner hotkey SS58 address")
    answers["hotkey"] = hotkey or ""

    if auto:
        answers.update(dict(
            internal_port="4000",
            external_port="4000",
            ssh_port="4122",
            ssh_public_port="",
            port_range=""
        ))
    else:
        def ask_port(label, default):
            while True:
                v = Prompt.ask(label, default=str(default))
                if v.isdigit() and 1 <= int(v) <= 65535:
                    return v
                console.warning("Port must be an integer between 1 and 65535.")
        answers["internal_port"] = ask_port("Internal port", 4000)
        answers["external_port"] = ask_port("External port", 4000)
        answers["ssh_port"] = ask_port("SSH port", 4122)
        answers["ssh_public_port"] = Prompt.ask("SSH public port (optional)", default="")
        answers["port_range"] = Prompt.ask("Port range (optional, e.g. 2000-2005 or 2000,2001)", default="")

    return answers


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
        with timed_step_status(5, 5, "Starting executor"):
            started = _start_executor(executor_dir)
        
        if not started:
            console.warning("⚠️  Executor started but health check failed")
            console.info("\nTroubleshooting:")
            console.info(f"  cd {executor_dir}")
            console.info("  docker compose logs -f  # View logs")
            console.info("  docker compose ps       # Check status")
            return

    console.success("\n✨ Miner setup complete!")
