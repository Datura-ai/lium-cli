# This file is intentionally left blank.

from typing import TYPE_CHECKING
import typer

from celium_cli.src.const import EPILOG

if TYPE_CHECKING:
    from celium_cli.src.cli_manager import CLIManager


class TemplateBaseArguments:
    dockerfile: str = typer.Option(
        None,
        "--dockerfile",
        "--dockerfile-path",
        help="The path to the Dockerfile to use for the pod",
    )
    docker_image: str = typer.Option(
        None,
        "--docker-image",
        "--dockerimage",
        "--docker_image",
        "--docker.image",
        help="The name of the Docker image to use for the pod",
    )


class BaseApp:
    app: typer.Typer

    def __init__(self, cli_manager: "CLIManager"):
        self.cli_manager = cli_manager
        self.app = typer.Typer(epilog=EPILOG)
        self.run()

    def run(self):
        pass
