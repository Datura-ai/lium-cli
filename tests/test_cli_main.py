"""Tests for main CLI entry point."""
import os
from cli.cli import cli


def test_cli_help(cli_runner):
    """
    Test that CLI shows help when run without commands.
    Expected: exit code 0 and "Usage:" text in output.
    """
    # Arrange - no setup needed
    
    # Act - run CLI without arguments
    result = cli_runner.invoke(cli, [])
    
    # Assert - success code and help in output
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_cli_version(cli_runner):
    """
    Test that --version command works.
    Expected: exit code 0 and version in output.
    """
    # Arrange - no setup needed
    
    # Act - run with --version
    result = cli_runner.invoke(cli, ["--version"])
    
    # Assert - success code and version present
    assert result.exit_code == 0
    assert "lium" in result.output.lower()


def test_cli_plugin_loading_no_crash(cli_runner, monkeypatch):
    """
    Test that plugin loading doesn't crash CLI.
    Expected: CLI starts even if plugins are unavailable.
    """
    # Arrange - disable completion to avoid side effects
    monkeypatch.setenv("_LIUM_COMPLETE", "1")
    
    # Act - run CLI
    result = cli_runner.invoke(cli, [])
    
    # Assert - CLI doesn't crash on plugin loading
    assert result.exit_code == 0


def test_cli_unknown_command(cli_runner):
    """
    Test reaction to non-existent command.
    Expected: error code and unknown command message.
    """
    # Arrange - no setup needed
    
    # Act - run with non-existent command
    result = cli_runner.invoke(cli, ["nonexistent"])
    
    # Assert - error code
    assert result.exit_code != 0