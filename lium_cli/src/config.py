class Defaults:
    class config:
        path = "~/.lium/config.yaml"
        base_path = "~/.lium"
        dictionary = {
            "docker_username": None,
            "docker_password": None,
            "api_key": None,
            "server_url": "https://lium.io",
            "tao_pay_url": "https://pay-api.lium.io",
            "network": "finney",
        }

defaults = Defaults