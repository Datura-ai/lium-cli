from functools import wraps
from celium_cli.src.services.validator import ValidationError
from celium_cli.src.utils import console


def catch_validation_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            console.print(f"[bold red]Error: [/bold red] {str(e)}")
        except Exception as e:
            console.print_exception(show_locals=True)
    return wrapper
