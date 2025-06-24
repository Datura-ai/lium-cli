import typer
from celium_cli.src.apps import BaseApp, TemplateBaseArguments
from celium_cli.src.decorator import catch_validation_error
from celium_cli.src.services.executor import get_executors_and_print_table, rent_executor
from celium_cli.src.services.template import create_template
from celium_cli.src.services.validator import validate_for_api_key, validate_for_docker_build, validate_machine_name
from celium_cli.src.styles import style_manager
from celium_cli.src.utils import pretty_minutes
from celium_cli.src.services.api import api_client
from rich.table import Table, Column
from rich import box
from datetime import datetime, timezone, timedelta
import hashlib
import re
import requests
import json
from rich.prompt import Prompt
from collections import defaultdict

ADJECTIVES = ["swift", "silent", "brave", "bright", "calm", "clever", "eager", "fierce", "gentle", "grand"]
NOUNS = ["hawk", "lion", "tiger", "eagle", "fox", "wolf", "shark", "viper", "cobra", "falcon"]

def generate_pod_huid(pod_id: str) -> str:
    if not pod_id or not isinstance(pod_id, str):
        return "invalid-id"
    hasher = hashlib.md5(pod_id.encode('utf-8'))
    digest = hasher.hexdigest()
    adj_idx = int(digest[0:3], 16) % len(ADJECTIVES)
    noun_idx = int(digest[3:6], 16) % len(NOUNS)
    suffix_chars = digest[-2:]
    return f"{ADJECTIVES[adj_idx]}-{NOUNS[noun_idx]}-{suffix_chars}"

def extract_gpu_model_simple(machine_name: str) -> str:
    if not machine_name: return "Unknown"
    match = re.search(r'([A-Z]?\d{2,4}[A-Z]*(?:Ti|S|X)?(?![0-9]))', machine_name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    parts = machine_name.split()
    for part in reversed(parts):
        if re.match(r'^[A-Za-z0-9]+$', part) and any(char.isdigit() for char in part):
            return part.upper()
    return parts[-1] if parts else "Unknown"

def get_status_style(status: str) -> str:
    if not status: return "white"
    status_upper = status.upper()
    if status_upper in ["RUNNING", "ACTIVE", "READY", "COMPLETED", "VERIFY_SUCCESS"]:
        return "green"
    elif status_upper in ["FAILED", "ERROR", "STOPPED", "TERMINATED"]:
        return "red"
    elif status_upper in ["PENDING", "STARTING", "CREATING", "PROVISIONING", "INITIALIZING"]:
        return "yellow"
    return "white"

def extract_gpu_model_detailed(machine_name: str) -> str:
    """Extract just the model number from GPU name (more robust)."""
    if not machine_name: return "Unknown"
    patterns = [
        (r'RTX\s*A(\d{4}[A-Z]?)', 'RTXA'), # Must be before RTX\s*(\d{4}[A-Z]?) to catch RTX A series specifically
        (r'RTX\s*(\d{4}[A-Z]?)', 'RTX'),  # RTX 4090, RTX 3090, RTX 4090 D
        (r'H(\d{2,3})', 'H'),              # H100, H200 - BEFORE A pattern
        (r'B(\d{2,3})', 'B'),              # B200
        (r'L(\d{2}[S]?)', 'L'),            # L40, L40S
        (r'A(\d{2,3})', 'A'),              # A100, A40 - AFTER H pattern
        (r'MI(\d{2,3})X?', 'MI'),         # MI200, MI300X 
        (r'V(\d{2,3})', 'V')               # V100
    ]
    normalized_name = machine_name.upper()
    for pattern, prefix_group in patterns:
        match = re.search(pattern, normalized_name)
        if match:
            model_part = match.group(1)
            # For RTX A series, the prefix_group is RTXA to distinguish from consumer RTX
            if prefix_group == 'RTXA': return f"RTX A{model_part}"
            if prefix_group == 'RTX': return f"RTX {model_part}"
            # For others, prefix_group is the letter, model_part is the number
            return f"{prefix_group}{model_part}"
    # Fallback if no specific pattern matches, try to find a common GPU-like name
    common_models = ["A100", "H100", "L40S", "L40", "A40", "A6000", "4090", "3090"]
    for model in common_models:
        if model in normalized_name: return model
    # Last resort, simple extraction
    return extract_gpu_model_simple(machine_name) 

def group_executors_by_gpu_type(executors: list[dict]) -> dict:
    """Group executors by detailed GPU model type."""
    grouped = defaultdict(list)
    for executor in executors:
        machine_name = executor.get("machine_name", "Unknown")
        gpu_model = extract_gpu_model_detailed(machine_name)
        grouped[gpu_model].append(executor)
    return dict(grouped)

class Arguments(TemplateBaseArguments):
    machine: str = typer.Option(
        None,
        "--machine",
        "--machine-name",
        help="The name of the machine to run the pod on. If not provided, an interactive selection will be shown.",
    )
    ssh_key_path: str = typer.Option(
        None,
        "--ssh-key-path",
        "--ssh-key",
        help="The path to the SSH key to use for the pod",
    )
    template_id: str = typer.Option(
        None,
        "--template-id",
        help="The ID of the template to use for the pod."
    )
    pod_name: str = typer.Option(
        None,
        "--pod-name",
        help="A specific name for the pod. If not provided, a default name will be generated."
    )
    skip_confirmation: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompts (e.g., for default template selection)."
    )
    use_default_docker_image: bool = typer.Option(
        True,
        "--use-default-docker-image",
        help="Use the default docker image for the selected executor."
    )

class PodApp(BaseApp):
    def run(self):
        self.app.command("run")(self.run_pod)
        self.app.command("ps")(self.list_active_pods)
        self.app.command("ls")(self.list_available_pods)
        self.app.command("rm")(self.terminate_pod)

    @catch_validation_error
    def run_pod(
        self,
        machine: str = Arguments.machine,
        docker_image: str = Arguments.docker_image,
        dockerfile: str = Arguments.dockerfile,
        ssh_key_path: str = Arguments.ssh_key_path,
        template_id: str = Arguments.template_id,
        pod_name: str = Arguments.pod_name,
        skip_confirmation: bool = Arguments.skip_confirmation,
        use_default_docker_image: bool = Arguments.use_default_docker_image
    ):
        """
        Run a pod on a machine.

        This command allows you to run a pod on the celium platform.
        It offers multiple ways to specify the pod's software: by direct Docker image/file, 
        by existing template ID, or via interactive template selection.

        [bold]USAGE[/bold]: 
            [green]$[/green] celium pod run --machine 8XA100 --template-id <template_uuid>
            [green]$[/green] celium pod run --machine 8XA100 --docker-image user/image:tag
            [green]$[/green] celium pod run --machine 8XA100 --dockerfile ./Dockerfile 
        """
        validate_for_api_key(self.cli_manager)
        
        selected_executor_id = None
        machine_name_validated = None # Will be set if machine is provided or after selection

        if machine:
            count, machine_name_validated = validate_machine_name(machine)
            style_manager.console.print(f"[cyan]Fetching executors matching criteria: '{machine}'... For a detailed overview, try 'celium pod ls'.[/cyan]")
            executors = get_executors_and_print_table(count, machine_name_validated)
            if len(executors) == 0:
                style_manager.console.print("[bold yellow]Warning:[/bold yellow] No executors found for the specified machine criteria. Please try a different machine type or check availability.[/bold yellow]")
                # Optionally, proceed to interactive selection here too
                # For now, exiting if specific machine yields no results.
                return 
            selected_executor = executors[0] # Simplified: use the first executor found
            selected_executor_id = selected_executor['id']
            machine_name_validated = selected_executor.get('machine_name', machine_name_validated)
            style_manager.console.print(f"\n[bold blue]Selected machine from argument:[/bold blue] {machine_name_validated} (ID: [green]{selected_executor_id}[/green])")
        else:
            style_manager.console.print("[cyan]No machine specified, proceeding to interactive executor selection.[/cyan]")
            selected_executor_id, machine_name_validated = self._select_executor_interactively(skip_confirmation)
            if not selected_executor_id:
                style_manager.console.print("[bold red]No executor selected. Aborting pod run.[/bold red]")
                raise typer.Exit(code=1)
            style_manager.console.print(f"\n[bold blue]Selected machine via interactive selection:[/bold blue] {machine_name_validated} (ID: [green]{selected_executor_id}[/green])")

        template_id_to_use = template_id # Prioritize explicitly passed --template-id
        template_source_info = ""

        # 1. Determine Template ID
        if not template_id_to_use:
            # Check config for default template_id (adjust key as needed for celium config structure)
            # Assuming config is loaded into self.cli_manager.config_app.config
            # default_template_id_from_config = self.cli_manager.config_app.config.get("default_template_id")

            if use_default_docker_image:
                # Handle case where selected_executor might be None (from interactive selection)
                all_executors = api_client.get("executors")
                gpu_driver = ""
                executor = next((ex for ex in all_executors if ex.get("id") == selected_executor_id), None)
                if executor:
                    machine_name = executor.get("machine_name")
                    gpu_driver = executor.get("specs", {}).get("gpu", {}).get("driver", "")
                
                default_docker_image = self.cli_manager.template_app.get_default_docker_image(machine_name, gpu_driver)
                style_manager.console.print(f"[cyan]Using Default Docker Image:[/cyan] {default_docker_image}")
                
                templates = api_client.get("templates")
                default_template = next((t for t in templates if f"{t.get('docker_image')}:{t.get('docker_image_tag')}" == default_docker_image), None)
                default_template_id_from_config = default_template.get("id") if default_template else None
                style_manager.console.print(f"[cyan]Using Default Docker Image:[/cyan] {default_docker_image}")

            if default_template_id_from_config:
                template_source_info = f"Using default template from config: '{default_template_id_from_config}' - '{default_template.get('docker_image')}:{default_template.get('docker_image_tag')}'"
                if skip_confirmation:
                    template_id_to_use = default_template_id_from_config
                    style_manager.console.print(f"[cyan]{template_source_info}[/cyan]")
                else:
                    if typer.confirm(f"{template_source_info}. Use this template?", default=True):
                        template_id_to_use = default_template_id_from_config
                    else:
                        template_source_info = "User opted out of default template."
            
            if not template_id_to_use: # Still no template ID, try interactive selection or dockerfile
                if not dockerfile and not docker_image: # If no dockerfile or docker_image, prompt for preference
                    style_manager.console.print("[cyan]No template, Docker image, or Dockerfile specified.[/cyan]")
                    preference = Prompt.ask(
                        "How would you like to specify the software for the pod?",
                        choices=["template", "docker_image", "dockerfile"],
                        default="template",
                        console=style_manager.console
                    )
                    if preference == "template":
                        # Proceed with interactive template selection
                        pass # The existing logic below will handle this
                    elif preference == "docker_image":
                        docker_image = Prompt.ask("Enter the Docker image name (e.g., user/image:tag)", console=style_manager.console)
                        if not docker_image:
                            style_manager.console.print("[bold red]Error: Docker image name cannot be empty.[/bold red]")
                            raise typer.Exit(code=1)
                    elif preference == "dockerfile":
                        dockerfile_path_str = Prompt.ask("Enter the path to your Dockerfile", default="./Dockerfile", console=style_manager.console)
                        # Validate dockerfile_path_str if needed, e.g., check if file exists
                        dockerfile = dockerfile_path_str # Assign to the dockerfile variable
                        if not dockerfile: # Or add os.path.exists(dockerfile)
                             style_manager.console.print("[bold red]Error: Dockerfile path cannot be empty.[/bold red]")
                             raise typer.Exit(code=1)
                             
                if not dockerfile: # Only go interactive for templates if not building from Dockerfile locally
                    style_manager.console.print(f"[cyan]{template_source_info} Proceeding to interactive template selection.[/cyan]" if template_source_info else "[cyan]No template specified, proceeding to interactive selection.[/cyan]")
                    try:
                        with style_manager.console.status("Fetching available templates...", spinner="dots") as status:
                            available_templates = api_client.get("templates")
                        if not available_templates:
                            style_manager.console.print("[yellow]No templates available to choose from.[/yellow]")
                            # Fallback: if docker_image is provided, old logic in rent_executor might find one.
                            # If not, this will likely fail in rent_executor if it strictly needs a template_id.
                            if not docker_image and not dockerfile:
                                style_manager.console.print("[bold red]Error: No template selected and no Docker image/file provided.[/bold red]")
                                raise typer.Exit(code=1)
                        else:
                            template_id_to_use = self._select_template_interactively(available_templates, skip_confirmation)
                            if not template_id_to_use and not docker_image and not dockerfile:
                                style_manager.console.print("[bold red]Error: No template selected and no Docker image/file provided.[/bold red]")
                                raise typer.Exit(code=1)
                    except Exception as e:
                        style_manager.console.print(f"[red]Error fetching or selecting templates: {e}[/red]")
                        # Decide if to exit or try to proceed if docker_image is available
                        if not docker_image and not dockerfile:
                           raise typer.Exit(code=1)
        else:
            style_manager.console.print(f"[cyan]Using provided template ID: '{template_id_to_use}'[/cyan]")

        # 2. Handle Dockerfile if provided and no template_id was resolved from options/config/interactive
        # If a template_id_to_use IS resolved, we use that, and dockerfile argument is ignored for template creation.
        # The docker_image argument might still be used by rent_executor if template_id_to_use is None (template by name).
        final_template_id_for_rent = template_id_to_use
        if dockerfile and not final_template_id_for_rent:
            style_manager.console.print("[cyan]Dockerfile provided, creating or updating template...[/cyan]")
            try:
                # create_template will build and push, then create/update template on backend
                # It needs docker_image as a suggestion for the new template's image name if not specified already
                # or if the user wants to name the image built from Dockerfile.
                final_template_id_for_rent = create_template(docker_image, dockerfile) # docker_image here can be None
                style_manager.console.print(f"[green]Using template from Dockerfile: '{final_template_id_for_rent}'[/green]")
            except Exception as e:
                style_manager.console.print(f"[bold red]Error creating template from Dockerfile: {e}[/bold red]")
                raise typer.Exit(code=1)
        
        # At this point, final_template_id_for_rent should be set if a template is to be used by ID.
        # If it's None, rent_executor might try to find a template by docker_image name (older celium-cli behavior).

        # 3. Determine Pod Name
        actual_pod_name = pod_name
        if not actual_pod_name:
            pass 

        # 4. Rent Executor (machine selection part is now above)
        if not selected_executor_id: # Should have been caught earlier
            style_manager.console.print("[bold red]Critical Error: No executor ID determined before renting. Aborting.[/bold red]")
            raise typer.Exit(code=1)

        style_manager.console.print(f"\n[bold blue]Preparing to deploy on machine:[/bold blue] {machine_name_validated} (ID: [green]{selected_executor_id}[/green])")
        if final_template_id_for_rent:
             style_manager.console.print(f"[cyan]Using Template ID:[/cyan] {final_template_id_for_rent}")
        elif docker_image:
             style_manager.console.print(f"[cyan]Using Docker Image:[/cyan] {docker_image} (template will be matched by image name if possible)")
        # If only dockerfile was provided and template created, final_template_id_for_rent will be set.
        # If neither template, image, nor dockerfile, it's an error.
        elif not final_template_id_for_rent and not docker_image and not dockerfile:
            # This case should ideally be caught by the prompt logic or earlier checks.
            style_manager.console.print("[bold red]Error: No template ID, Docker image, or Dockerfile specified to run.[/bold red]")
            raise typer.Exit(code=1)
        
        # Call rent_executor - this function will need to be updated to accept pod_name
        # and use final_template_id_for_rent instead of doing its own template lookup if ID is provided.
        rent_executor(selected_executor_id, docker_image, final_template_id_for_rent, ssh_key_path, actual_pod_name)

    def _select_template_interactively(self, templates: list, skip_prompts: bool) -> str | None:
        """Helper to interactively select a template from a list."""
        if not templates:
            return None

        current_templates = templates

        if not skip_prompts and templates:
            if typer.confirm("Filter templates by Docker image keyword?", default=False):
                keyword = Prompt.ask("Enter keyword for Docker image (e.g., 'pytorch', 'cuda12.1')", console=style_manager.console).strip().lower()
                if keyword:
                    filtered_templates = [
                        tpl for tpl in templates
                        if keyword in tpl.get("docker_image", "").lower() or \
                           keyword in tpl.get("docker_image_tag", "").lower()
                    ]
                    if not filtered_templates:
                        style_manager.console.print(f"[yellow]No templates found matching Docker image keyword: '{keyword}'. Showing all available templates.[/yellow]")
                        # Keep current_templates as all templates
                    else:
                        current_templates = filtered_templates
                        style_manager.console.print(f"[cyan]Showing templates filtered by Docker image keyword: '{keyword}'[/cyan]")
                else:
                    style_manager.console.print("[yellow]No keyword entered. Showing all available templates.[/yellow]")

        if not current_templates: # Can happen if initial templates list was empty or filter cleared it and we decided not to show all
            style_manager.console.print("[yellow]No templates available to choose from (after filtering).[/yellow]")
            return None

        style_manager.console.print("\n[bold magenta]Available Templates:[/bold magenta]")
        table = Table(box=box.SIMPLE, show_lines=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="yellow", min_width=20)
        table.add_column("Docker Image", style="green", min_width=30)
        table.add_column("ID (partial)", style="dim", width=15)

        template_map = {}
        for idx, tpl in enumerate(current_templates, 1): # Use current_templates here
            tpl_id = tpl.get("id", "N/A")
            tpl_name = tpl.get("name", "Unnamed Template")
            tpl_image = f"{tpl.get('docker_image', 'N/A')}:{tpl.get('docker_image_tag', 'latest')}"
            table.add_row(str(idx), tpl_name, tpl_image, tpl_id[:13] + "..." if len(tpl_id) > 13 else tpl_id)
            template_map[str(idx)] = tpl_id
        
        style_manager.console.print(table)

        if skip_prompts:
            # If --yes, and we are in interactive mode (meaning no explicit ID and no default config was accepted),
            # we could pick the first template, or require explicit choice. Lium prompts for first one.
            # For celium, let's require a choice if we reach full interactive mode.
            # However, this part of the function might not be hit if skip_prompts is true and a default_template_id was set & auto-accepted.
            # If truly interactive and --yes, it's ambiguous. Let's assume --yes means don't show this interactive list.
            # This function should ideally not be called with skip_prompts=True if other options were available.
            # For safety, if skip_prompts is true here, we return the first template.
            style_manager.console.print("[yellow]--yes specified during interactive selection, choosing the first template.[/yellow]")
            return current_templates[0].get("id") if current_templates else None # Use current_templates


        while True:
            choice = Prompt.ask("Enter the [bold cyan]#[/bold cyan] or full [bold cyan]ID[/bold cyan] of the template to use (or type 'cancel')", console=style_manager.console).strip()
            if choice.lower() == 'cancel':
                return None
            if choice in template_map: # User entered number
                return template_map[choice]
            # User might have entered full ID
            for tpl_id_check in template_map.values():
                if tpl_id_check == choice:
                    return choice 
            style_manager.console.print("[red]Invalid selection. Please try again or type 'cancel'.[/red]")

    def _select_executor_interactively(self, skip_prompts: bool) -> tuple[str | None, str | None]:
        """Helper to interactively select an executor from a list."""
        try:
            with style_manager.console.status("Fetching available executors...", spinner="dots") as status:
                all_executors = api_client.get("executors")
        except Exception as e:
            style_manager.console.print(f"[red]Error fetching executors: {e}[/red]")
            return None, None

        if not all_executors:
            style_manager.console.print("[yellow]No executors available to choose from.[/yellow]")
            return None, None

        if not skip_prompts:
            # Display summary of GPU types first
            grouped_by_gpu = group_executors_by_gpu_type(all_executors)
            if grouped_by_gpu:
                style_manager.console.print("\n[bold magenta]Available GPU Types Summary:[/bold magenta]")
                summary_table = Table(box=box.ROUNDED, show_lines=False, header_style="bold cyan")
                summary_table.add_column("GPU Type", style="yellow", min_width=15)
                summary_table.add_column("Min $/GPU/hr", style="green", justify="right")
                summary_table.add_column("Max $/GPU/hr", style="green", justify="right")
                summary_table.add_column("Available Hosts", style="blue", justify="right")
                summary_table.add_column("Total GPUs", style="magenta", justify="right")

                # Sort GPU types: by total GPUs descending, then by name ascending for tie-breaking
                sorted_gpu_types = sorted(
                    grouped_by_gpu.keys(),
                    key=lambda x: (
                        sum(e.get("specs", {}).get("gpu", {}).get("count", 0) for e in grouped_by_gpu[x]),
                        x
                    ),
                    reverse=True
                )

                for gpu_type in sorted_gpu_types:
                    type_executors = grouped_by_gpu[gpu_type]
                    if not type_executors: continue

                    prices_per_gpu = []
                    total_gpus_in_type = 0
                    for exec_data in type_executors:
                        gpu_count = exec_data.get("specs", {}).get("gpu", {}).get("count", 1)
                        if gpu_count == 0: gpu_count = 1 # Avoid division by zero for price calc
                        price_ph = exec_data.get("price_per_hour")
                        if isinstance(price_ph, (int, float)):
                            prices_per_gpu.append(price_ph / gpu_count)
                        total_gpus_in_type += exec_data.get("specs", {}).get("gpu", {}).get("count", 0) # Use actual count for sum
                    
                    min_price_str = f"${min(prices_per_gpu):.2f}" if prices_per_gpu else "N/A"
                    max_price_str = f"${max(prices_per_gpu):.2f}" if prices_per_gpu else "N/A"
                    
                    summary_table.add_row(
                        gpu_type,
                        min_price_str,
                        max_price_str,
                        str(len(type_executors)),
                        str(total_gpus_in_type)
                    )
                style_manager.console.print(summary_table)
                style_manager.console.print("") # Add a newline for better spacing
            else:
                style_manager.console.print("[yellow]No GPU types found from available executors.[/yellow]")


        filtered_executors = all_executors
        
        # GPU ID Filter
        if not skip_prompts and typer.confirm("Filter by GPU type/ID?", default=False):
            gpu_filter_prompt = Prompt.ask("Enter GPU type/ID to filter by (e.g., H100, RTX4090, A100)", console=style_manager.console).strip().upper()
            if gpu_filter_prompt:
                filtered_executors = [
                    ex for ex in filtered_executors 
                    if gpu_filter_prompt in ex.get("machine_name", "").upper() or \
                       gpu_filter_prompt in ex.get("gpu_type", "").upper() or \
                       gpu_filter_prompt in extract_gpu_model_detailed(ex.get("machine_name", "")).upper()
                ]
                if not filtered_executors:
                    style_manager.console.print(f"[yellow]No executors found matching GPU filter: {gpu_filter_prompt}[/yellow]")
                    return None, None

        # Sorting Options
        sort_key = "default" # Default sort from API or by first seen
        if not skip_prompts and len(filtered_executors) > 1:
            sort_choice = Prompt.ask(
                "Sort executors by?",
                choices=["default", "uptime", "download_speed", "upload_speed", "location", "price"],
                default="default",
                console=style_manager.console
            )
            if sort_choice == "uptime":
                # API response needs 'uptime_in_minutes' or similar. Assuming it exists or needs to be calculated.
                # For now, let's assume a placeholder 'uptime_in_minutes' key for sorting.
                # If not available, this sort won't be effective or might error.
                # Need to ensure 'uptime_in_minutes' is a comparable type (e.g., int).
                # Add error handling for missing keys if necessary.
                filtered_executors.sort(key=lambda ex: ex.get("uptime_in_minutes", 0), reverse=True)
                sort_key = "uptime"
            elif sort_choice == "download_speed":
                # Assuming 'network_stats.download_mbps' or similar key.
                filtered_executors.sort(key=lambda ex: ex.get("specs", {}).get("network", {}).get("download_speed", 0) or 0, reverse=True)
                sort_key = "download_speed"
            elif sort_choice == "upload_speed":
                 # Assuming 'network_stats.upload_mbps' or similar key.
                filtered_executors.sort(key=lambda ex: ex.get("specs", {}).get("network", {}).get("upload_speed", 0) or 0, reverse=True)
                sort_key = "upload_speed"
            elif sort_choice == "location":
                # Assuming 'location.city' or 'location.country'
                filtered_executors.sort(key=lambda ex: (ex.get("location", {}).get("country", ""), ex.get("location", {}).get("city", "")))
                sort_key = "location"
            elif sort_choice == "price":
                # Assuming 'price_per_hour'
                 filtered_executors.sort(key=lambda ex: ex.get("price_per_hour", float('inf')))
                 sort_key = "price"


        top_n_executors = filtered_executors[:10]
        if not top_n_executors:
            style_manager.console.print("[yellow]No executors available after filtering/sorting.[/yellow]")
            return None, None

        style_manager.console.print(f"\n[bold magenta]Top {len(top_n_executors)} Available Executors (Sorted by {sort_key}):[/bold magenta]")
        table = Table(box=box.SIMPLE, show_lines=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Machine Name", style="yellow", min_width=20)
        table.add_column("GPU(s)", style="cyan", min_width=15)
        table.add_column("RAM (GB)", style="magenta", justify="right", width=8)
        table.add_column("Price ($/hr)", style="green", justify="right", width=10)
        table.add_column("Location", style="blue", min_width=10)
        table.add_column("Uptime (min)", style="white", justify="right", width=10) # Example, assuming uptime_in_minutes
        table.add_column("Net Down/Up (Mbps)", style="dim", justify="right", width=18) # Example for network
        table.add_column("DinD Support", justify="center", width=12) # Removed style, will apply per cell

        executor_map = {}
        for idx, ex in enumerate(top_n_executors, 1):
            ex_id = ex.get("id", "N/A")
            machine_name = ex.get("machine_name", "Unknown Executor")
            
            gpu_model = extract_gpu_model_detailed(machine_name)
            gpu_count = ex.get("specs", {}).get("gpu", {}).get("count", 1)
            gpu_display = f"{gpu_count}x {gpu_model}" if gpu_model != "Unknown" else "N/A"

            ram_gb = "N/A"
            ram_total_kb = ex.get("specs", {}).get("ram", {}).get("total_kb") # Assuming 'total_kb'
            if isinstance(ram_total_kb, (int, float)) and ram_total_kb > 0:
                ram_gb = f"{ram_total_kb / 1024 / 1024:.0f}"

            price_hr = ex.get("price_per_hour")
            price_display = f"${price_hr:.2f}" if isinstance(price_hr, (float, int)) else "N/A"
            
            location_info = ex.get("location", {})
            loc_display = f"{location_info.get('city', '')}, {location_info.get('country', '')}".strip(", ") or "N/A"

            uptime_min = ex.get("uptime_in_minutes", "N/A") # Placeholder
            
            net_stats = ex.get("specs", {}).get("network", {})
            download_speed_val = net_stats.get("download_speed", "N/A")
            upload_speed_val = net_stats.get("upload_speed", "N/A")
            download_speed_display = f"{download_speed_val:.1f} Mbps" if isinstance(download_speed_val, (int, float)) else "N/A"
            upload_speed_display = f"{upload_speed_val:.1f} Mbps" if isinstance(upload_speed_val, (int, float)) else "N/A"
            net_display = f"{download_speed_display}/{upload_speed_display}"

            dind_support = ex.get("specs", {}).get("sysbox_runtime", False)
            dind_display = "[green]✅[/green]" if dind_support else "[red]❌[/red]"

            table.add_row(
                str(idx), 
                machine_name, 
                gpu_display,
                ram_gb,
                price_display,
                loc_display,
                str(uptime_min),
                net_display,
                dind_display
            )
            executor_map[str(idx)] = (ex_id, machine_name)
        
        style_manager.console.print(table)

        if skip_prompts:
            style_manager.console.print("[yellow]--yes specified, choosing the first available executor.[/yellow]")
            first_ex_id, first_ex_name = executor_map.get("1")
            return first_ex_id, first_ex_name


        while True:
            choice = Prompt.ask("Enter the [bold cyan]#[/bold cyan] of the executor to use (or type 'cancel')", console=style_manager.console).strip()
            if choice.lower() == 'cancel':
                return None, None
            if choice in executor_map:
                selected_id, selected_name = executor_map[choice]
                return selected_id, selected_name
            style_manager.console.print("[red]Invalid selection. Please try again or type 'cancel'.[/red]")

    def _select_pod_to_terminate_interactively(self) -> dict | None:
        """Helper to interactively select an active pod for termination."""
        style_manager.console.print("[cyan]Fetching active pods for selection...[/cyan]")
        try:
            with style_manager.console.status("Fetching active pods...", spinner="dots"):
                active_pods = api_client.get("pods")
        except Exception as e:
            style_manager.console.print(f"[red]Error fetching active pods: {e}[/red]")
            return None

        if not active_pods:
            style_manager.console.print("[yellow]No active pods found to select from.[/yellow]")
            return None

        style_manager.console.print("\n[bold magenta]Select a pod to terminate:[/bold magenta]")
        table = Table(box=box.SIMPLE, show_lines=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("HUID", style="dim", min_width=16)
        table.add_column("Pod Name", style="yellow", min_width=20)
        table.add_column("Status", style="primary", width=11)
        table.add_column("GPU Config", style="cyan", width=12, no_wrap=True)
        
        pod_selection_map = {} 

        for idx, pod_data in enumerate(active_pods, 1):
            pod_id = pod_data.get("id")
            if not pod_id:
                continue 

            huid = generate_pod_huid(pod_id)
            pod_name_display = pod_data.get("pod_name", huid) # Display pod_name, fallback to HUID
            status = pod_data.get("status", "N/A")
            status_style = get_status_style(status)
            status_display = f"[{status_style}]{status}[/{status_style}]"

            gpu_name = pod_data.get("machine_name")
            if not gpu_name and pod_data.get("executor_details"):
                gpu_name = pod_data["executor_details"].get("machine_name", pod_data["executor_details"].get("gpu_type"))
            if not gpu_name: gpu_name = "N/A"

            gpu_count = pod_data.get("gpu_count", 1)
            if isinstance(gpu_count, str) and gpu_count.isdigit(): gpu_count = int(gpu_count)
            elif not isinstance(gpu_count, int) or gpu_count <= 0: gpu_count = 1
            
            gpu_model = extract_gpu_model_simple(gpu_name)
            gpu_config_display = f"{gpu_count}x {gpu_model}" if gpu_name != "N/A" else "N/A"
            
            table.add_row(
                str(idx),
                huid,
                pod_name_display,
                status_display,
                gpu_config_display
            )
            # Store information needed for termination
            pod_selection_map[str(idx)] = {"id": pod_id, "huid": huid, "original_ref": pod_name_display} 
        
        style_manager.console.print(table)

        while True:
            choice = Prompt.ask("Enter the [bold cyan]#[/bold cyan] of the pod to terminate (or type 'cancel')", console=style_manager.console).strip()
            if choice.lower() == 'cancel':
                style_manager.console.print("[yellow]Termination cancelled by user.[/yellow]")
                return None
            if choice in pod_selection_map:
                return pod_selection_map[choice]
            style_manager.console.print("[red]Invalid selection. Please try again or type 'cancel'.[/red]")

    def list_active_pods(self):
        """
        Lists all active pods for the current user.
        """
        validate_for_api_key(self.cli_manager)
        try:
            with style_manager.console.status("Fetching active pods...", spinner="dots") as status:
                active_pods = api_client.get("pods")

            if not active_pods:
                style_manager.console.print("[yellow]No active pods found.[/yellow]")
                return

            table = Table(
                Column("HUID", style="dim", no_wrap=False, min_width=16, max_width=20),
                Column("Status", style="primary", width=11),
                Column("GPU Config", style="cyan", width=12, no_wrap=True),
                Column("RAM (GB)", style="magenta", justify="right", width=8),
                Column("$/hr", style="green", justify="right", width=7),
                Column("Spent", style="green", justify="right", width=8),
                Column("Uptime", style="blue", justify="right", width=10),
                box=box.ROUNDED,
                title=f"Active Pods ({len(active_pods)} total)",
                title_style="bold magenta",
                header_style="bold white on blue"
            )

            for idx, pod_data in enumerate(active_pods):
                huid = generate_pod_huid(pod_data.get("id", str(idx)))
                status = pod_data.get("status", "N/A")
                status_style = get_status_style(status)
                status_display = f"[{status_style}]{status}[/{status_style}]"
                
                gpu_name = pod_data.get("machine_name")
                if not gpu_name and pod_data.get("executor_details"):
                    gpu_name = pod_data["executor_details"].get("machine_name", pod_data["executor_details"].get("gpu_type"))
                if not gpu_name: gpu_name = "N/A"

                gpu_count = pod_data.get("gpu_count", 1)
                if isinstance(gpu_count, str) and gpu_count.isdigit(): gpu_count = int(gpu_count)
                elif not isinstance(gpu_count, int) or gpu_count <= 0: gpu_count = 1
                
                gpu_model = extract_gpu_model_simple(gpu_name)
                gpu_config_display = f"{gpu_count}x {gpu_model}" if gpu_name != "N/A" else "N/A"

                ram_total_gb = "N/A"
                specs = pod_data.get("specs", pod_data.get("executor_details", {}).get("specs"))
                if specs and specs.get("ram") and specs["ram"].get("total"):
                     ram_total_kb = specs["ram"]["total"]
                     if isinstance(ram_total_kb, (int, float)) and ram_total_kb > 0:
                         ram_total_gb = f"{ram_total_kb / 1024 / 1024:.0f}"
                
                price_per_hour = pod_data.get("price_per_hour")
                price_display = f"${price_per_hour:.2f}" if isinstance(price_per_hour, (int, float)) else "N/A"
                
                cost_so_far_display = "N/A"
                uptime_display = "N/A"
                created_at_str = pod_data.get("created_at")
                if created_at_str:
                    try:
                        if created_at_str.endswith('Z'): 
                            dt_created = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        elif '.' in created_at_str and ('+' not in created_at_str and '-' not in created_at_str[10:]):
                            dt_parsed = datetime.fromisoformat(created_at_str)
                            dt_created = dt_parsed.replace(tzinfo=timezone.utc) if dt_parsed.tzinfo is None else dt_parsed
                        else: 
                            dt_created = datetime.fromisoformat(created_at_str)
                        
                        if dt_created.tzinfo is None:
                            dt_created = dt_created.replace(tzinfo=timezone.utc)

                        now_utc = datetime.now(timezone.utc)
                        if now_utc < dt_created:
                             duration = timedelta(seconds=0)
                        else:
                             duration = now_utc - dt_created
                        
                        duration_hours = duration.total_seconds() / 3600
                        total_seconds = duration.total_seconds()

                        if total_seconds < 0: total_seconds = 0

                        days, remainder = divmod(total_seconds, 86400)
                        hours, remainder = divmod(remainder, 3600)
                        minutes, seconds = divmod(remainder, 60)

                        if days > 0:
                            uptime_display = f"{int(days)}d{int(hours)}h"
                        elif hours > 0:
                            uptime_display = f"{int(hours)}h{int(minutes)}m"
                        elif minutes > 0:
                            uptime_display = f"{int(minutes)}m{int(seconds)}s"
                        else:
                            uptime_display = f"{int(seconds)}s"
                        
                        if isinstance(price_per_hour, (int, float)) and duration_hours > 0:
                            cost_so_far_display = f"${(duration_hours * price_per_hour):.2f}"
                        elif isinstance(price_per_hour, (int, float)):
                            cost_so_far_display = "$0.00"

                    except ValueError:
                        uptime_display = "DateErr"
                        cost_so_far_display = "CalcErr"
                    except Exception:
                        uptime_display = "TimeErr"
                        cost_so_far_display = "CostErr"
                
                table.add_row(
                    huid,
                    status_display,
                    gpu_config_display,
                    ram_total_gb,
                    price_display,
                    cost_so_far_display,
                    uptime_display,
                    style="on #111111" if idx % 2 == 1 else "on #222222"
                )
            
            style_manager.console.print(table)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                 style_manager.console.print("[bold red]Error: Authentication failed. Invalid API Key.[/bold red]")
            elif e.response.status_code == 404:
                 style_manager.console.print("[bold red]Error: Could not find pods. The API endpoint '/api/pods' might be incorrect or you have no active pods.[/bold red]")
            else:
                 style_manager.console.print(f"[bold red]API Error ({e.response.status_code}): {e.response.text}[/bold red]")
        except requests.exceptions.RequestException as e:
            style_manager.console.print(f"[bold red]Request Error: Failed to connect to the server. {e}[/bold red]")
        except Exception as e:
            style_manager.console.print(f"[bold red]Error listing active pods: {type(e).__name__} - {e}[/bold red]")

    def terminate_pod(self, 
                      pod_identifier: str = typer.Argument(None, help="HUID or ID of the pod to terminate. If not provided and --all is not used, an interactive selection will be shown."), 
                      all_pods: bool = typer.Option(False, "--all", "-a", help="Terminate all active pods for the user."),
                      skip_confirmation: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts.")):
        """
        Terminates one or more pods.
        
        Provide a Pod HUID (e.g., swift-hawk-a2) or the full Pod ID.
        Use --all to terminate all your active pods.
        """
        validate_for_api_key(self.cli_manager)

        pods_to_terminate_info = [] # List of dicts like {"huid": huid, "id": pod_id, "original_ref": identifier}
        try:
            if not pod_identifier and not all_pods:
                # Interactive selection mode
                selected_pod_info = self._select_pod_to_terminate_interactively()
                if not selected_pod_info:
                    return # User cancelled or no pod selected
                pods_to_terminate_info.append(selected_pod_info)
            elif all_pods:
                if pod_identifier: # Cannot use --all with a specific identifier
                    style_manager.console.print("[bold red]Error: Cannot use a specific pod identifier with the --all flag.[/bold red]")
                    raise typer.Exit(code=1)
                # Fetch all active pods for termination
                with style_manager.console.status("Fetching all active pods to terminate...", spinner="dots"):
                    active_pods = api_client.get("pods")
                if not active_pods:
                    style_manager.console.print("[yellow]No active pods found to terminate.[/yellow]")
                    return
                for pod in active_pods:
                    pod_id = pod.get("id")
                    if pod_id:
                        huid = generate_pod_huid(pod_id)
                        pod_name_display = pod.get("pod_name", huid)
                        pods_to_terminate_info.append({
                            "huid": huid,
                            "id": pod_id,
                            "original_ref": pod_name_display 
                        })
            elif pod_identifier: # Specific pod identifier provided
                with style_manager.console.status(f"Fetching pod '{pod_identifier}' to terminate...", spinner="dots"):
                    active_pods = api_client.get("pods") # Fetches all to find the one
                if not active_pods:
                    style_manager.console.print(f"[yellow]No active pods found. Cannot find '{pod_identifier}'.[/yellow]")
                    return
                
                found_pod = None
                for pod in active_pods:
                    pod_id = pod.get("id")
                    if not pod_id: continue
                    huid = generate_pod_huid(pod_id)
                    pod_name = pod.get("pod_name")

                    # Match by HUID, full ID, or pod_name
                    if pod_identifier.lower() == huid.lower() or \
                       pod_identifier == pod_id or \
                       (pod_name and pod_identifier == pod_name) :
                        found_pod = pod
                        break
                
                if found_pod:
                    pod_id = found_pod.get("id")
                    huid = generate_pod_huid(pod_id)
                    pod_name_display = found_pod.get("pod_name", huid)
                    pods_to_terminate_info.append({
                        "huid": huid,
                        "id": pod_id,
                        "original_ref": pod_name_display # Use HUID or name used for search
                    })
                else:
                    style_manager.console.print(f"[bold red]Error: Pod with identifier '{pod_identifier}' not found among active pods.[/bold red]")
                    return
            else: # Should not be reached if logic is correct, but as a fallback:
                style_manager.console.print("[bold red]Error: You must specify a pod identifier, use --all, or run interactively (no arguments).[/bold red]")
                raise typer.Exit(code=1)


            if not pods_to_terminate_info:
                style_manager.console.print("[yellow]No pods selected for termination.[/yellow]")
                return

            style_manager.console.print("\n[bold magenta]Pods to be terminated:[/bold magenta]")
            for p_info in pods_to_terminate_info:
                style_manager.console.print(f"  - {p_info['original_ref']} (ID: {p_info['id']})")
            style_manager.console.print("")

            if not skip_confirmation:
                confirm_message = f"Are you sure you want to terminate {len(pods_to_terminate_info)} pod(s)?"
                if not typer.confirm(confirm_message, abort=True):
                    # This aborts if user says no, so no explicit return needed.
                    pass 
            
            success_count = 0
            failure_count = 0
            failed_details = []

            with style_manager.console.status("Terminating selected pod(s)...", spinner="dots") as status:
                for p_info in pods_to_terminate_info:
                    try:
                        # Assuming the API endpoint is DELETE /api/pods/{pod_id}
                        api_client.delete(f"pods/{p_info['id']}")
                        style_manager.console.print(f"[green]Successfully requested termination for pod: {p_info['original_ref']}[/green]")
                        success_count += 1
                    except requests.exceptions.HTTPError as e:
                        failure_count += 1
                        error_msg = f"API Error {e.response.status_code}"
                        try: 
                            error_details = e.response.json()
                            detail_msg = error_details.get('detail', e.response.text)
                            error_msg += f" - {detail_msg if isinstance(detail_msg, str) else json.dumps(detail_msg)}"
                        except ValueError: # json.JSONDecodeError is a subclass of ValueError
                            error_msg += f" - {e.response.text[:100]}" # Truncate if not json
                        failed_details.append(f"'{p_info['original_ref']}': {error_msg}")
                        style_manager.console.print(f"[red]Failed to terminate pod {p_info['original_ref']}: {error_msg}[/red]")
                    except Exception as e:
                        failure_count += 1
                        failed_details.append(f"'{p_info['original_ref']}': Unexpected error: {str(e)}")
                        style_manager.console.print(f"[red]Unexpected error terminating pod {p_info['original_ref']}: {str(e)}[/red]")
            
            style_manager.console.print("\n[bold underline]Termination Summary:[/bold underline]")
            if success_count > 0:
                style_manager.console.print(f"[green]Successfully terminated {success_count} pod(s).[/green]")
            if failure_count > 0:
                style_manager.console.print(f"[red]Failed to terminate {failure_count} pod(s):[/red]")
                for detail in failed_details:
                    style_manager.console.print(f"  - {detail}")
            
            if success_count > 0 or failure_count > 0:
                style_manager.console.print("\nUse [blue]celium pod ps[/blue] to verify status.")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                 style_manager.console.print("[bold red]Error: Authentication failed. Invalid API Key.[/bold red]")
            else:
                 style_manager.console.print(f"[bold red]API Error ({e.response.status_code}) during pod data retrieval: {e.response.text}[/bold red]")
        except requests.exceptions.RequestException as e:
            style_manager.console.print(f"[bold red]Request Error: Failed to connect to the server. {e}[/bold red]")
        except typer.Abort:
            style_manager.console.print("[yellow]Operation cancelled by user.[/yellow]")
        except Exception as e:
            style_manager.console.print(f"[bold red]An unexpected error occurred: {type(e).__name__} - {e}[/bold red]")

    def list_available_pods(self, gpu_type_filter: str = typer.Option(None, "--gpu-type", "-g", help="Filter directly by a GPU type (e.g., 'H100', '4090').")):
        """
        Lists all available executors (pods that can be rented), grouped by GPU type.
        Provides a summary and allows viewing details for a selected GPU type.
        """
        validate_for_api_key(self.cli_manager) # API key might be needed depending on API config
        try:
            with style_manager.console.status("Fetching available executors...", spinner="dots") as status:
                # Assuming "executors" endpoint lists all rentable instances
                # Lium uses require_auth=False here, celium might differ.
                # For now, let api_client use its default auth behavior.
                executors = api_client.get("executors") 

            if not executors:
                style_manager.console.print("[yellow]No executors currently available.[/yellow]")
                return

            grouped_by_gpu = group_executors_by_gpu_type(executors)
            
            selected_gpu_type_to_detail = None
            if gpu_type_filter:
                # Normalize and check filter
                normalized_filter = gpu_type_filter.upper()
                # Find a matching key in our grouped_by_gpu (keys are already normalized by extract_gpu_model_detailed)
                matched_key = next((key for key in grouped_by_gpu.keys() if normalized_filter in key.upper()), None)
                if matched_key:
                    selected_gpu_type_to_detail = matched_key
                else:
                    style_manager.console.print(f"[yellow]GPU type '{gpu_type_filter}' not found. Available types: {', '.join(sorted(grouped_by_gpu.keys()))}[/yellow]")
                    return # Exit if filter yields no results
            else:
                # Show summary and prompt for selection
                style_manager.console.print("\n[bold magenta]Available GPU Types Summary:[/bold magenta]")
                summary_table = Table(box=box.ROUNDED, show_lines=False, header_style="bold cyan")
                summary_table.add_column("GPU Type", style="yellow", min_width=15)
                summary_table.add_column("Min $/GPU/hr", style="green", justify="right")
                summary_table.add_column("Max $/GPU/hr", style="green", justify="right")
                summary_table.add_column("Available Hosts", style="blue", justify="right")
                summary_table.add_column("Total GPUs", style="magenta", justify="right")

                sorted_gpu_types = sorted(grouped_by_gpu.keys(), key=lambda x: (sum(e.get("specs",{}).get("gpu",{}).get("count",0) for e in grouped_by_gpu[x]), x), reverse=True)

                for gpu_type in sorted_gpu_types:
                    type_executors = grouped_by_gpu[gpu_type]
                    if not type_executors: continue

                    prices_per_gpu = []
                    total_gpus_in_type = 0
                    for exec_data in type_executors:
                        gpu_count = exec_data.get("specs", {}).get("gpu", {}).get("count", 1)
                        if gpu_count == 0: gpu_count = 1 # Avoid division by zero
                        price_ph = exec_data.get("price_per_hour")
                        if isinstance(price_ph, (int, float)):
                            prices_per_gpu.append(price_ph / gpu_count)
                        total_gpus_in_type += gpu_count
                    
                    min_price_str = f"${min(prices_per_gpu):.2f}" if prices_per_gpu else "N/A"
                    max_price_str = f"${max(prices_per_gpu):.2f}" if prices_per_gpu else "N/A"
                    
                    summary_table.add_row(
                        gpu_type,
                        min_price_str,
                        max_price_str,
                        str(len(type_executors)), # Number of hosts/executors of this type
                        str(total_gpus_in_type)
                    )
                style_manager.console.print(summary_table)
                
                choice = Prompt.ask("\nEnter GPU type from list to see details (or type 'all', 'exit')", default="exit", console=style_manager.console).strip()
                if choice.lower() == 'exit' or not choice:
                    return
                if choice.lower() == 'all':
                    # If user types 'all', we can show details for all types one by one or a combined list.
                    # For now, let's just re-iterate and call _show_gpu_type_details for each.
                    # This could be long, so maybe just pick top N types or prompt again.
                    # For simplicity, let's just say 'all' is not implemented for detailed view yet.
                    style_manager.console.print("[yellow]'all' option for detailed view is not yet implemented. Please pick a specific type.[/yellow]")
                    return # Or loop back to prompt
                
                # Find a matching key for user's choice
                normalized_choice = choice.upper()
                matched_key_choice = next((key for key in grouped_by_gpu.keys() if normalized_choice in key.upper()), None)
                if matched_key_choice:
                    selected_gpu_type_to_detail = matched_key_choice
                else:
                    style_manager.console.print(f"[yellow]GPU type '{choice}' not found.[/yellow]")
                    return

            if selected_gpu_type_to_detail:
                style_manager.console.print(f"\n[bold magenta]Details for GPU Type: {selected_gpu_type_to_detail}[/bold magenta]")
                # Call a new helper method to show detailed table for this type
                self._show_gpu_type_details_table(selected_gpu_type_to_detail, grouped_by_gpu[selected_gpu_type_to_detail])

        except requests.exceptions.HTTPError as e:
            # ... (similar error handling as list_active_pods) ...
            style_manager.console.print(f"[bold red]API Error fetching executors: {e.response.status_code} - {e.response.text}[/bold red]")
        except requests.exceptions.RequestException as e:
            style_manager.console.print(f"[bold red]Request Error connecting to server: {e}[/bold red]")
        except Exception as e:
            style_manager.console.print(f"[bold red]Error listing available pods: {type(e).__name__} - {e}[/bold red]")

    def _show_gpu_type_details_table(self, gpu_type: str, executors_of_type: list[dict]):
        """Displays a detailed table for executors of a specific GPU type."""
        if not executors_of_type:
            style_manager.console.print(f"[yellow]No executors found for GPU type: {gpu_type}[/yellow]")
            return

        # Sort by price per GPU (ascending) - this is a simple sort, not Pareto
        # For price_per_gpu, ensure gpu_count > 0
        def get_price_per_gpu(e):
            price = e.get("price_per_hour")
            count = e.get("specs", {}).get("gpu", {}).get("count", 1)
            if isinstance(price, (int, float)) and count > 0:
                return price / count
            return float('inf') # Sort non-priced or invalid ones to the end

        sorted_executors = sorted(executors_of_type, key=get_price_per_gpu)

        detail_table = Table(box=box.ROUNDED, show_lines=True, header_style="bold cyan")
        # Columns similar to lium ls details
        detail_table.add_column("Host ID (HUID)", style="dim", min_width=18) # Or Executor ID
        detail_table.add_column("GPU Config", style="yellow", min_width=10)
        detail_table.add_column("$/GPU/hr", style="green", justify="right")
        detail_table.add_column("VRAM/GPU (GB)", style="magenta", justify="right")
        detail_table.add_column("RAM (GB)", style="blue", justify="right")
        detail_table.add_column("Location", style="white", min_width=10)
        detail_table.add_column("Down (Mbps)", style="cyan", justify="right")
        detail_table.add_column("Up (Mbps)", style="cyan", justify="right")
        detail_table.add_column("DinD Support", justify="center") # Removed style, will apply per cell
        # Add more columns as needed based on available data and lium ls: Disk, PCIe, Mem speed, TFLOPs, Net Up/Down etc.

        for exec_data in sorted_executors:
            host_id = exec_data.get("id") # This is likely the executor UUID
            # Generate HUID for display if preferred, or show UUID directly
            display_id = generate_pod_huid(host_id) if host_id else "N/A" 
            
            gpu_count = exec_data.get("specs", {}).get("gpu", {}).get("count", 1)
            gpu_config_str = f"{gpu_count}x {gpu_type}"

            price_per_gpu_val = get_price_per_gpu(exec_data)
            price_per_gpu_display = f"${price_per_gpu_val:.2f}" if price_per_gpu_val != float('inf') else "N/A"

            # VRAM per GPU - Assuming API provides total VRAM for the host or per GPU details
            # This is a placeholder, actual data structure from API needed
            vram_per_gpu_gb = "N/A"
            gpu_specs_list = exec_data.get("specs",{}).get("gpu",{}).get("details",[])
            if gpu_specs_list and isinstance(gpu_specs_list[0].get("capacity"), (int,float)):
                vram_mib = gpu_specs_list[0]["capacity"]
                vram_per_gpu_gb = f"{vram_mib / 1024:.0f}" 
            elif exec_data.get("specs",{}).get("gpu",{}).get("total_capacity_mib"): # hypothetical field
                 total_vram_mib = exec_data["specs"]["gpu"]["total_capacity_mib"]
                 if gpu_count > 0: vram_per_gpu_gb = f"{(total_vram_mib / gpu_count) / 1024:.0f}"
            
            ram_gb = "N/A"
            ram_total_kb = exec_data.get("specs",{}).get("ram",{}).get("total")
            if isinstance(ram_total_kb, (int, float)) and ram_total_kb > 0:
                ram_gb = f"{ram_total_kb / 1024 / 1024:.0f}"

            location = exec_data.get("location", {}).get("country", "N/A") # Example from lium
            network_download_speed_val = exec_data.get('specs', {}).get('network', {}).get('download_speed')
            network_upload_speed_val = exec_data.get('specs', {}).get('network', {}).get('upload_speed')

            download_speed_display = f"{network_download_speed_val:.1f} Mbps" if isinstance(network_download_speed_val, (int, float)) else "N/A"
            upload_speed_display = f"{network_upload_speed_val:.1f} Mbps" if isinstance(network_upload_speed_val, (int, float)) else "N/A"

            dind_support = exec_data.get("specs", {}).get("sysbox_runtime", False)
            dind_display = "[green]✅[/green]" if dind_support else "[red]❌[/red]"

            detail_table.add_row(
                display_id,
                gpu_config_str,
                price_per_gpu_display,
                vram_per_gpu_gb,
                ram_gb,
                location,
                download_speed_display,
                upload_speed_display,
                dind_display
            )
        style_manager.console.print(detail_table)


        
        