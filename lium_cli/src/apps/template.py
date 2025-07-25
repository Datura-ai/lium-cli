import typer
from lium_cli.src.apps import BaseApp, TemplateBaseArguments
from lium_cli.src.decorator import catch_validation_error
from lium_cli.src.services.docker_credential import get_docker_credential
from lium_cli.src.services.template import create_template
from rich.prompt import Prompt, Confirm
import random
import string
from lium_cli.src.styles import style_manager


class Arguments(TemplateBaseArguments):
    pass


class TemplateApp(BaseApp):
    def run(self):
        self.app.command("create")(self.create_template)

    @catch_validation_error
    def create_template(
        self, 
        dockerfile: str = Arguments.dockerfile,
        docker_image: str = Arguments.docker_image,
        is_docker_image_required: bool = True
    ):
        """
        Create a new template.

        This command allows you to create a new template by building a docker image from a Dockerfile 
        or using an existing image from Docker Hub.

        [bold]USAGE[/bold]: 
            [green]$[/green] lium template create --dockerfile Dockerfile --docker-image yourrepo/yourimage:tag
            [green]$[/green] lium template create --docker-image yourrepo/yourimage:tag (uses existing image from DockerHub)
            [green]$[/green] lium template create --dockerfile Dockerfile (builds and uses a temporary local image)
            [green]$[/green] lium template create (interactive prompt)
        """

        # Check if running in interactive mode (no direct dockerfile or docker_image args)
        # Use strip to handle cases where empty strings might be passed from CLI defaults
        run_interactive_mode = not (dockerfile or '').strip() and not (docker_image or '').strip()

        if run_interactive_mode:
            style_manager.console.print(
                "[bold cyan]Interactive Template Creation[/bold cyan]\n"
                "You can create a template by:\n"
                "1. Providing a Dockerfile to build a new image, or\n"
                "2. Using an existing Docker image from a registry (e.g., Docker Hub)."
            )

            # Attempt to get Dockerfile information
            if Confirm.ask("\n[bold magenta]?[/bold magenta] Would you like to use a Dockerfile to build a local image?", default=True, console=style_manager.console):
                df_path_input = Prompt.ask("  Enter the path to your Dockerfile", default="Dockerfile", console=style_manager.console)
                if df_path_input and df_path_input.strip():
                    dockerfile = df_path_input.strip()
                else:
                    style_manager.console.print("[yellow]  Info:[/yellow] No Dockerfile path provided or path was empty.")

            # Get docker hub credential
            _, docker_username, _ = get_docker_credential()
            
            # Handle docker_image based on Dockerfile presence and is_docker_image_required
            if (dockerfile or '').strip():
                # Dockerfile IS provided
                if is_docker_image_required:
                    style_manager.console.print("[bold cyan]A Docker image name is required for this operation.[/bold cyan]")
                    docker_image_name_input = Prompt.ask(
                        f"  Enter the Docker image name (e.g., '{docker_username}/yourimage:tag')",
                        console=style_manager.console
                    )
                    if docker_image_name_input and docker_image_name_input.strip():
                        docker_image = docker_image_name_input.strip()
                    else:
                        style_manager.console.print("[yellow]  Info:[/yellow] No Docker image name provided or name was empty.")
                else: # Docker image is optional
                    docker_image_name_input = Prompt.ask(
                        f"  Enter the Docker image name to use for pushing to Docker Hub (e.g., '{docker_username}/yourimage:tag') [Optional]",
                        console=style_manager.console,
                        default=""
                    )
                    if docker_image_name_input and docker_image_name_input.strip():
                        docker_image = docker_image_name_input.strip()
            else:
                # No Dockerfile was provided
                if is_docker_image_required:
                    style_manager.console.print("[bold cyan]A Docker image is required as no Dockerfile will be used.[/bold cyan]")
                    docker_image_name_input = Prompt.ask(
                        f"  Enter the Docker image name (e.g., '{docker_username}/ubuntu:latest' or '{docker_username}/yourimage:tag')",
                        console=style_manager.console
                    )
                    if docker_image_name_input and docker_image_name_input.strip():
                        docker_image = docker_image_name_input.strip()
                    else:
                        style_manager.console.print("[yellow]  Info:[/yellow] No Docker image name provided or name was empty. This is required if no Dockerfile is used.")
                else: # Docker image not strictly required by flag, but needed if no Dockerfile
                    style_manager.console.print("[bold yellow]Info:[/bold yellow] No Dockerfile specified.")
                    if Confirm.ask("[bold magenta]?[/bold magenta] Would you like to use an existing Docker image from Docker Hub instead?", default=True, console=style_manager.console):
                        docker_image_name_input = Prompt.ask(
                            f"  Enter the Docker image name (e.g., '{docker_username}/ubuntu:latest' or '{docker_username}/yourimage:tag')",
                            console=style_manager.console
                        )
                        if docker_image_name_input and docker_image_name_input.strip():
                            docker_image = docker_image_name_input.strip()
                        else:
                            style_manager.console.print("[yellow]  Info:[/yellow] No Docker image name provided or name was empty.")
                    # If user says No here, and no Dockerfile, final validation will catch it.

        # Final Validation (applies after interactive prompts or if CLI args were used directly)
        current_dockerfile_val = (dockerfile or '').strip()
        current_docker_image_val = (docker_image or '').strip()

        if is_docker_image_required:
            if not current_docker_image_val:
                style_manager.console.print("[bold red]Error:[/bold red] A Docker image is required for this operation but was not provided or was empty.")
                if not current_dockerfile_val:
                    style_manager.console.print("       Additionally, no Dockerfile was specified.")
                raise typer.Exit(code=1)
        else: # is_docker_image_required is False (docker_image is optional)
            # We need AT LEAST dockerfile OR docker_image.
            if not current_dockerfile_val and not current_docker_image_val:
                style_manager.console.print("[bold red]Error:[/bold red] Operation cancelled. Insufficient information provided.")
                style_manager.console.print("You must provide either a Dockerfile path or a Docker image name.")
                raise typer.Exit(code=1)

        # Prepare values for create_template service call (None if empty/whitespace)
        final_docker_image = current_docker_image_val if current_docker_image_val else None
        final_dockerfile = current_dockerfile_val if current_dockerfile_val else None
        
        create_template(final_docker_image, final_dockerfile)
