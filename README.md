<div align="center">

# Lium CLI 
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.com/channels/799672011265015819/1291754566957928469)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

**A powerful command-line interface for managing GPU cloud computing resources on the Celium platform**

---

</div>

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [Install from PyPI](#install-from-pypi)
  - [Install from source](#install-from-source)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [Initialization](#initialization)
  - [Pod Management](#pod-management)
  - [Template Management](#template-management)
  - [Configuration](#configuration)
  - [Payment](#payment)
  - [Theme Management](#theme-management)
- [Examples](#examples)
- [Configuration](#configuration-1)
- [Support](#support)

---

## Overview

Lium CLI (formerly Celium CLI) is a comprehensive command-line tool for interacting with the Celium GPU cloud computing platform. It provides developers and researchers with powerful tools to manage GPU resources, deploy containerized applications, and handle payments seamlessly.

### Key Features

- **🚀 Easy Setup**: One-command initialization with guided setup
- **🖥️ GPU Management**: Deploy and manage pods across various GPU types (H100, RTX 4090, A100, etc.)
- **🐳 Docker Integration**: Built-in Docker Hub support and template management
- **💳 Payment Processing**: Seamless TAO token payments via Bittensor integration
- **🎨 Rich Interface**: Beautiful, colorized CLI output with progress indicators
- **⚡ Fast Operations**: Optimized for quick deployments and management
- **🔧 Template System**: Create and manage reusable deployment templates
- **🔐 SSH Integration**: Automatic SSH key management and secure connections

## Installation

### Install from PyPI

```bash
pip install -U celium-cli
```

### Install from source

1. **Create and activate a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Clone the repository**
```bash
git clone https://github.com/Datura-ai/celium-cli.git
cd celium-cli
```

3. **Install the package**
```bash
pip3 install .
```

## Quick Start

1. **Initialize your Celium CLI**
```bash
lium init
```
This will guide you through:
- Creating a Celium account (or logging in)
- Email verification
- API key generation
- Docker Hub setup
- SSH key configuration

2. **List available GPU resources**
```bash
lium pod ls
```

3. **Deploy your first pod**
```bash
lium pod run --docker-image nvidia/cuda:latest
```

4. **Check your running pods**
```bash
lium pod ps
```

## Commands

### Initialization

#### `lium init`
Complete setup and initialization process for first-time users.

**Features:**
- Account creation or login
- Email verification with optional payment
- API key generation
- Docker Hub configuration
- SSH key management

```bash
lium init
```

### Pod Management

#### `lium pod run` (alias: `lium p run`)
Deploy a new pod on the Celium platform.

**Options:**
- `--machine TEXT`: Specify machine by name
- `--docker-image TEXT`: Use existing Docker image
- `--dockerfile TEXT`: Build from Dockerfile
- `--pod-name TEXT`: Custom pod name
- `--template`: Use template-based deployment

**Examples:**
```bash
# Deploy with specific image
lium pod run --docker-image nvidia/cuda:latest

# Deploy with custom machine and pod name
lium pod run --machine 8xH100 --docker-image pytorch/pytorch:latest --pod-name ml-training

# Interactive deployment
lium pod run
```

#### `lium pod ps` (alias: `lium p ps`)
List all active pods with detailed information.

**Features:**
- Pod status with color coding
- GPU specifications
- Uptime and cost tracking
- Human-readable identifiers (HUID)

```bash
lium pod ps
```

#### `lium pod ls` (alias: `lium p ls`)
List available executors/machines.

**Options:**
- `--gpu-type TEXT`: Filter by GPU type (H100, RTX4090, A100, etc.)

**Examples:**
```bash
# List all available machines
lium pod ls

# Filter by GPU type
lium pod ls --gpu-type H100
```

#### `lium pod rm` (alias: `lium p rm`)
Terminate one or more pods.

**Options:**
- `--all`: Terminate all pods
- `--yes, -y`: Skip confirmation prompts

**Examples:**
```bash
# Terminate specific pod
lium pod rm swift-hawk-a2

# Terminate all pods
lium pod rm --all --yes
```

### Template Management

#### `lium template create` (alias: `lium t create`)
Create reusable deployment templates.

**Options:**
- `--dockerfile TEXT`: Build from Dockerfile
- `--docker-image TEXT`: Use existing Docker image

**Examples:**
```bash
# Create template from Dockerfile
lium template create --dockerfile ./Dockerfile --docker-image myrepo/myapp:latest

# Create template from existing image
lium template create --docker-image nginx:latest

# Interactive template creation
lium template create
```

### Configuration

#### `lium config` (aliases: `lium c`, `lium conf`)
Manage CLI configuration settings.

**Subcommands:**
- `set`: Set configuration values
- `get`: Display current configuration
- `unset`: Remove configuration values
- `show`: Display entire configuration file
- `path`: Show configuration file path

**Configuration Keys:**
- `docker_username`: Docker Hub username
- `docker_password`: Docker Hub password
- `server_url`: Celium server URL
- `tao_pay_url`: Tao Pay server URL
- `api_key`: API key for Celium services
- `network`: Network to use (default: finney)

**Examples:**
```bash
# Set configuration values
lium config set --docker-username myuser --api-key abc123

# View current configuration
lium config get

# Remove a configuration value
lium config unset docker_password

# Show configuration file location
lium config path
```

### Payment

#### `lium pay`
Transfer TAO tokens for Celium services.

**Options:**
- `--wallet-name TEXT`: Bittensor wallet name
- `--amount FLOAT`: Amount to transfer

**Features:**
- USD to TAO conversion
- Wallet integration
- Transfer confirmation
- Customer account linking

**Examples:**
```bash
# Transfer with specific wallet and amount
lium pay --wallet-name my-wallet --amount 50.0

# Interactive payment
lium pay
```

### Theme Management

#### `lium theme`
Manage CLI display themes.

**Subcommands:**
- `set`: Set display theme
- `list`: List available themes
- `current`: Show current theme

**Examples:**
```bash
# Set theme
lium theme set dark

# List available themes
lium theme list

# Show current theme
lium theme current
```

## Examples

### Complete Workflow Example

```bash
# 1. Initialize CLI
lium init

# 2. Create a template for your application
lium template create --dockerfile ./Dockerfile --docker-image myapp:latest

# 3. Deploy your application
lium pod run --template myapp:latest --pod-name production-app

# 4. Check deployment status
lium pod ps

# 5. Add funds if needed
lium pay --amount 25.0

# 6. Scale up with more pods
lium pod run --machine 4xRTX4090 --docker-image myapp:latest --pod-name worker-1
lium pod run --machine 4xRTX4090 --docker-image myapp:latest --pod-name worker-2

# 7. Monitor all pods
lium pod ps

# 8. Clean up when done
lium pod rm --all
```

### GPU-Specific Deployments

```bash
# Deploy on high-end GPUs for training
lium pod run --machine 8xH100 --docker-image pytorch/pytorch:latest --pod-name training-job

# Deploy on cost-effective GPUs for inference
lium pod run --machine 4xRTX4090 --docker-image tensorflow/tensorflow:latest --pod-name inference-server

# List available GPU types
lium pod ls --gpu-type H100
```

## Configuration

The CLI stores configuration in `~/.celium/config.yaml`. Key settings include:

```yaml
api_key: "your-api-key"
server_url: "https://celiumcompute.ai"
tao_pay_url: "https://pay-api.celiumcompute.ai"
network: "finney"
docker_username: "your-docker-username"
docker_password: "your-docker-password"
```

### Global Options

- `--version`: Show version information
- `--commands`: Display command tree
- `--help`: Show help information

## Support

- **[GitHub Issues](https://github.com/Datura-ai/celium-cli/issues)** — Bug reports and feature requests
- **[Discord](https://discord.com/channels/799672011265015819/1291754566957928469)** — Community support and discussion
- **[Documentation](https://docs.celium.ai)** — Comprehensive guides and API reference

---

<div align="center">
<strong>Happy GPU Computing! 🚀</strong>
</div>