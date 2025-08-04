import os
from pathlib import Path
from typing import TYPE_CHECKING
import typer
from yaml import safe_dump, safe_load
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.table import Column, Table
from rich import box
from lium_cli.src.apps import BaseApp
from lium_cli.src.const import EPILOG
from lium_cli.src.styles import style_manager
from lium_cli.src.config import defaults
if TYPE_CHECKING:
    from lium_cli.src.cli_manager import CLIManager


class Arguments: 
    docker_username: str = typer.Option(
        None,
        "--docker-username",
        "--docker.username",
        "--docker_username",
        help="The username for the Docker registry",
    )
    docker_password: str = typer.Option(
        None,
        "--docker-password",
        "--docker.password",
        "--docker_password",
        help="The password for the Docker registry",
    )
    server_url: str = typer.Option(
        None,
        "--server-url",
        "--server.url",
        "--server_url",
        help="The URL of the Celium server",
    )
    tao_pay_url: str = typer.Option(
        None,
        "--tao-pay-url",
        "--tao.pay.url",
        "--tao_pay_url",
        help="The URL of the Tao Pay server",
    )
    api_key: str = typer.Option(
        None,
        "--api-key",
        "--api.key",
        "--api_key",
        help="The API key for the Celium server",
    )
    network: str = typer.Option(
        None,
        "--network",
        "--network.name",
        "--network_name",
        help="The network to use",
    )


class ConfigApp(BaseApp):
    def run(self):
        self.config = {
            "docker_username": None,
            "docker_password": None,
            "server_url": "https://lium.io",
            "tao_pay_url": "https://pay-api.lium.io",
            "api_key": None,
            "network": "finney",
        }
        self.config_base_path = os.path.expanduser(defaults.config.base_path)
        self.config_path = os.path.expanduser(defaults.config.path)
        self.app.command("set")(self.set_config)
        self.app.command("get")(self.get_config)
        self.app.command("unset")(self.unset_config)
        self.app.command("show")(self.show_config)
        self.app.command("path")(self.config_path_command)

    def callback(self):
        # Load or create the config file
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                config = safe_load(f)
        else:
            directory_path = Path(self.config_base_path)
            directory_path.mkdir(exist_ok=True, parents=True)
            config = defaults.config.dictionary.copy()
            with open(self.config_path, "w") as f:
                safe_dump(config, f)

        # Update missing values
        updated = False
        for key, value in defaults.config.dictionary.items():
            if key not in config:
                config[key] = value
                updated = True
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in config[key]:
                        config[key][sub_key] = sub_value
                        updated = True
        if updated:
            with open(self.config_path, "w") as f:
                safe_dump(config, f)

        for k, v in config.items():
            if k in self.config.keys():
                self.config[k] = v #  Load or create the config file

        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                config = safe_load(f)
        else:
            directory_path = Path(self.config_base_path)
            directory_path.mkdir(exist_ok=True, parents=True)
            config = defaults.config.dictionary.copy()
            with open(self.config_path, "w") as f:
                safe_dump(config, f)

        # Update missing values
        updated = False
        for key, value in defaults.config.dictionary.items():
            if key not in config:
                config[key] = value
                updated = True
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in config[key]:
                        config[key][sub_key] = sub_value
                        updated = True
        if updated:
            with open(self.config_path, "w") as f:
                safe_dump(config, f)

        for k, v in config.items():
            if k in self.config.keys():
                self.config[k] = v

    def set_config(
        self,
        docker_username: str = Arguments.docker_username,
        docker_password: str = Arguments.docker_password,
        server_url: str = Arguments.server_url,
        tao_pay_url: str = Arguments.tao_pay_url,
        api_key: str = Arguments.api_key,
        network: str = Arguments.network,
    ):  
        """
        Sets or updates configuration values in the Celium CLI config file.

        This command allows you to set default values that will be used across all Celium CLI commands.

        USAGE
        Interactive mode:
            [green]$[/green] lium-cli config set

        Set specific values:
            [green]$[/green] lium-cli config set --docker-username <username> --docker-password <password>

        [bold]NOTE[/bold]:
        - Changes are saved to ~/.lium/lium.yaml
        - Use '[green]$[/green] lium config get' to view current settings
        """
        args = {
            "docker_username": docker_username,
            "docker_password": docker_password,
            "server_url": server_url,
            "tao_pay_url": tao_pay_url,
            "api_key": api_key,
            "network": network,
        }
        bools = []
        if all(v is None for v in args.values()):
            # Print existing configs
            self.get_config()

            # Create numbering to choose from
            config_keys = list(args.keys())
            style_manager.console.print("Which config setting would you like to update?\n")
            for idx, key in enumerate(config_keys, start=1):
                style_manager.console.print(f"{idx}. {key}")

            choice = IntPrompt.ask(
                "\nEnter the [bold]number[/bold] of the config setting you want to update",
                choices=[str(i) for i in range(1, len(config_keys) + 1)],
                show_choices=False,
            )
            arg = config_keys[choice - 1]

            if arg in bools:
                nc = Confirm.ask(
                    f"What value would you like to assign to [red]{arg}[/red]?",
                    default=True,
                )
                self.config[arg] = nc
            else:
                val = Prompt.ask(
                    f"What value would you like to assign to [red]{arg}[/red]?"
                )
                args[arg] = val
                self.config[arg] = val

        for arg, val in args.items():
            if val is not None:
                self.config[arg] = val
        with open(self.config_path, "w") as f:
            safe_dump(self.config, f)

        # Print latest configs after updating
        self.get_config()

    def _update_config(self, key: str, val: str):
        self.config[key] = val
        with open(self.config_path, "w") as f:
            safe_dump(self.config, f)

    def get_config(self):
        table = Table(
            Column("[bold white]Name", style="dark_orange"),
            Column("[bold white]Value", style="gold1"),
            Column("", style="medium_purple"),
            box=box.SIMPLE_HEAD,
        )

        for key, value in self.config.items():
            if isinstance(value, dict):
                # Nested dictionaries: only metagraph for now, but more may be added later
                for idx, (sub_key, sub_value) in enumerate(value.items()):
                    table.add_row(key if idx == 0 else "", str(sub_key), str(sub_value))
            else:
                table.add_row(str(key), str(value), "")

        style_manager.console.print(table)

    def unset_config(self, key: str = typer.Argument(..., help="The configuration key to unset.")):
        """
        Removes a configuration value from the Celium CLI config file.
        """
        config_updated = False
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                current_config = safe_load(f)
            
            if key in current_config:
                del current_config[key]
                with open(self.config_path, "w") as f:
                    safe_dump(current_config, f)
                # Update in-memory config as well
                if key in self.config:
                    del self.config[key] 
                style_manager.console.print(f"[green]Configuration key '{key}' unset successfully.[/green]")
                config_updated = True
            else:
                style_manager.console.print(f"[yellow]Configuration key '{key}' not found.[/yellow]")
        else:
            style_manager.console.print("[yellow]Configuration file does not exist.[/yellow]")

        if config_updated:
            # Reload config to ensure in-memory self.config is fresh
            self.callback() 

    def show_config(self):
        """
        Displays the entire content of the Celium CLI configuration file.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                content = f.read()
            if content.strip():
                style_manager.console.print("[bold magenta]Current Configuration:[/bold magenta]")
                # Assuming YAML, for pretty printing:
                try:
                    parsed_yaml = safe_load(content)
                    style_manager.console.print_json(data=parsed_yaml) # rich console can print json/yaml nicely
                except Exception:
                    style_manager.console.print(content) # Fallback to raw content
            else:
                style_manager.console.print("[yellow]Configuration file is empty.[/yellow]")
        else:
            style_manager.console.print("[yellow]Configuration file does not exist.[/yellow]")

    def config_path_command(self):
        """
        Displays the path to the Celium CLI configuration file.
        """
        style_manager.console.print(f"Configuration file path: [blue]{self.config_path}[/blue]")
