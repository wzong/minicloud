# Minicloud

Self-hosted AWS EKS for bare metal — a Docker-containerized web app that manages on-premises datacenters, provisions VMs on physical hosts via SSH, connects datacenters across NAT networks via WireGuard, and bootstraps Kubernetes clusters using k3s/k3sup.

## Overview

Minicloud turns a set of physical machines (Linux, macOS, or Windows) into a private cloud platform. Each Minicloud instance manages one datacenter — a group of hosts under the same NAT network. Multiple datacenters are connected via WireGuard tunnels for cross-network routing.

**Key capabilities:**
- Register and manage physical hosts via SSH
- Provision VMs with static IPs, bridged networking, and cloud-init
- Manage SSH keys (generate or import)
- Allocate and track IP addresses across a configurable range
- Bootstrap Kubernetes clusters (k3s) with control plane HA and worker nodes
- Connect datacenters across NAT boundaries via WireGuard mesh

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), aiosqlite, asyncssh, Jinja2 |
| Frontend | React 18, TypeScript, Ant Design 5, React Router 6, TanStack Query, Vite |
| Infrastructure | Docker (multi-stage build), WireGuard, k3s + k3sup, SQLite |

## Quick Start

```bash
# Docker (production)
cd docker && docker compose up --build
```

### Backend dev

Create the local Python venv once from the repo root using Python 3.12.

If `python3.12` is not available on macOS, install it first:

```bash
brew install python@3.12
# add Homebrew Python 3.12 to your path if necessary
export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"
```

Then create the venv:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Then run the backend from the `backend` folder, overriding the default Docker-only paths with local data paths:

```bash
cd backend
source ../.venv/bin/activate
mkdir -p ~/data/minicloud/ssh_keys
export MC_DB_PATH=~/data/minicloud/minicloud.db
export MC_SSH_KEY_DIR=~/data/minicloud/ssh_keys/
export MC_WG_PRIVATE_KEY_PATH=~/data/minicloud/wg_private.key
uvicorn app.main:app --reload --port 8080
```

### Frontend dev

```bash
cd frontend
npm install
npm run dev
```

### Tests

Activate the same venv and run:

```bash
source .venv/bin/activate
python -m pytest tests/backend/ -v
```

## Configuration

All environment variables use the `MC_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `MC_DATACENTER_CODE` | 2-letter datacenter identifier | `dc` |
| `MC_IP_RANGE_START` | Start of allocatable IP range | — |
| `MC_IP_RANGE_END` | End of allocatable IP range | — |
| `MC_DB_PATH` | SQLite database path | `/app/data/minicloud.db` inside Docker; override locally with `~/data/minicloud/minicloud.db` when running from `backend` |
| `MC_SSH_KEY_DIR` | SSH key directory | `/app/data/ssh_keys` inside Docker; override locally with `~/data/minicloud/ssh_keys` when running from `backend` |
| `MC_WG_PRIVATE_KEY_PATH` | WireGuard private key path | `/app/data/wg_private.key` inside Docker; override locally with `~/data/minicloud/wg_private.key` when running from `backend` |

## Documentation

- [Architecture & Design](docs/architecture.md) — System architecture, component design, data flow
- [API Reference](docs/api.md) — REST API routes and schemas
- [Implementation Plan](docs/plan.md) — Phased build plan with milestones
- [Networking](docs/networking.md) — WireGuard mesh, bridged VMs, IP allocation
- [Hypervisor Drivers](docs/drivers.md) — KVM, Multipass, Hyper-V driver details

## License

Private — all rights reserved.
