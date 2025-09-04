"""Tests for utility functions."""
import pytest
from unittest.mock import patch, MagicMock
from cli.utils import loading_status, handle_errors


def test_loading_status_success():
    """
    Test loading_status context manager success case.
    Expected: context manager completes without exceptions.
    """
    # Arrange - no setup needed
    
    # Act & Assert - context manager should not raise
    with loading_status("Testing", "Success"):
        pass  # No exception should be raised


def test_loading_status_exception_propagation():
    """
    Test that loading_status propagates exceptions.
    Expected: exception is re-raised after being caught.
    """
    # Arrange - prepare exception
    test_exception = ValueError("Test error")
    
    # Act & Assert - exception should be propagated
    with pytest.raises(ValueError, match="Test error"):
        with loading_status("Testing", "Success"):
            raise test_exception


@patch('cli.utils.console')
def test_handle_errors_decorator(mock_console):
    """
    Test handle_errors decorator functionality.
    Expected: decorator catches exceptions and shows error via console.
    """
    # Arrange - create decorated function that raises
    @handle_errors
    def failing_function():
        raise ValueError("Test error")
    
    # Act - call decorated function
    failing_function()
    
    # Assert - console.error was called
    mock_console.error.assert_called()


def test_loading_status_with_empty_success_message():
    """
    Test loading_status with empty success message.
    Expected: context manager works with empty success message.
    """
    # Arrange - no setup needed
    
    # Act & Assert - should complete without issues
    with loading_status("Testing", ""):
        pass