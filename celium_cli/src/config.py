class Defaults:
    class config:
        path = "~/.celium/config.yaml"
        base_path = "~/.celium"
        dictionary = {
            "docker_username": None,
            "docker_password": None,
            "api_key": None,
            "server_url": "https://celiumcompute.ai",
            "tao_pay_url": "https://pay-api.celiumcompute.ai",
            "network": "finney",
        }

defaults = Defaults