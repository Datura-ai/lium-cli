from functools import wraps
from celium_cli.src.services.validator import ValidationError
from celium_cli.src.styles import style_manager


def catch_validation_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            style_manager.console.print(f"[bold red]Error: [/bold red] {str(e)}")
        except Exception as e:
            style_manager.console.print_exception(show_locals=True)
    return wrapper
