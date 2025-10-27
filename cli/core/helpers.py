"""Helper functions for the up command (extracted to avoid circular imports)."""

from typing import List, Optional

from cli.lium_sdk import ExecutorInfo, Lium, Template
from rich.prompt import Prompt
from rich.text import Text

from ..utils import (
    calculate_pareto_frontier,
    console,
    loading_status,
    resolve_executor_indices,
)


def _apply_executor_filters(
    executors: List[ExecutorInfo],
    gpu_count: Optional[int] = None,
    country_code: Optional[str] = None,
    ports: Optional[int] = None
) -> List[ExecutorInfo]:
    """Apply filters to executor list."""
    if gpu_count:
        executors = [e for e in executors if e.gpu_count == gpu_count]
    if country_code:
        executors = [
            e for e in executors
            if e.location and e.location.get('country_code', '').upper() == country_code.upper()
        ]
    if ports:
        executors = [
            e for e in executors
            if e.available_port_count and e.available_port_count >= ports
        ]
    return executors


def _build_filter_description(
    gpu: Optional[str] = None,
    count: Optional[int] = None,
    country: Optional[str] = None,
    ports: Optional[int] = None
) -> str:
    """Build a description of active filters."""
    filters = []
    if gpu:
        filters.append(f"GPU type={gpu}")
    if count:
        filters.append(f"GPU count={count}")
    if country:
        filters.append(f"country={country}")
    if ports:
        filters.append(f"min ports={ports}")
    return ', '.join(filters)


def _get_executor_id(executor_id: str) -> Optional[str]:
    """Resolve executor ID from index or return as-is."""
    if executor_id and executor_id.isdigit():
        resolved_ids, error_msg = resolve_executor_indices([executor_id])
        if error_msg:
            console.error(error_msg)
            if not resolved_ids:
                return None
        if resolved_ids:
            return resolved_ids[0]
    return executor_id


def _find_executor_by_id(lium: Lium, executor_id: str, ports: Optional[int] = None) -> Optional[ExecutorInfo]:
    """Find executor by ID with retry logic."""
    from cli.commands.ls import ls_store_executor

    original_id = executor_id
    executor_id = _get_executor_id(executor_id)

    if executor_id is None:
        return None

    executor = lium.get_executor(executor_id)

    # Single retry if not found
    if executor is None:
        ls_store_executor()
        executor_id = _get_executor_id(original_id)
        if executor_id is None:
            return None
        executor = lium.get_executor(executor_id)
        if executor is None:
            console.error(f"No executor found with ID '{original_id}'")
            console.info(f"Tip: {console.get_styled('lium ls', 'success')}")
            return None

    # Validate port count if specified
    if ports:
        if not executor.available_port_count or executor.available_port_count < ports:
            available = executor.available_port_count or 0
            console.error(
                f"Executor {executor.huid} has insufficient ports "
                f"(available: {available}, required: {ports})"
            )
            return None

    return executor


def _auto_select_executor(
    lium: Lium,
    gpu: Optional[str] = None,
    count: Optional[int] = None,
    country: Optional[str] = None,
    ports: Optional[int] = None
) -> Optional[ExecutorInfo]:
    """Automatically select best executor based on filters."""
    from cli.commands.ls import ls_store_executor

    executors = lium.ls(gpu_type=gpu)
    executors = _apply_executor_filters(executors, gpu_count=count, country_code=country, ports=ports)

    if not executors:
        if gpu is not None and gpu not in lium.gpu_types():
            console.error(f"GPU '{gpu}' Not recognized")
        else:
            filter_desc = _build_filter_description(gpu, count, country, ports)
            console.error(f"All matching GPUs are currently rented out. (filters: {filter_desc})")
        console.info(f"Tip: {console.get_styled('lium ls', 'success')}")
        return None

    # Store for potential index reference
    ls_store_executor(gpu_type=gpu)

    # Calculate Pareto frontier to get the best executors
    pareto_flags = calculate_pareto_frontier(executors)
    pareto_executors = [e for e, is_pareto in zip(executors, pareto_flags) if is_pareto]

    # Pick the best executor
    executor = pareto_executors[0] if pareto_executors else executors[0]

    # Don't print here - let the action handle the message after the step completes
    return executor


def select_executor(
    lium: Lium,
    gpu_type: Optional[str] = None,
    gpu_count: Optional[int] = None,
    country_code: Optional[str] = None,
    ports: Optional[int] = None
) -> Optional[ExecutorInfo]:
    """Interactive executor selection with optional filters."""
    from cli.commands.ls import show_executors

    console.warning("Select executor:")

    executors = lium.ls(gpu_type=gpu_type)
    executors = _apply_executor_filters(executors, gpu_count=gpu_count, country_code=country_code, ports=ports)

    if not executors:
        filter_desc = _build_filter_description(gpu_type, gpu_count, country_code, ports)
        if filter_desc:
            console.error(f"No executors available with filters: {filter_desc}")
        else:
            console.error("No executors available")
        return None

    showed_executors = show_executors(executors, limit=20)

    choice = Prompt.ask(
        "[cyan]Select executor by number[/cyan]",
        choices=[str(i) for i in range(1, len(showed_executors) + 1)],
        default="1"
    )

    chosen_executor = showed_executors[int(choice) - 1]
    return chosen_executor


def select_template(lium: Lium, filter_text: Optional[str] = None) -> Optional[Template]:
    """Interactive template selection."""
    from cli.commands.templates import show_templates

    console.warning("Select template:")

    templates = lium.templates(filter_text)

    if not templates:
        console.error("No templates available")
        return None

    show_templates(templates, numbered=True)

    choice = Prompt.ask(
        "Select template by number or enter text to filter",
        default="1"
    )

    if not choice.isnumeric():
        return select_template(lium, choice)

    chosen_template = templates[int(choice) - 1]
    text = Text(
        f"Selected: {chosen_template.docker_image}:{chosen_template.docker_image_tag}",
        style="dim"
    )
    console.dim(text, markup=False, highlight=False)
    return chosen_template
