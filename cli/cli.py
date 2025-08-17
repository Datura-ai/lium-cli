"""Main CLI entry point for Lium."""
import click
from importlib.metadata import version, PackageNotFoundError
from .themed_console import ThemedConsole
from .commands.init import init_command
from .commands.ls import ls_command
from .commands.templates import templates_command
from .commands.up import up_command
from .commands.ps import ps_command
from .commands.exec import exec_command
from .commands.ssh import ssh_command
from .commands.rm import rm_command
from .commands.scp import scp_command
from .commands.rsync import rsync_command
from .commands.theme import theme_command
# from .commands.compose import compose_command  # Disabled for beta.1
from .commands.config import config_command
# from .commands.image import image_command  # Disabled for beta.1
from .commands.fund import fund_command
from .plugins import load_plugins


def get_version():
    """Get version from package metadata."""
    try:
        return version("lium-cli")
    except PackageNotFoundError:
        return "unknown"


@click.group(invoke_without_command=True)
@click.version_option(version=get_version(), prog_name="lium")
@click.pass_context
def cli(ctx):
    """Lium CLI - Unix-style GPU pod management.
    
    A clean, Unix-style command-line interface for managing GPU pods.
    Run individual commands or use 'lium --help' to see all available commands.
    """
    # Make ThemedConsole available to all commands via context
    ctx.ensure_object(dict)
    ctx.obj['console'] = ThemedConsole()
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register core commands
cli.add_command(init_command)
cli.add_command(ls_command)
cli.add_command(templates_command)
cli.add_command(up_command)
cli.add_command(ps_command)
cli.add_command(exec_command)
cli.add_command(ssh_command)
cli.add_command(rm_command)
cli.add_command(scp_command)
cli.add_command(rsync_command)
cli.add_command(theme_command)
cli.add_command(config_command)
# cli.add_command(image_command)  # Disabled for beta.1
cli.add_command(fund_command)

# Add compose placeholder (will be overridden if plugin is installed)
# cli.add_command(compose_command)  # Disabled for beta.1

# Load any installed plugins
# Plugins can override existing commands or add new ones
load_plugins(cli)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()