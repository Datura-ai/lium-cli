from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from celium_cli.src.cli_manager import CLIManager


class ValidationError(Exception):
    pass


def validate_for_docker_build(cli_manager: "CLIManager") -> bool:
    if not cli_manager.config_app.config["docker_username"]:
        raise ValidationError(
            (
                "The [bold green]docker_username[/bold green] is not set."
                "Please set it using the [bold green]celium config set --docker-username[/bold green] command."
            )
        )
    if not cli_manager.config_app.config["docker_password"]:
        raise ValidationError(
            (
                "The [bold green]docker_password[/bold green] is not set."
                "Please set it using the [bold green]celium config set --docker-password[/bold green] command."
            )
        )
    return True


def validate_for_api_key(cli_manager: "CLIManager") -> bool:
    if not cli_manager.config_app.config["api_key"]:
        raise ValidationError(
            (
                "The [bold green]api_key[/bold green] is not set."
                "Please set it using the [bold green]celium config set --api-key[/bold green] command."
            )
        )
    return True
