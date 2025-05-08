import typer
from celium_cli.src.apps import BaseApp, TemplateBaseArguments
from celium_cli.src.decorator import catch_validation_error
from celium_cli.src.services.docker import build_and_push_docker_image_from_dockerfile
from celium_cli.src.services.executor import get_executors_and_print_table, rent_executor
from celium_cli.src.services.template import create_template
from celium_cli.src.services.validator import validate_for_api_key, validate_for_docker_build, validate_machine_name
from celium_cli.src.utils import console

class Arguments(TemplateBaseArguments):
    machine: str = typer.Option(
        ...,
        "--machine",
        "--machine-name",
        help="The name of the machine to run the pod on",
    )
    ssh_key_path: str = typer.Option(
        None,
        "--ssh-key-path",
        "--ssh-key",
        help="The path to the SSH key to use for the pod",
    )
    

class PodApp(BaseApp):
    def run(self):
        self.app.command("run")(self.run_pod)

    @catch_validation_error
    def run_pod(
        self,
        machine: str = Arguments.machine,
        docker_image: str = Arguments.docker_image,
        dockerfile: str = Arguments.dockerfile,
        ssh_key_path: str = Arguments.ssh_key_path,
    ):
        """
        Run a pod on a machine.

        This command allows you to run a pod on the celium platform.

        [bold]USAGE[/bold]: 
            [green]$[/green] celium pod run --machine 8XA100 --docker-image daturaai/dind:latest
        """
        validate_for_api_key(self.cli_manager)
        count, machine_name = validate_machine_name(machine)

        if dockerfile:
            # Validate if all configs are set for docker build
            validate_for_docker_build(self.cli_manager)
            # Build and push the docker image
            create_template(docker_image, dockerfile)
        else:
            console.print("[bold yellow]ℹ[/bold yellow] No [blue]Dockerfile[/blue] provided, [italic]skipping build[/italic]. \n\n\n")
        
        executors = get_executors_and_print_table(count, machine_name)
        if len(executors) == 0:
            console.print("[bold yellow]Warning:[/bold yellow] No executors found, please try again later.")
            return
        
        executor = executors[0]
        console.print(f"\n\n [bold blue]Deploying a pod[/bold blue] on machine: [green]{executor['id']}[/green] \n\n")
        rent_executor(executor["id"], docker_image, ssh_key_path)


        
        
        