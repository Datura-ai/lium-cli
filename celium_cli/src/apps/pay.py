import typer
import asyncio
from bittensor_cli.cli import CLIManager
from bittensor_cli.src.commands import wallets
from bittensor_cli.src import (
    WalletOptions as WO,
    WalletValidationTypes as WV,
)
from rich.table import Table
from celium_cli.src.apps import BaseApp
from celium_cli.src.services.tao import get_tao_pay_info
from celium_cli.src.services.user import get_customer_id
from celium_cli.src.services.wallet import get_client_wallets, create_client_wallet, create_potential_transfer
from celium_cli.src.styles import style_manager
from celium_cli.src.services.api import tao_pay_client
from celium_cli.src.services.tao import wallet_transfer


class Arguments:
    wallet_name = typer.Option(
        None,
        "--wallet-name",
        "--name",
        "--wallet_name",
        "--wallet.name",
        help="Name of the wallet.",
        prompt=True,
    )
    wallet_path = typer.Option(
        None,
        "--wallet-path",
        "-p",
        "--wallet_path",
        "--wallet.path",
        help="Path where the wallets are located. For example: `/Users/btuser/.bittensor/wallets`.",
    )


class PayApp(BaseApp):
    def run(self):
        pass

    def pay(
        self,
        wallet_name: str = Arguments.wallet_name,
        wallet_path: str = Arguments.wallet_path,
        amount: float = typer.Option(
            0.0, "--amount", help="The amount of USD to transfer", prompt="Amount in USD"
        ),
        jwt_token: str | None = None
    ):
        cli_manager = CLIManager()
        app_id, to_wallet = get_tao_pay_info(jwt_token)
        customer_id = get_customer_id(jwt_token)

        if not customer_id:
            style_manager.console.print("No customer ID found. Please sign up for a Celium account to continue.", style="error")
            raise typer.Abort()
        
        if amount == 0 or amount is None:
            amount = typer.prompt("Amount in USD", type=float)

        style_manager.console.print("Asking for wallet...", style="info")
        wallet = cli_manager.wallet_ask(
            wallet_name, wallet_path, wallet_hotkey=None, 
            ask_for=[WO.NAME, WO.PATH], validate=WV.WALLET
        )
        keypair = wallet.coldkey
        ss58_address = keypair.ss58_address

        # Get or create a client wallet
        wallets = get_client_wallets(customer_id, ss58_address)
        if len(wallets) == 0:
            wallet_hash = create_client_wallet(keypair, app_id, customer_id)
        else:
            wallet_hash = wallets[0]["wallet_hash"]
        
        response = tao_pay_client.get("balance/convert", params={"amount": amount})
        amount_tao = float(response["converted"])
        rate = float(response["rate"]) 

        table = Table(title="Transfer Details")
        table.add_column("Amount", style="bold green")
        table.add_column("Amount in TAO", style="bold yellow")
        table.add_column("Rate", style="bold blue")
        table.add_column("To Wallet", style="bold magenta")
        table.add_column("Network", style="bold cyan")
        table.add_row(str(amount), str(amount_tao), str(rate), to_wallet, self.cli_manager.config_app.config["network"])
        style_manager.console.print(table)

        # Ask for confirmation before proceeding
        if not typer.confirm("Do you want to proceed with this transfer?"):
            style_manager.console.print("Transfer cancelled by user.", style="warning")
            raise typer.Abort()

        # Create a potential transfer
        create_potential_transfer(wallet_hash, to_wallet, amount_tao, amount, rate, customer_id)

        # Transfer tao amount.
        subtensor = cli_manager.initialize_chain(
            [self.cli_manager.config_app.config["network"]]
        )
        style_manager.console.print("Initiating transfer...", style="info")
        try:
            wallet_transfer(wallet, subtensor, to_wallet, amount_tao)
            style_manager.console.print(f"Successfully transferred {amount_tao} TAO to {to_wallet}.", style="success")
        except Exception as e:
            style_manager.console.print(f"Transfer failed: {e}", style="error")
            raise typer.Abort()
        