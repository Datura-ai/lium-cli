from bittensor_wallet import Keypair, Wallet
from rich.table import Table
from bittensor_cli import CLIManager
from bittensor_cli.src.commands import wallets
from bittensor_cli.src import (
    WalletOptions as WO,
    WalletValidationTypes as WV,
)
from lium_cli.src.services.api import tao_pay_client
from lium_cli.src.styles import style_manager


def get_client_wallets(customer_id: str, coldkey_ss58_address: str) -> list[str]:
    with style_manager.console.status("Getting client wallets...", spinner="monkey") as status:
        wallets = tao_pay_client.get(f"wallet/available-wallets/{customer_id}")
        wallets = [_wallet for _wallet in wallets if _wallet["wallet_hash"] == coldkey_ss58_address]

    # Print wallets table
    if len(wallets) > 0:
        table = Table(title="Available Wallets")
        table.add_column("Wallet Hash", style="bold green")

        for wallet in wallets:
            table.add_row(wallet["wallet_hash"])

        style_manager.console.print(table)

    if len(wallets) == 0:
        style_manager.console.print("Warning: No wallets found for the given customer ID and coldkey address.", style="warning")
    return wallets


def create_client_wallet(keypair: Keypair, app_id: str, customer_id: str) -> str:
    # Generate a signature for the wallet
    # Step 1: Get access token from tao pay api server. 
    style_manager.console.print("Creating new client wallet...", style="info")
    style_manager.console.print("Step 1: Requesting access token...", style="info")
    access_token = tao_pay_client.get("token/generate")["access_key"]
    style_manager.console.print(f"Access token received: {access_token}", style="dim")
    
    # Step 2: Sign the access token
    style_manager.console.print("Step 2: Signing access token with your wallet's coldkey...", style="info")
    signed_message = keypair.sign(access_token.encode("utf-8")).hex()

    style_manager.console.print(f"Signed message: {signed_message}", style="dim")

    # call verify endpoint
    style_manager.console.print("Step 3: Verifying signature with the server...", style="info")
    tao_pay_client.post("token/verify", json={
        "coldkey_address": keypair.ss58_address,
        "access_key": access_token,
        "signature": signed_message,
        "stripe_customer_id": customer_id,
        "application_id": app_id
    })

    wallets = get_client_wallets(customer_id, keypair.ss58_address)
    if len(wallets) == 0:
        style_manager.console.print("Failed to create and verify client wallet.", style="error")
        raise Exception("Failed to create wallet")
    
    style_manager.console.print(f"Successfully created and verified client wallet: {keypair.ss58_address}", style="success")
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
