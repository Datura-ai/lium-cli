import asyncio
import importlib
import ssl
import sys
import traceback
from typing import Coroutine, Optional
from bittensor_cli.src.commands import wallets
from async_substrate_interface.errors import (
    SubstrateRequestException,
    ConnectionClosed,
    InvalidHandshake,
)
from bittensor_cli.src.bittensor.subtensor_interface import SubtensorInterface
from bittensor_cli.src.commands import wallets
import typer
from celium_cli.src.utils import err_console, verbose_console
from celium_cli.src.services.api import api_client, tao_pay_client


def asyncio_runner():
    if sys.version_info < (3, 10):
        # For Python 3.9 or lower
        return asyncio.get_event_loop().run_until_complete
    else:
        try:
            uvloop = importlib.import_module("uvloop")
            if sys.version_info >= (3, 11):
                return uvloop.run
            else:
                uvloop.install()
                return asyncio.run
        except ModuleNotFoundError:
            return asyncio.run

def run_command(cmd: Coroutine, exit_early: bool = True, subtensor: Optional[SubtensorInterface] = None):
    async def _run():
        initiated = False
        try:
            if subtensor:
                async with subtensor:
                    initiated = True
                    result = await cmd
            else:
                initiated = True
                result = await cmd
            return result
        except (ConnectionRefusedError, ssl.SSLError, InvalidHandshake):
            err_console.print(f"Unable to connect to the chain: {subtensor}")
            verbose_console.print(traceback.format_exc())
        except (
            ConnectionClosed,
            SubstrateRequestException,
            KeyboardInterrupt,
            RuntimeError,
        ) as e:
            if isinstance(e, SubstrateRequestException):
                err_console.print(str(e))
            elif isinstance(e, RuntimeError):
                pass  # Temporarily to handle loop bound issues
            verbose_console.print(traceback.format_exc())
        except Exception as e:
            err_console.print(f"An unknown error has occurred: {e}")
            verbose_console.print(traceback.format_exc())
        finally:
            if initiated is False:
                asyncio.create_task(cmd).cancel()
            if (
                exit_early is True
            ):  # temporarily to handle multiple run commands in one session
                try:
                    raise typer.Exit()
                except Exception as e:  # ensures we always exit cleanly
                    if not isinstance(e, (typer.Exit, RuntimeError)):
                        err_console.print(f"An unknown error has occurred: {e}")

    return asyncio_runner()(_run())



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
    run_command(wallets.transfer(
        wallet=wallet,
        subtensor=subtensor,
        destination=destination,
        amount=amount,
        transfer_all=False,
        era=3, 
        prompt=True,
        json_output=False,
    ), subtensor=subtensor)