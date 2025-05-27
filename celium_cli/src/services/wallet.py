from bittensor_wallet import Wallet
from rich.table import Table
from bittensor_cli import CLIManager
from bittensor_cli.src.commands import wallets
from bittensor_cli.src import (
    WalletOptions as WO,
    WalletValidationTypes as WV,
)
from celium_cli.src.services.api import tao_pay_client
from celium_cli.src.styles import style_manager


def get_client_wallets(customer_id: str) -> list[str]:
    with style_manager.console.status("Getting client wallets...", spinner="monkey") as status:
        wallets = tao_pay_client.get(f"wallet/available-wallets/{customer_id}")

    # Print wallets table
    if len(wallets) > 0:
        table = Table(title="Available Wallets")
        table.add_column("Wallet Hash", style="bold green")

        for wallet in wallets:
            table.add_row(wallet["wallet_hash"])

        style_manager.console.print(table)
    return wallets


def create_client_wallet(wallet: Wallet, app_id: str, customer_id: str) -> str:
    # Generate a signature for the wallet
    # Step 1: Get access token from tao pay api server. 
    access_token = tao_pay_client.get("token/generate")["access_key"]
    
    # Step 2: Sign the access token
    keypair = wallet.coldkey
    signed_message = keypair.sign(access_token.encode("utf-8")).hex()

    style_manager.console.print(f"Signed message: {signed_message}")

    # call verify endpoint
    tao_pay_client.post("token/verify", json={
        "coldkey_address": keypair.ss58_address,
        "access_key": access_token,
        "signature": signed_message,
        "stripe_customer_id": customer_id,
        "application_id": app_id
    })

    wallets = get_client_wallets(customer_id)
    if len(wallets) == 0:
        raise Exception("Failed to create wallet")
    
    return keypair.ss58_address


def create_potential_transfer(from_wallet: str, to_wallet: str, amount_tao: float, amount_usd: float, rate: float, customer_id: str): 
    tao_pay_client.post("wallet/potential-transfer", json={
        "amount_tao": float(amount_tao),
        "amount_usd": float(amount_usd),
        "rate": float(rate),
        "from_wallet": from_wallet,
        "to_wallet": to_wallet,
        "stripe_customer_id": customer_id,
    })
