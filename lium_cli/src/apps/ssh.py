import typer
from typing import TYPE_CHECKING
from lium_cli.src.apps import BaseApp
from lium_cli.src.styles import style_manager

if TYPE_CHECKING:
    from lium_cli.src.cli_manager import CLIManager

class SSHApp(BaseApp):
    def run(self):
        self.app.command("connect")(self.connect_ssh)
        self.app.command("exec")(self.execute_command)

    def connect_ssh(self, pod_name: str = typer.Argument(..., help="Name or ID of the pod to SSH into.")):
        """
        Opens an interactive SSH session to a running pod.
        (This feature is currently a placeholder.)
        """
        style_manager.console.print(f"[cyan]SSH connection requested for pod: '{pod_name}'.[/cyan]")
        style_manager.console.print("[yellow]Interactive SSH is not yet implemented in lium-cli.[/yellow]")

    def execute_command(self, pod_name: str = typer.Argument(..., help="Name or ID of the pod."), command_to_run: str = typer.Argument(..., help="The command to execute on the pod.")):
        """
        Executes a command on a running pod via SSH.
        (This feature is currently a placeholder.)
        """
        style_manager.console.print(f"[cyan]SSH command execution requested for pod: '{pod_name}'.[/cyan]")
        style_manager.console.print(f"[cyan]Command: '{command_to_run}'.[/cyan]")
        style_manager.console.print("[yellow]SSH command execution is not yet implemented in lium-cli.[/yellow]") 