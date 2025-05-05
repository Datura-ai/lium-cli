import os
from pathlib import Path
import sys
import asyncio
import importlib
from typing import Annotated, Optional
import typer
from rich.tree import Tree
from yaml import safe_dump, safe_load

from celium_cli.src.apps.config import ConfigApp
from celium_cli.src.const import EPILOG
from celium_cli.src.config import defaults
from celium_cli.src.version import __version__
from celium_cli.src.utils import console
try:
    from git import Repo, GitError
except ImportError:
    Repo = None

    class GitError(Exception):
        pass


def version_callback(value: bool):
    """
    Prints the current version/branch-name
    """
    if value:
        try:
            repo = Repo(os.path.dirname(os.path.dirname(__file__)))
            version = (
                f"Celium CLI version: {__version__}/"
                f"{repo.active_branch.name}/"
                f"{repo.commit()}"
            )
        except (TypeError, GitError):
            version = f"Celium CLI version: {__version__}"
        typer.echo(version)
        raise typer.Exit()


def commands_callback(value: bool):
    """
    Prints a tree of commands for the app
    """
    if value:
        cli = CLIManager()
        console.print(cli.generate_command_tree())
        raise typer.Exit()


class CLIManager:
    config_app: ConfigApp

    def __init__(self):
        # Initialize the CLI app
        self.app = typer.Typer(
            rich_markup_mode="rich",
            callback=self.main_callback,
            epilog=EPILOG,
            no_args_is_help=True,
        )
        self.config_app = ConfigApp(self)

        self.app.add_typer(
            self.config_app.app, 
            name="config",
            short_help="Config commands, aliases: `c`, `conf`",
            no_args_is_help=True,
        )
        
    def main_callback(
        self,
        version: Annotated[
            Optional[bool],
            typer.Option(
                "--version", callback=version_callback, help="Show Celium CLI version"
            ),
        ] = None,
        commands: Annotated[
            Optional[bool],
            typer.Option(
                "--commands", callback=commands_callback, help="Show Celium CLI commands"
            ),
        ] = None,
    ):
        """
        Command line interface (CLI) for Celium. Uses the values in the configuration file. These values can be
            overriden by passing them explicitly in the command line.
        """
        self.config_app.callback()

        if sys.version_info < (3, 10):
            # For Python 3.9 or lower
            self.asyncio_runner = asyncio.get_event_loop().run_until_complete
        else:
            try:
                uvloop = importlib.import_module("uvloop")
                if sys.version_info >= (3, 11):
                    self.asyncio_runner = uvloop.run
                else:
                    uvloop.install()
                    self.asyncio_runner = asyncio.run
            except ModuleNotFoundError:
                self.asyncio_runner = asyncio.run

    def generate_command_tree(self) -> Tree:
        """
        Generates a rich.Tree of the commands, subcommands, and groups of this app
        """

        def build_rich_tree(data: dict, parent: Tree):
            for group, content in data.get("groups", {}).items():
                group_node = parent.add(
                    f"[bold cyan]{group}[/]"
                )  # Add group to the tree
                for command in content.get("commands", []):
                    group_node.add(f"[green]{command}[/]")  # Add commands to the group
                build_rich_tree(content, group_node)  # Recurse for subgroups

        def traverse_group(group: typer.Typer) -> dict:
            tree = {}
            if commands := [
                cmd.name for cmd in group.registered_commands if not cmd.hidden
            ]:
                tree["commands"] = commands
            for group in group.registered_groups:
                if "groups" not in tree:
                    tree["groups"] = {}
                if not group.hidden:
                    if group_transversal := traverse_group(group.typer_instance):
                        tree["groups"][group.name] = group_transversal

            return tree

        groups_and_commands = traverse_group(self.app)
        root = Tree("[bold magenta]Celium CLI Commands[/]")  # Root node
        build_rich_tree(groups_and_commands, root)
        return root

    def run(self):
        self.app()