"""Display formatting for config show command."""


def format_config(config_data: dict, config_path: str, show_all: bool) -> tuple[str, str]:
    """Format config data for display. Returns (path, content)."""
    if not config_data:
        return config_path, "Configuration is empty"

    lines = []

    skip_sections = {'last_selection'} if not show_all else set()
    section_order = ['api', 'ssh', 'ui', 'template']
    shown_sections = set()

    for section_name in section_order:
        if section_name in config_data and section_name not in skip_sections:
            values = config_data[section_name]
            for key, value in values.items():
                if key in ['api_key'] and value:
                    display_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                elif key == 'data' and len(str(value)) > 100:
                    display_value = str(value)[:100] + '...'
                else:
                    display_value = value
                lines.append(f"{key} = {display_value}")
            shown_sections.add(section_name)

    for section, values in config_data.items():
        if section in skip_sections or section in shown_sections:
            continue
        for key, value in values.items():
            if key == 'data' and len(str(value)) > 100:
                display_value = str(value)[:100] + '...'
            else:
                display_value = value
            lines.append(f"{key} = {display_value}")

    if not show_all:
        hidden_sections = [s for s in config_data.keys() if s in {'last_selection'}]
        if hidden_sections:
            lines.append(f"Hidden: {', '.join(hidden_sections)} (use --all to show)")

    return config_path, "\n".join(lines)
