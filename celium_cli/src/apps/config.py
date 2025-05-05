import os
from pathlib import Path
from typing import TYPE_CHECKING
import typer
from yaml import safe_dump, safe_load
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.table import Column, Table
from rich import box
from celium_cli.src.apps import BaseApp
from celium_cli.src.const import EPILOG
from celium_cli.src.utils import console
from celium_cli.src.config import defaults
if TYPE_CHECKING:
    from celium_cli.src.cli_manager import CLIManager


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


class ConfigApp(BaseApp):
    def run(self):
        self.config = {
            "docker_username": None,
            "docker_password": None,
        }
        self.config_base_path = os.path.expanduser(defaults.config.base_path)
        self.config_path = os.path.expanduser(defaults.config.path)
        self.app.command("set")(self.set_config)
        self.app.command("get")(self.get_config)

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
    ):
        """
        Sets or updates configuration values in the Celium CLI config file.

        This command allows you to set default values that will be used across all Celium CLI commands.

        USAGE
        Interactive mode:
            [green]$[/green] celium config set

        Set specific values:
            [green]$[/green] celium config set --docker-username <username> --docker-password <password>

        [bold]NOTE[/bold]:
        - Changes are saved to ~/.celium/celium.yaml
        - Use '[green]$[/green] celium config get' to view current settings
        """
        args = {
            "docker_username": docker_username,
            "docker_password": docker_password,
        }
        bools = []
        if all(v is None for v in args.values()):
            # Print existing configs
            self.get_config()

            # Create numbering to choose from
            config_keys = list(args.keys())
            console.print("Which config setting would you like to update?\n")
            for idx, key in enumerate(config_keys, start=1):
                console.print(f"{idx}. {key}")

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

        console.print(table)
