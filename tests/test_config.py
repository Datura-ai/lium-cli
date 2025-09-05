"""Tests for configuration management."""
import os
from pathlib import Path
from cli.config import ConfigManager


def test_config_dir_creation(temp_config):
    """
    Test that config directory is created.
    Expected: ~/.lium directory exists after ConfigManager creation.
    """
    # Arrange - no setup needed (temp_config fixture sets up temp HOME)
    
    # Act - create ConfigManager
    config = ConfigManager()
    
    # Assert - directory is created
    assert config.config_dir.exists()
    assert config.config_dir.name == ".lium"


def test_config_set_and_get(temp_config):
    """
    Test basic set/get config operations.
    Expected: value is saved and read correctly.
    """
    # Arrange - create config
    config = ConfigManager()
    
    # Act - set and get value
    config.set("test.key", "test_value")
    result = config.get("test.key")
    
    # Assert - value is preserved
    assert result == "test_value"


def test_config_persistence(temp_config):
    """
    Test that config persists between sessions.
    Expected: value remains after recreating ConfigManager.
    """
    # Arrange - create first config and save value
    config1 = ConfigManager()
    config1.set("persist.test", "persistent_value")
    
    # Act - create new ConfigManager
    config2 = ConfigManager()
    result = config2.get("persist.test")
    
    # Assert - value persisted
    assert result == "persistent_value"


def test_config_default_template_id(temp_config):
    """
    Test that default template ID is returned.
    Expected: default_template_id is not None and contains UUID.
    """
    # Arrange - create config
    config = ConfigManager()
    
    # Act - get default template ID
    template_id = config.default_template_id
    
    # Assert - ID exists and looks like UUID
    assert template_id is not None
    assert len(template_id) == 36  # UUID length
    assert "-" in template_id  # UUID contains dashes