from celium_cli.src.cli_manager import CLIManager
from celium_cli.src.services.api import api_client


def main():
    manager = CLIManager()
    api_client.set_cli_manager(manager)
    manager.run()


if __name__ == "__main__":
    main()

