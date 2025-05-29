import requests
from celium_cli.src.services.api import api_client


def get_customer_id(jwt_token: str | None = None) -> str:
    response = api_client.get("users/me", auth_heads={"Authorization": f"Bearer {jwt_token}"} if jwt_token else None)
    return response["stripe_customer_id"]


def signup(name: str, email: str, password: str) -> None:
    api_client.post("users", json={"name": name, "email": email, "password": password})


def login(email: str, password: str) -> str:
    response = api_client.post("users/login", json={"email": email, "password": password})
    return response["token"]


def get_email_verified(token: str) -> bool:
    response = api_client.get("users/me", auth_heads={"Authorization": f"Bearer {token}"})
    return response["email_verified"]


def create_api_key(token: str) -> None:
    response = api_client.post("keys", auth_heads={"Authorization": f"Bearer {token}"})
    return response["key"]


def get_or_create_api_key(token: str) -> str:
    api_keys = api_client.get("keys", auth_heads={"Authorization": f"Bearer {token}"})
    if len(api_keys) == 0:
        return create_api_key(token)
    else:
        return api_keys[0]["key"]


