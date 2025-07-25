import os
from pathlib import Path
import sys
import asyncio
import importlib
from typing import Annotated, Optional
import typer
from rich.tree import Tree
from yaml import safe_dump, safe_load

from lium_cli.src.apps.config import ConfigApp
from lium_cli.src.apps.pay import PayApp
from lium_cli.src.apps.pod import PodApp
from lium_cli.src.apps.template import TemplateApp
from lium_cli.src.apps.theme import ThemeApp
from lium_cli.src.apps.ssh import SSHApp
from lium_cli.src.apps.lium import LiumApp
from lium_cli.src.const import EPILOG
from lium_cli.src.config import defaults
from lium_cli.src.version import __version__
from lium_cli.src.styles import style_manager
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
                f"Lium CLI version: {__version__}/"
                f"{repo.active_branch.name}/"
                f"{repo.commit()}"
            )
        except (TypeError, GitError):
            version = f"Lium CLI version: {__version__}"
        typer.echo(version)
        raise typer.Exit()


def commands_callback(value: bool):
    """
    Prints a tree of commands for the app
    """
    if value:
        cli = CLIManager()
        style_manager.console.print(cli.generate_command_tree())
        raise typer.Exit()


class CLIManager:
    config_app: ConfigApp
    pod_app: PodApp
    pay_app: PayApp
    template_app: TemplateApp
    theme_app: ThemeApp
    ssh_app: SSHApp
    lium_app: LiumApp

    def __init__(self):
        # Initialize the CLI app
        self.app = typer.Typer(
            rich_markup_mode="rich",
            callback=self.main_callback,
            epilog=EPILOG,
            no_args_is_help=True,
        )
        self.config_app = ConfigApp(self)
        self.pod_app = PodApp(self)
        self.template_app = TemplateApp(self)
        self.pay_app = PayApp(self)
        self.theme_app = ThemeApp(self)
        self.ssh_app = SSHApp(self)
        self.lium_app = LiumApp(self)

        # config aliases
        self.app.add_typer(
            self.config_app.app, 
            name="config",  
            short_help="Config commands, aliases: `c`, `conf`",
            no_args_is_help=True,
        )
        self.app.add_typer(
            self.config_app.app, name="c", hidden=True, no_args_is_help=True,
        )
        self.app.add_typer(
            self.config_app.app, name="conf", hidden=True, no_args_is_help=True,
        )

        # pod aliases
        self.app.add_typer(
            self.pod_app.app,
            name="pod",
            short_help="Pod commands, aliases: `p`",
            no_args_is_help=True,
        )
        self.app.add_typer(
            self.pod_app.app, name="p", hidden=True, no_args_is_help=True,
        )

        # template aliases
        self.app.add_typer(
            self.template_app.app,
            name="template",
            short_help="Template commands, aliases: `t`, `tpl`",
            no_args_is_help=True,
        )
        self.app.add_typer(
            self.template_app.app, name="t", hidden=True, no_args_is_help=True,
        )
        self.app.add_typer(
            self.template_app.app, name="tpl", hidden=True, no_args_is_help=True,
        )

        # pay aliases
        self.app.command("pay")(self.pay_app.pay)

        # lium aliases
        self.app.command("init")(self.lium_app.init)

        # theme command (simple, no aliases for now)
        self.app.add_typer(
            self.theme_app.app,
            name="theme",
            short_help="Manage CLI themes (placeholder)",
            no_args_is_help=True,
        )

        # ssh commands
        self.app.add_typer(
            self.ssh_app.app,
            name="ssh",
            short_help="SSH related commands (placeholder)",
            no_args_is_help=True,
        )

        # lium commands
        self.app.add_typer(
            self.lium_app.app,
            name="lium",
            short_help="Lium related commands",
            no_args_is_help=True,
        )
        
    def main_callback(
        self,
        version: Annotated[
            Optional[bool],
            typer.Option(
                "--version", callback=version_callback, help="Show Lium CLI version"
            ),
        ] = None,
        commands: Annotated[
            Optional[bool],
            typer.Option(
                "--commands", callback=commands_callback, help="Show Lium CLI commands"
            ),
        ] = None,
    ):
        """
        Command line interface (CLI) for Lium. Uses the values in the configuration file. These values can be
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
        root = Tree("[bold magenta]Lium CLI Commands[/]")  # Root node
        build_rich_tree(groups_and_commands, root)
        return root

    def run(self):
        self.app()