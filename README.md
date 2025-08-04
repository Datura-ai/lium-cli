<div align="center">

# 🚀 Lium CLI

[![PyPI version](https://badge.fury.io/py/lium-cli.svg)](https://badge.fury.io/py/lium-cli)
[![Python Support](https://img.shields.io/pypi/pyversions/lium-cli.svg)](https://pypi.org/project/lium-cli/)
[![Downloads](https://pepy.tech/badge/lium-cli)](https://pepy.tech/project/lium-cli)

**A powerful command-line interface for managing GPU cloud computing resources on the Lium platform**

![Lium CLI Demo](lium-cli-demo.gif)

</div>

---

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [🚀 Lium CLI](#-lium-cli)
  - [🌟 Overview](#-overview)
  - [⚡ Quick Start](#-quick-start)
  - [🎯 Features](#-features)
  - [📦 Installation](#-installation)
    - [Via pip (Recommended)](#via-pip-recommended)
    - [From Source](#from-source)
    - [Development Setup](#development-setup)
  - [🏁 Getting Started](#-getting-started)
  - [📚 Commands](#-commands)
    - [🆔 Lium Commands](#-lium-commands)
    - [🐳 Pod Management](#-pod-management)
    - [📋 Template Management](#-template-management)
    - [💳 Payment & Wallet Management](#-payment--wallet-management)
    - [⚙️ Configuration](#️-configuration)
    - [🎨 Theme Management](#-theme-management)
    - [🔗 SSH Access](#-ssh-access)
  - [⚙️ Configuration](#️-configuration-1)
  - [💡 Examples](#-examples)
  - [🤝 Contributing](#-contributing)
  - [📄 License](#-license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## 🌟 Overview

Lium CLI is a comprehensive command-line tool for interacting with the Lium GPU cloud computing platform. It provides developers and researchers with powerful tools to manage GPU resources, deploy containerized applications, and handle payments seamlessly.

### Key Benefits:
- **🚀 Lightning Fast**: Deploy GPU workloads in seconds
- **💰 Cost Effective**: Pay only for what you use with TAO token integration
- **🔧 Developer Friendly**: Intuitive CLI commands with rich output formatting
- **🐳 Docker Native**: First-class support for containerized applications
- **🔒 Secure**: Built-in authentication and encrypted communications
- **🎨 Customizable**: Multiple themes and extensive configuration options

---

## ⚡ Quick Start

```bash
# Install Lium CLI
pip install -U lium-cli

# Initialize and authenticate
lium init

# List available machines
lium pod ls

# Deploy your first pod
git clone https://github.com/Datura-ai/lium-cli.git
cd lium-cli
lium pod run --machine 8XA100 --dockerfile examples/pytorch/Dockerfile
```

---

## 🎯 Features

### 🆔 **Lium Account Management**
1. **Initialize your Lium CLI**
   - Account creation and login
   - API key management
   - Configuration setup
   - Creating a Lium account (or logging in)
   - Setting up API credentials
   - Configuring default preferences

### 🐳 **Advanced Pod Management**
- **Deploy Pods**: Launch GPU instances with custom Docker containers
- **Monitor Resources**: Real-time status monitoring and resource tracking
- **Flexible Deployment**: Support for Dockerfiles, pre-built images, and interactive environments
- **Auto-scaling**: Dynamic resource allocation based on workload demands

### 💳 **Integrated Payment System**
- **TAO Token Integration**: Native support for Bittensor network payments
- **Wallet Management**: Create and manage multiple payment wallets
- **Cost Tracking**: Transparent pricing and usage monitoring
- **Automated Billing**: Seamless payment processing for resource usage

### ⚙️ **Rich Configuration Management**
- **Flexible Settings**: Comprehensive configuration options
- **Profile Management**: Multiple configuration profiles
- **Environment Variables**: Support for environment-based configuration
- **Secure Storage**: Encrypted credential storage

---

## 📦 Installation

### Via pip (Recommended)

```bash
pip install -U lium-cli
```

### From Source

```bash
git clone https://github.com/Datura-ai/lium-cli.git
cd lium-cli
pip install -e .
```

### Development Setup

For contributing to the project:

```bash
git clone https://github.com/Datura-ai/lium-cli.git
cd lium-cli
pip install -e ".[dev]"
```

---

## 🏁 Getting Started

Deploy a new pod on the Lium platform.

**Syntax:**
```bash
lium pod run [OPTIONS]
```

**Options:**
- `--machine TEXT`: Machine type to rent (e.g., "8XA100", "4XA6000") [required]
- `--dockerfile TEXT`: Path to Dockerfile for building custom image
- `--docker-image TEXT`: Pre-built Docker image to use
- `--template-id TEXT`: UUID of saved template to use
- `--ports TEXT`: Ports to expose (format: "external:internal" or just "port")
- `--volume TEXT`: Volumes to mount (format: "host_path:container_path")
- `--env TEXT`: Environment variables (format: "KEY=value")
- `--name TEXT`: Custom name for the pod
- `--no-follow`: Don't follow pod logs after creation
- `--interactive / --no-interactive`: Enable interactive mode for shell access

**Examples:**

```bash
# Deploy with a Dockerfile
lium pod run --machine 8XA100 --dockerfile ./Dockerfile

# Deploy with pre-built image
lium pod run --machine 4XA6000 --docker-image nvidia/cuda:11.8-runtime-ubuntu20.04

# Deploy with custom configuration
lium pod run \
  --machine 8XA100 \
  --docker-image pytorch/pytorch:latest \
  --ports 8080:80 \
  --env "MODEL_NAME=bert-base" \
  --volume "/data:/workspace/data" \
  --name "my-training-job"

# Interactive deployment with shell access
lium pod run --machine 2XA100 --docker-image ubuntu:22.04 --interactive
```

**Interactive Mode Features:**
- Real-time logs and status updates
- Direct shell access to running containers
- Port forwarding for web applications
- File transfer capabilities

**Advanced Usage:**

```bash
# Use saved template
lium pod run --machine 8XA100 --template-id abc123def456

# Multiple port mappings
lium pod run --machine 4XA6000 --docker-image jupyter/tensorflow-notebook \
  --ports 8888:8888 --ports 6006:6006

# Multiple environment variables
lium pod run --machine 2XA100 --docker-image python:3.9 \
  --env "API_KEY=your_key" --env "DEBUG=true" --env "WORKERS=4"
```

The `run` command automatically handles:
- Docker image building (if Dockerfile provided)
- Resource allocation and scheduling
- Network configuration and port mapping
- Volume mounting and data persistence
- Environment variable injection
- Payment processing and billing

---

## 📚 Commands

### 🆔 Lium Commands

Initialize and manage your Lium account:

```bash
# Initialize Lium CLI (create account or login)
lium init

# Check initialization status
lium status
```

### 🐳 Pod Management

Manage your GPU pods:

```bash
# List all running pods
lium pod ls

# Show detailed pod information
lium pod show <pod-id>

# Stop a running pod
lium pod stop <pod-id>

# Get pod logs
lium pod logs <pod-id>

# Connect to pod via SSH
lium pod ssh <pod-id>
```

### 📋 Template Management

Save and reuse deployment configurations:

```bash
# Create a template from Dockerfile
lium template create --dockerfile Dockerfile --name "my-template"

# Create template from existing image
lium template create --docker-image pytorch/pytorch:latest --name "pytorch-base"

# List saved templates
lium template ls

# Use template for deployment
lium pod run --machine 8XA100 --template-id <template-uuid>
```

### 💳 Payment & Wallet Management

Manage TAO tokens and payments:

```bash
# Check TAO balance
lium pay balance

# Create new wallet
lium pay wallet create

# Transfer TAO tokens
lium pay transfer --amount 10.5 --destination <wallet-address>

# View payment history
lium pay history
```

### ⚙️ Configuration

Manage CLI configuration:

```bash
# View current configuration
lium config get

# Set configuration values
lium config set --api-key <your-api-key>
lium config set --docker-username <username> --docker-password <password>

# Reset configuration
lium config reset
```

### 🎨 Theme Management

Customize CLI appearance:

```bash
# List available themes
lium theme list

# Set theme
lium theme set dark

# Preview theme
lium theme preview monokai
```

### 🔗 SSH Access

Direct SSH access to pods:

```bash
# SSH into running pod
lium ssh <pod-id>

# Execute command on pod
lium ssh <pod-id> --command "nvidia-smi"

# File transfer via SCP
lium ssh <pod-id> --upload local_file.txt:/remote/path/
lium ssh <pod-id> --download /remote/file.txt:./local_path/
```

---

## ⚙️ Configuration

The CLI stores configuration in `~/.lium/config.yaml`. Key settings include:

- `api_key`: Your Lium API key
- `docker_username`/`docker_password`: Docker Hub credentials
- `server_url`: "https://lium.io"
- `tao_pay_url`: "https://pay-api.lium.io"
- `network`: Bittensor network ("finney" or "testnet")

**Manual Configuration:**
```yaml
api_key: "your-api-key-here"
docker_username: "your-docker-username" 
docker_password: "your-docker-password"
server_url: "https://lium.io"
tao_pay_url: "https://pay-api.lium.io"
network: "finney"
```

---

## 💡 Examples

Transfer TAO tokens for Lium services.

**Basic Transfer:**
```bash
lium pay transfer --amount 5.0 --destination 5GK8...
```

**Advanced Examples:**

```bash
# Transfer with memo
lium pay transfer --amount 10.5 --destination 5GK8... --memo "Payment for GPU hours"

# Check balance before transfer
lium pay balance
lium pay transfer --amount 2.0 --destination 5GK8...

# View transaction history
lium pay history --limit 10
```

**Multi-step Workflow:**
```bash
# 1. Check available machines and pricing
lium pod ls

# 2. Check your TAO balance
lium pay balance

# 3. Deploy workload
lium pod run --machine 8XA100 --docker-image pytorch/pytorch:latest

# 4. Monitor usage and costs
lium pod show <pod-id>
lium pay history
```

**Integration with CI/CD:**
```bash
#!/bin/bash
# Deploy script for automated workflows

# Set configuration via environment variables
export LIUM_API_KEY="your-api-key"
export LIUM_DOCKER_USERNAME="your-username"
export LIUM_DOCKER_PASSWORD="your-password"

# Deploy and capture pod ID
POD_ID=$(lium pod run --machine 4XA6000 --dockerfile Dockerfile --format json | jq -r '.pod_id')

# Wait for completion
lium pod wait $POD_ID --timeout 3600

# Download results
lium ssh $POD_ID --download /workspace/results:./results/

# Cleanup
lium pod stop $POD_ID
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the Repository**
2. **Create a Feature Branch**: `git checkout -b feature/amazing-feature`
3. **Commit Changes**: `git commit -m 'Add amazing feature'`
4. **Push to Branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

**Development Guidelines:**
- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting

**Useful Links:**
- **[GitHub Issues](https://github.com/Datura-ai/lium-cli/issues)** — Bug reports and feature requests
- **[Discussions](https://github.com/Datura-ai/lium-cli/discussions)** — Community discussions
- **[Documentation](https://docs.lium.ai)** — Comprehensive guides and API reference

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy Computing with Lium! 🚀✨**