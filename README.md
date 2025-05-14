<div align="center">

# Celium CLI 
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.com/channels/799672011265015819/1291754566957928469)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

---

</div>

- [Overview](#overview)
- [Install](#install)
  - [Install from PyPI](#install-from-pypi)
  - [Install from source](#install-from-source)
- [Usage](#usage)
- [Support](#support)

---

## Overview

Celium CLI is a command-line tool for interacting with the Celium ecosystem. It provides a set of commands to help developers and users manage, monitor, and interact with Celium services and infrastructure directly from their terminal.

Key features:
- Easy installation and setup
- Rich CLI interface with helpful output
- Integration with Celium services

## Install

You can install `celium-cli` on your local machine directly from source, or from PyPI. 

### Install from PyPI

Run 
```
pip install -U celium-cli
```

### Install from source

1. Create and activate a virtual environment. 

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Clone the Celium CLI repo. 

```bash
git clone https://github.com/Datura-ai/celium-cli.git
cd celium-cli
```

3. Install

```bash
pip3 install .
```

## Usage

After installation, you can use the CLI by running:

```
celium-cli --help
```

This will display all available commands and options. For example, to see the version:

```
celium-cli --version
```

## Support

- [GitHub Issues](https://github.com/Datura-ai/celium-cli/issues) — for bug reports and feature requests
- [Discord](https://discord.com/channels/799672011265015819/1291754566957928469) — for community support and discussion