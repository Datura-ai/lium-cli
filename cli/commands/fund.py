"""Fund account command."""
from __future__ import annotations

import os
import sys
import time
from typing import Optional

import click
from rich.prompt import Prompt, Confirm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium
from ..utils import console, handle_errors, loading_status
from ..config import config

# Constants
LIUM_FUNDING_ADDRESS = "5FqACMtcegZxxopgu1g7TgyrnyD8skurr9QDPLPhxNQzsThe"  # Official Lium funding address
FUNDING_TIMEOUT = 300  # 5 minutes timeout for balance update


def validate_amount(amount_str: str) -> float:
    """Validate and return TAO amount."""
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return amount
    except ValueError as e:
        if "could not convert" in str(e):
            raise ValueError("Invalid amount format")
        raise e


def ask_tao_amount() -> float:
    """Ask user for TAO amount with validation loop."""
    amount_str = Prompt.ask(console.get_styled("Enter TAO amount to fund", "info")).strip()
    return validate_amount(amount_str)


@click.command("fund")
@click.option("--wallet", "-w", help="Bittensor wallet name")
@click.option("--amount", "-a", help="Amount of TAO to fund")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@handle_errors
def fund_command(wallet: Optional[str], amount: Optional[str], yes: bool):
    """
    \b
    Fund your Lium account with TAO from Bittensor wallet.
    Examples:
      lium fund                          # Interactive mode
      lium fund -w default -a 1.5        # Fund with specific wallet and amount
      lium fund -w mywal -a 0.5 -y       # Skip confirmation
    """
    # Import bittensor here to handle missing dependency gracefully
    try:
        import bittensor as bt
    except ImportError:
        console.error("Bittensor library not installed")
        console.dim("Install with: pip install bittensor")
        return

    # Initialize SDK
    lium = Lium()
    
    # Get parameters
    wallet_name = wallet or config.get_or_ask('funding.default_wallet', 'Bittensor wallet name', default='default')
    tao_amount = validate_amount(amount) if amount else ask_tao_amount()
    
    # Create Bittensor wallet and get address
    with loading_status("Loading wallet", "Wallet loaded"):
        try:
            bt_wallet = bt.wallet(wallet_name)
            wallet_address = bt_wallet.coldkeypub.ss58_address
        except Exception as e:
            raise RuntimeError(f"Failed to load wallet '{wallet_name}': {e}")
    
    # Check current balance
    with loading_status("Getting current lium balance", ""):
        current_balance = lium.balance()
    
    console.info(f"Current balance: {console.get_styled(f'{current_balance} USD', 'success')}")
    console.info(f"Wallet ({wallet_name}) address: {console.get_styled(wallet_address, 'id')}")
    
    # Confirmation
    if not yes:
        fund_msg = f"Fund account with {console.get_styled(f'{tao_amount} TAO', 'info')}?"
        if not Confirm.ask(fund_msg, default=False):
            console.warning("Funding cancelled")
            return
    
    # Check/register wallet with Lium
    with loading_status("Checking wallet registration", "Wallet verified"):
        try:
            user_wallets = lium.wallets()
            wallet_addresses = [w.get('wallet_hash', '') for w in user_wallets]
            
            if wallet_address not in wallet_addresses:
                console.info("Linking wallet with your account...")
                lium.add_wallet(bt_wallet)
                time.sleep(2)  # Allow registration to complete
        except Exception as e:
            raise RuntimeError(f"Failed to register wallet: {e}")
    
    # Execute transfer
    with loading_status("Processing TAO transfer", "Transfer initiated"):
        try:
            bt.subtensor().transfer(
                wallet=bt_wallet,
                dest=LIUM_FUNDING_ADDRESS,
                amount=bt.Balance.from_tao(tao_amount)
            )
        except Exception as e:
            raise RuntimeError(f"Transfer failed: {e}")
    
    # Wait for balance update with timeout
    console.info("Waiting for balance update...")
    start_time = time.time()

    with loading_status("Waiting balance update", "Balance updated"):
        while time.time() - start_time < FUNDING_TIMEOUT:
            try:
                new_balance = lium.balance()
                if new_balance > current_balance:
                    break
            except Exception:
                pass  # Ignore temporary API errors

            time.sleep(5)  # Check every 5 seconds
        else:
            console.warning(f"Balance not updated after {FUNDING_TIMEOUT}s timeout")
            console.dim("Check your balance later with 'lium config get user.balance'")
            return
    
    # Success
    funded_amount = new_balance - current_balance
    console.success(f"✓ Successfully funded {console.get_styled(f'{funded_amount:.4f} USD', 'success')}")
    console.success(f"✓ New balance: {console.get_styled(f'{new_balance} USD', 'success')}")