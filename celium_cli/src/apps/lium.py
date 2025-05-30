import os
import typer
from rich.prompt import Prompt, Confirm
import time
from rich.live import Live
from rich.spinner import Spinner

from celium_cli.src.services import user as user_service
from celium_cli.src.apps import BaseApp
from celium_cli.src.styles import style_manager
from celium_cli.src.services import docker_credential as docker_credential_service
from celium_cli.src.services.api import api_client


class LiumApp(BaseApp):
    def run(self):
        self.app.command("init")(self.init)

    def init(self):
        """Initialize Celium and set up API key."""
        style_manager.console.print("[bold magenta]Welcome to Celium CLI Initialization![/bold magenta]")

        # Step 1: Check if API key is set
        api_key = self.cli_manager.config_app.config.get('api_key')
        if api_key:
            style_manager.console.print("[green]✓ API key is already set. Initialization not required.[/green]")
            style_manager.console.print(f"Current API key starts with: [cyan]{api_key[:4]}...[/cyan]")
        else:

            # Step 2: Ask if user has an account
            has_account = Confirm.ask("Do you already have a Celium account?", default=True, console=style_manager.console)

            jwt_token = None
            email_verified = False
            user_email = ""

            if not has_account:
                style_manager.console.print("\n[bold]Let's create a new Celium account for you.[/bold]")
                name = Prompt.ask("Enter your full name", console=style_manager.console)
                user_email = Prompt.ask("Enter your email address", console=style_manager.console)
                password = Prompt.ask("Create a password", password=True, console=style_manager.console)
                
                try:
                    style_manager.console.print(f"Creating account for {user_email}...")
                    # Assuming signup service handles prints or is silent on success
                    user_service.signup(name, user_email, password)
                    style_manager.console.print("[green]✓ Account created successfully![/green]")
                    style_manager.console.print("Now, let's log you in.")
                    jwt_token = user_service.login(user_email, password)
                    if not jwt_token:
                        style_manager.console.print("[bold red]Error: Automatic login after signup failed. Please try 'lium init' again and choose to log in.[/bold red]")
                        return
                    email_verified = user_service.get_email_verified(jwt_token)
                except Exception as e:
                    style_manager.console.print(f"[bold red]Account creation failed: {e}. Please try again.[/bold red]")
                    return
            else:
                style_manager.console.print("\n[bold]Please log in to your Celium account.[/bold]")
                user_email = Prompt.ask("Enter your email address", console=style_manager.console)
                password = Prompt.ask("Enter your password", password=True, console=style_manager.console)
                try:
                    style_manager.console.print(f"Logging in as {user_email}...")
                    jwt_token = user_service.login(user_email, password)
                    if not jwt_token:
                        style_manager.console.print("[bold red]Login failed. Please check your email and password and try again.[/bold red]")
                        return
                    style_manager.console.print("[green]✓ Logged in successfully![/green]")
                    email_verified = user_service.get_email_verified(jwt_token)
                except Exception as e:
                    style_manager.console.print(f"[bold red]Login error: {e}. Please try again.[/bold red]")
                    return

            if not jwt_token: # Should be caught earlier, but as a safeguard
                style_manager.console.print("[bold red]Could not obtain authentication token. Exiting.[/bold red]")
                return

            # Step 4, 5, 6: Verify email if not already verified
            if not email_verified:
                style_manager.console.print("\n[bold yellow]Your email address needs to be verified.[/bold yellow]")
                style_manager.console.print("Email verification is essential for account security and full access to Celium features.")
                
                fund_to_verify = Confirm.ask("Would you like to make a small payment to instantly verify your email and add initial funds to your account?", default=True, console=style_manager.console)
                if fund_to_verify:
                    style_manager.console.print("Proceeding to payment for verification...")
                    try:
                        # Assuming pay_app.pay() handles its own UI and exceptions
                        self.cli_manager.pay_app.pay(wallet_name=None, wallet_path=None, amount=None, jwt_token=jwt_token)
                        style_manager.console.print("Payment process initiated. Checking email verification status...")
                        email_verified = user_service.get_email_verified(jwt_token) # Check again after payment
                    except Exception as e:
                        raise e
                        style_manager.console.print(f"[bold red]Payment process error: {e}. Please try verifying your email manually.[/bold red]")
                else:
                    style_manager.console.print("No problem. Please check your inbox for an email from Celium with a verification link.")
                    style_manager.console.print("Once verified, run [cyan]lium init[/cyan] again.")
                    return # User chose to verify manually and exit for now

                # Polling loop if still not verified (e.g. after payment or if user chose non-payment path that didn't exit)
                if not email_verified: 
                    style_manager.console.print("We will now check for email verification periodically.")
                    style_manager.console.print("If you haven't received it, please check your spam folder for an email from Celium.")
                    max_retries = 30  # Poll for 5 minutes (30 * 10 seconds)
                    retries = 0
                    with Live(Spinner("dots", text="Waiting for email verification..."), console=style_manager.console, refresh_per_second=10) as live:
                        while not email_verified and retries < max_retries:
                            email_verified = user_service.get_email_verified(jwt_token)
                            if email_verified:
                                live.update("[green]✓ Email verified successfully![/green]")
                                break
                            retries += 1
                            live.update(Spinner("dots", text=f"Waiting for email verification... (attempt {retries}/{max_retries})"))
                            time.sleep(10)
                    
                    if not email_verified:
                        style_manager.console.print("[bold yellow]Email verification timed out.[/bold yellow]")
                        style_manager.console.print("Please ensure you have clicked the verification link in your email.")
                        style_manager.console.print("Run [cyan]lium init[/cyan] again once verified, or contact support if issues persist.")
                        return
            else:
                style_manager.console.print("[green]✓ Your email is already verified.[/green]")

            # Step 7: Get or create API key
            style_manager.console.print("\nCreating your API key...")
            try:
                new_api_key = user_service.get_or_create_api_key(jwt_token)
                if new_api_key:
                    self.cli_manager.config_app._update_config("api_key", new_api_key)
                    style_manager.console.print("[green]✓ API key created and saved successfully![/green]")

                    
                else:
                    style_manager.console.print("[bold red]Failed to create API key. The server did not return an API key. Please try again or contact support.[/bold red]")
            except Exception as e:
                raise e
                style_manager.console.print(f"[bold red]Error creating API key: {e}. Please try again or contact support.[/bold red]") 

        docker_credentials = docker_credential_service.list_credentials()
        if len(docker_credentials) == 0:
            # Docker Hub Credentials
            style_manager.console.print("\n[bold]Docker Hub Configuration[/bold]")
            has_docker_account = Confirm.ask("Do you have your own Docker Hub account?", default=False, console=style_manager.console)
            if has_docker_account:
                docker_username = Prompt.ask("Enter your Docker Hub username", console=style_manager.console)
                docker_password = Prompt.ask("Enter your Docker Hub password", password=True, console=style_manager.console)
                docker_credential_service.create_docker_credential(docker_username, docker_password)
            else:
                style_manager.console.print("The CLI will use a shared Docker Hub account for operations.")
                docker_credential_service.get_docker_credential()

        # Add SSH keys if doesn't exist 
        ssh_keys = api_client.get("ssh-keys/me")
        if len(ssh_keys) == 0:
            ssh_key_path = Prompt.ask("Enter the path to your SSH public key file", default="~/.ssh/id_rsa.pub", console=style_manager.console)
            try:
                ssh_key_path = os.path.expanduser(ssh_key_path)
                with open(ssh_key_path, "r") as f:
                    public_key_content = f.read().strip()
            except Exception as e:
                style_manager.console.print(f"[bold red]Error:[/bold red] Could not read SSH key file: {e}")
                return
            
            api_client.post("ssh-keys", json={
                "name": "celium-cli",
                "public_key": public_key_content
            })

        style_manager.console.print("[bold green]Celium CLI is now initialized and ready to use.[/bold green]")