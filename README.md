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

# Backend (dev)
cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --port 8080

# Frontend (dev)
cd frontend && npm run dev

# Tests
source .venv/bin/activate && python -m pytest tests/backend/ -v
```

## Configuration

All environment variables use the `MC_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `MC_DATACENTER_CODE` | 2-letter datacenter identifier | `dc` |
| `MC_IP_RANGE_START` | Start of allocatable IP range | — |
| `MC_IP_RANGE_END` | End of allocatable IP range | — |
| `MC_DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./minicloud.db` |

## Documentation

- [Architecture & Design](docs/architecture.md) — System architecture, component design, data flow
- [API Reference](docs/api.md) — REST API routes and schemas
- [Implementation Plan](docs/plan.md) — Phased build plan with milestones
- [Networking](docs/networking.md) — WireGuard mesh, bridged VMs, IP allocation
- [Hypervisor Drivers](docs/drivers.md) — KVM, Multipass, Hyper-V driver details

## License

Private — all rights reserved.
