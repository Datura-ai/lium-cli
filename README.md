# Lium CLI

Command-line interface for managing GPU pods on the Lium platform.

## Installation

```bash
pip install lium-cli
```

## Quick Start

```bash
# First-time setup
lium init

# List available executors (GPU machines)
lium ls

# Create a pod
lium up 1  # Use executor #1 from previous ls

# List your pods
lium ps

# Copy files to pod
lium scp 1 ./my_script.py

# SSH into a pod
lium ssh <pod-name>

# Stop a pod
lium rm <pod-name>
```

## Commands

### Core Commands

- `lium init` - Initialize configuration (API key, SSH keys)
- `lium ls [GPU_TYPE]` - List available executors
- `lium up [EXECUTOR]` - Create a pod on an executor
- `lium ps` - List active pods
- `lium ssh <POD>` - SSH into a pod
- `lium exec <POD> <COMMAND>` - Execute command on pod
- `lium scp <POD> <LOCAL_FILE> [REMOTE_PATH]` - Copy files to pods
- `lium rm <POD>` - Remove/stop a pod
- `lium templates [SEARCH]` - List available Docker templates

### Command Examples

```bash
# Filter executors by GPU type
lium ls H100
lium ls A100

# Create pod with specific options
lium up --name my-pod --template pytorch --yes

# Execute commands
lium exec my-pod "nvidia-smi"
lium exec my-pod "python train.py"

# Copy files to pods
lium scp my-pod ./script.py                    # Copy to /root/script.py
lium scp 1 ./data.csv /root/data/             # Copy to specific directory
lium scp all ./config.json                    # Copy to all pods
lium scp 1,2,3 ./model.py /root/models/       # Copy to multiple pods

# Remove multiple pods
lium rm my-pod-1 my-pod-2
lium rm all  # Remove all pods
```

## Features

- **Pareto Optimization**: `ls` command shows optimal executors with ★ indicator
- **Index Selection**: Use numbers from `ls` output in `up` command
- **Full-Width Tables**: Clean, readable terminal output
- **Cost Tracking**: See spending and hourly rates in `ps`
- **Interactive Setup**: `init` command for easy onboarding

## Configuration

Configuration is stored in `~/.lium/config.ini`:

```ini
[api]
api_key = your-api-key-here

[ssh]
key_path = /home/user/.ssh/id_ed25519
```

You can also use environment variables:
```bash
export LIUM_API_KEY=your-api-key-here
```

## Requirements

- Python 3.9+
- lium-sdk >= 0.2.0

## Development

```bash
# Clone repository
git clone https://github.com/Datura-ai/lium-cli.git
cd lium-cli

# Install in development mode
pip install -e .
```

## License

MIT License - see [LICENSE](LICENSE) file for details.