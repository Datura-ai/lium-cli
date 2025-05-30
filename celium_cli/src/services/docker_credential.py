from celium_cli.src.services.api import api_client
from celium_cli.src.styles import style_manager


def get_docker_credential() -> tuple[str, str, str]:
    docker_credentials = list_credentials()
    if len(docker_credentials) > 0:
        style_manager.console.print(f"[bold green]Using existing docker credential: {docker_credentials[0]['username']}[/bold green]")
        return docker_credentials[0]["id"], docker_credentials[0]["username"], docker_credentials[0]["password"] 
    # Create a new docker credential
    docker_credential = api_client.post("docker-credentials/")
    style_manager.console.print(f"[bold green]Created new docker credential: {docker_credential['username']}[/bold green]")
    return docker_credential["id"], docker_credential["username"], docker_credential["password"]


def list_credentials() -> list[dict]:
    return api_client.get("docker-credentials")


def create_docker_credential(username: str, password: str):
    docker_credential = api_client.post("docker-credentials/", json={
        "docker_username": username,
        "docker_password": password
    })
    style_manager.console.print(f"[bold green]Created new docker credential: {docker_credential['username']}[/bold green]")
    return docker_credential["id"], docker_credential["username"], docker_credential["password"]