from typing import TYPE_CHECKING

from lium_cli.src.utils import find_machine_from_keyword

if TYPE_CHECKING:
    from lium_cli.src.cli_manager import CLIManager


class ValidationError(Exception):
    pass


def validate_for_docker_build(cli_manager: "CLIManager") -> bool:
    if not cli_manager.config_app.config["docker_username"]:
        raise ValidationError(
            (
                "The [bold green]docker_username[/bold green] is not set."
                "Please set it using the [bold green]lium-cli config set --docker-username[/bold green] command."
            )
        )
    if not cli_manager.config_app.config["docker_password"]:
        raise ValidationError(
            (
                "The [bold green]docker_password[/bold green] is not set."
                "Please set it using the [bold green]lium-cli config set --docker-password[/bold green] command."
            )
        )
    return True


def validate_for_api_key(cli_manager: "CLIManager") -> bool:
    if not cli_manager.config_app.config["api_key"]:
        raise ValidationError(
            (
                "The [bold green]api_key[/bold green] is not set."
                "Please set it using the [bold green]lium-cli config set --api-key[/bold green] command."
            )
        )
    return True


def validate_machine_name(machine_name: str) -> tuple[int, str]:
    count, machine_keyword = machine_name.lower().split("x")
    if not count.isdigit():
        raise ValidationError(
            (
                "The [bold green]machine_name[/bold green] must be a number followed by a machine keyword."
            )
        )
    
    machine_name = find_machine_from_keyword(machine_keyword)
    if not machine_name:
        raise ValidationError(
            (
                "The [bold green]machine_name[/bold green] must be a valid machine name."
            )
        )
    return count, machine_name