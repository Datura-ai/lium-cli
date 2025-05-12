from celium_cli.src.services.api import api_client


def get_customer_id() -> str:
    response = api_client.get("users/me")
    return response["stripe_customer_id"]
