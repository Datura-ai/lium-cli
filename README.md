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
 ![quick start demo](https://vhs.charm.sh/vhs-1PbVchM8viEmMg8seSsGl7.gif)

## Commands

### Core Commands

- `lium init` - Initialize configuration (API key, SSH keys)
- `lium ls [GPU_TYPE]` - List available executors
- `lium up [EXECUTOR]` - Create a pod on an executor
- `lium ps` - List active pods
- `lium ssh <POD>` - SSH into a pod
- `lium exec <POD> <COMMAND>` - Execute command on pod
- `lium scp <POD> <LOCAL_FILE> [REMOTE_PATH]` - Copy files to pods
- `lium rsync <POD> <LOCAL_DIR> [REMOTE_PATH]` - Sync directories to pods
- `lium rm <POD>` - Remove/stop a pod
- `lium templates [SEARCH]` - List available Docker templates
- `lium image <IMAGE_NAME> <PATH>` - Build and deploy Docker image as template
- `lium fund` - Fund account with TAO from Bittensor wallet

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

# Sync directories to pods
lium rsync my-pod ./project                    # Sync to /root/project
lium rsync 1 ./data /root/datasets/           # Sync to specific directory
lium rsync all ./models                       # Sync to all pods
lium rsync 1,2,3 ./code /root/workspace/      # Sync to multiple pods

# Remove multiple pods
lium rm my-pod-1 my-pod-2
lium rm all  # Remove all pods

# Build and deploy Docker images
lium image my-app .                                   # Build from current directory
lium image my-model ./models                          # Build from models directory  
lium image web-server ./app --ports 22,8080          # Custom ports
lium image my-app . --ports 22,8000 --start-command "/start.sh"  # With start command

# Fund account with TAO
lium fund                           # Interactive mode
lium fund -w default -a 1.5        # Fund with specific wallet and amount
lium fund -w mywal -a 0.5 -y       # Skip confirmation
```

## Features

- **Pareto Optimization**: `ls` command shows optimal executors with ★ indicator
- **Index Selection**: Use numbers from `ls` output in `up` command
- **Full-Width Tables**: Clean, readable terminal output
- **Cost Tracking**: See spending and hourly rates in `ps`
- **Interactive Setup**: `init` command for easy onboarding
- **Docker Integration**: Build and deploy custom Docker images as templates
- **Cross-Platform Builds**: Automatic `linux/amd64` builds for server compatibility

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