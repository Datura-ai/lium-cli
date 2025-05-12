import asyncio
from bittensor_cli.src.commands import wallets
from celium_cli.src.services.api import api_client, tao_pay_client


def get_tao_pay_info() -> tuple[str, str]:
    transfer_url = api_client.post(
        "tao/create-transfer", json={"amount": 10}
    )["url"]
    # Extract app_id from transfer URL query parameters
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(transfer_url)
    query_params = parse_qs(parsed_url.query)
    app_id = query_params.get('app_id', [''])[0]

    # Get app from tao_pay_api server
    app = tao_pay_client.get(f"wallet/company", params={"app_id": app_id})
    return (app["application_id"], app["wallet_hash"])


def wallet_transfer(wallet, subtensor, destination, amount):
    asyncio.run(wallets.transfer(
        wallet=wallet,
        subtensor=subtensor,
        destination=destination,
        amount=amount,
        transfer_all=False,
        era=3, 
        prompt=True,
        json_output=False,
    ))