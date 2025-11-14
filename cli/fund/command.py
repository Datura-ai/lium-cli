"""Fund account command."""

from typing import Optional

import click
from rich.prompt import Prompt

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from cli.settings import config
from . import validation
from .actions import (
    LoadWalletAction,
    CheckWalletRegistrationAction,
    ExecuteTransferAction,
)


@click.command("fund")
@click.option("--wallet", "-w", help="Bittensor wallet name")
@click.option("--amount", "-a", help="Amount of TAO to fund")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@handle_errors
def fund_command(wallet: Optional[str], amount: Optional[str], yes: bool):
    """Fund your Lium account with TAO from Bittensor wallet.

    \b
    Examples:
      lium fund                          # Interactive mode
      lium fund -w default -a 1.5        # Fund with specific wallet and amount
      lium fund -w mywal -a 0.5 -y       # Skip confirmation
    """
    # Import bittensor here to handle missing dependency gracefully
    try:
        import bittensor as bt
    except ImportError:
        ui.error("Bittensor library not installed")
        ui.dim("Install with: pip install bittensor")
        return

    # Get wallet name
    if not wallet:
        default_wallet = config.get('funding.default_wallet', 'default')
        wallet_name = Prompt.ask("Bittensor wallet name", default=default_wallet).strip()
    else:
        wallet_name = wallet

    # Load wallet first to verify it exists
    action = LoadWalletAction()
    result = action.execute({"bt": bt, "wallet_name": wallet_name})

    if not result.ok:
        ui.error(f"Failed to load wallet '{wallet_name}': {result.error}")
        return

    bt_wallet = result.data["wallet"]
    wallet_address = result.data["address"]

    # Initialize Lium SDK
    lium = Lium()

    # Check/register wallet
    ctx = {
        "lium": lium,
        "wallet_address": wallet_address,
        "bt_wallet": bt_wallet
    }

    action = CheckWalletRegistrationAction()
    result = ui.load("Checking wallet registration", lambda: action.execute(ctx))

    if not result.ok:
        ui.error(f"Failed to register wallet: {result.error}")
        return

    # Get amount after wallet is verified
    if not amount:
        amount_str = Prompt.ask("Enter TAO amount to fund").strip()
    else:
        amount_str = amount

    tao_amount, error = validation.validate_amount(amount_str)
    if error:
        ui.error(error)
        return

    # Get current balance
    current_balance = ui.load("Loading balance", lambda: lium.balance())

    ui.info(f"Current balance: {current_balance} USD")

    # Confirmation
    if not yes:
        if not ui.confirm(f"Fund account with {tao_amount} TAO?", default=False):
            return

    ui.info("Waiting for bittensor...")
    # Execute transfer
    ctx = {
        "bt": bt,
        "bt_wallet": bt_wallet,
        "tao_amount": tao_amount
    }

    action = ExecuteTransferAction()
    result = action.execute(ctx)

    if not result.ok:
        ui.error(f"Transfer failed: {result.error}")
        return

    ui.info("Done.")
