import typer
from celium_cli.src.apps import BaseApp, TemplateBaseArguments
from celium_cli.src.decorator import catch_validation_error
from celium_cli.src.services.template import create_template
from celium_cli.src.services.validator import validate_for_docker_build


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
    ):
        """
        Create a new template.

        This command allows you to create a new template by building a docker image from a Dockerfile.

        [bold]USAGE[/bold]: 
            [green]$[/green] celium template create --dockerfile Dockerfile --docker-image daturaai/dind:latest
        """
        # Validate if all configs are set for docker build
        validate_for_docker_build(self.cli_manager)

        # Create the template
        create_template(docker_image, dockerfile)
