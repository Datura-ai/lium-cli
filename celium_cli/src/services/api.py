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
    
    def get_api_url(self, endpoint: str) -> str:
        return f"{self.base_url}/api/{endpoint}"

    def set_cli_manager(self, cli_manager: "CLIManager"):
        self.cli_manager = cli_manager

    def get_auth_headers(self, require_auth: bool = True):
        return {"X-API-Key": self.api_key} if require_auth else {}

    def get(self, endpoint: str, params: dict = None, require_auth: bool = True, auth_heads: None | dict = None):
        url = self.get_api_url(endpoint)
        response = requests.get(url, headers=self.get_auth_headers(require_auth) if auth_heads is None else auth_heads, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict = None, json: dict = None, require_auth: bool = True, auth_heads: None | dict = None):
        url = self.get_api_url(endpoint)
        response = requests.post(url, headers=self.get_auth_headers(require_auth) if auth_heads is None else auth_heads, data=data, json=json)
        response.raise_for_status()
        return response.json()
    
    def delete(self, endpoint: str, require_auth: bool = True):
        url = self.get_api_url(endpoint)
        response = requests.delete(url, headers=self.get_auth_headers(require_auth))
        response.raise_for_status()
        return response.json()
    

class TaoPayClient(APIClient):
    @property
    def base_url(self):
        return self.cli_manager.config_app.config["tao_pay_url"]
    
    def get_api_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

    def get_auth_headers(self, require_auth: bool = True):
        return {"X-Api-Key": "admin-test-key"} if require_auth else {}


api_client = APIClient()
tao_pay_client = TaoPayClient()