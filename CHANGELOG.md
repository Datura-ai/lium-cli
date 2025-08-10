# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-10

### Added
- **init command** - Interactive setup wizard for first-time users
- Pareto frontier optimization in `ls` command - shows optimal executors with ★ indicator
- Index-based executor selection in `up` command - use numbers from previous `ls` output
- Session storage for executor selection - enables quick selection by index
- Full-width tables across all commands for better terminal utilization
- Proper GPU configuration display in `ps` command showing actual GPU types
- Cost tracking in `ps` command showing spent amount and hourly rate
- Better error messages guiding users to run `lium init` when API key is missing

### Changed
- **BREAKING**: Now requires `lium-sdk>=0.2.0` from PyPI (no longer uses git dependency)
- Improved `ls` command with tighter table design and no units for cleaner display
- Enhanced `up` command with better template selection and confirmation flow
- Better `ps` command showing active pods with proper GPU configs and SSH commands
- Improved `templates` command removing unnecessary ID column and giving more space to tags
- Cleaner code throughout following PEP conventions
- All imports organized alphabetically and grouped properly
- Removed `from __future__ import annotations` (not needed in Python 3.9+)

### Fixed
- Rich markup issues with version numbers showing as colors
- SSH command generation missing spaces
- GPU configuration showing generic "GPU" instead of actual type
- Template selection colors and display issues
- Tables not taking full terminal width
- Various import and type hint improvements
- Bare except clauses replaced with specific exceptions

### Removed
- Unnecessary borders and decorations from tables
- Units (like "Gi") from numeric displays for cleaner look
- Confusing HUID column from templates display
- Debug code and trailing whitespace
- Unused helper functions

## [0.1.1] - Previous Release

- Initial release with basic pod management functionality
- Basic commands: ls, up, ps, exec, ssh, rm, templates
- Integration with lium-sdk from git
- Rich terminal UI with tables
- Basic error handling