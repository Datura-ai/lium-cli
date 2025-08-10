"""Main CLI entry point for Lium."""
import click
from .commands.ls import ls_command
from .commands.templates import templates_command
from .commands.up import up_command
from .commands.ps import ps_command
from .commands.exec import exec_command
from .commands.ssh import ssh_command
from .commands.rm import rm_command
from .commands.compose import compose_command
from .plugins import load_plugins


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Lium CLI - Unix-style GPU pod management.
    
    A clean, Unix-style command-line interface for managing GPU pods.
    Run individual commands or use 'lium --help' to see all available commands.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register core commands
cli.add_command(ls_command)
cli.add_command(templates_command)
cli.add_command(up_command)
cli.add_command(ps_command)
cli.add_command(exec_command)
cli.add_command(ssh_command)
cli.add_command(rm_command)

# Add compose placeholder (will be overridden if plugin is installed)
cli.add_command(compose_command)

# Load any installed plugins
# Plugins can override existing commands or add new ones
load_plugins(cli)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()