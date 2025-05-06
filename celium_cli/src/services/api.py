from typing import TYPE_CHECKING
import requests

if TYPE_CHECKING:
    from celium_cli.src.cli_manager import CLIManager


class APIClient:
    cli_manager: "CLIManager" = None

    def __init__(self):
        pass

    @property
    def api_key(self):
        return self.cli_manager.config_app.config["api_key"]
    
    @property
    def base_url(self):
        return self.cli_manager.config_app.config["server_url"]

    def set_cli_manager(self, cli_manager: "CLIManager"):
        self.cli_manager = cli_manager

    def get_auth_headers(self, require_auth: bool = True):
        return {"X-API-Key": self.api_key} if require_auth else {}

    def get(self, endpoint: str, params: dict = None, require_auth: bool = True):
        url = f"{self.base_url}/api/{endpoint}"
        response = requests.get(url, headers=self.get_auth_headers(require_auth), params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict = None, json: dict = None, require_auth: bool = True):
        url = f"{self.base_url}/api/{endpoint}"
        response = requests.post(url, headers=self.get_auth_headers(require_auth), data=data, json=json)
        response.raise_for_status()
        return response.json()


api_client = APIClient()