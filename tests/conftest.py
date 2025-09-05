"""Pytest configuration and shared fixtures."""
import tempfile
import os
from unittest.mock import MagicMock
from typing import Dict, Any
import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config(monkeypatch):
    """Create temporary config directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = os.path.join(temp_dir, ".lium")
        os.makedirs(config_dir, exist_ok=True)
        monkeypatch.setenv("HOME", temp_dir)
        yield config_dir


@pytest.fixture
def mock_lium_api():
    """Mock Lium SDK API calls."""
    mock_api = MagicMock()
    # Mock common responses
    mock_api.ls.return_value = []
    mock_api.get_executor.return_value = None
    return mock_api


@pytest.fixture
def sample_executors() -> list[Dict[str, Any]]:
    """Sample executor data for testing."""
    return [
        {
            "huid": "test-executor-1",
            "gpu_type": "RTX4090",
            "gpu_count": 1,
            "price_per_gpu_hour": 0.5,
            "price_per_hour": 0.5,
            "location": {"country": "US", "country_code": "US"},
            "specs": {
                "gpu": {"details": [{"capacity": 24000}]},
                "ram": {"total": 32768},
                "hard_disk": {"total": 1000000}
            }
        }
    ]