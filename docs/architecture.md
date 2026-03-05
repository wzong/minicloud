# Architecture & Design

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Docker Container (Minicloud Instance = 1 Datacenter)           │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │  React SPA   │  │   FastAPI    │  │     WireGuard      │     │
│  │  (static)    │──│   Backend    │  │  Gateway/Tunnel    │     │
│  └──────────────┘  └──────┬───────┘  └─────────┬──────────┘     │
│                           │                    │                │
│                    ┌──────┴───────┐            │                │
│                    │   SQLite DB  │            │                │
│                    └──────────────┘            │                │
└───────────────────────────┼────────────────────┼────────────────┘
                            │ SSH                │ WireGuard
              ┌─────────────┼─────────────┐      │
              │             │             │      │
        ┌─────┴──────┐ ┌────┴──────┐ ┌────┴─┐    │
        │  Host A    │ │  Host B   │ │Host C│    │
        │ (Linux)    │ │ (macOS)   │ │(Win) │    │
        │ KVM/virsh  │ │ Multipass │ │HyperV│    │
        │  ┌──┐┌──┐  │ │  ┌──┐     │ │ ┌──┐ │    │
        │  │VM││VM│  │ │  │VM│     │ │ │VM│ │    │
        │  └──┘└──┘  │ │  └──┘     │ │ └──┘ │    │
        └────────────┘ └───────────┘ └──────┘    │
                                                 │
                    ┌────────────────────────────┘
                    │  WireGuard Tunnel (UDP)
                    ▼
        ┌──────────────────────┐
        │  Other Datacenter(s) │
        │  (Minicloud peers)   │
        └──────────────────────┘
```

## Core Concepts

### Datacenter
Each Minicloud instance manages exactly one datacenter — a set of hosts under the same NAT network. Identified by a configurable 2-letter code (e.g., `dc`, `ny`, `sf`).

### Host (Virtual Rack)
A physical machine registered by IP + SSH port. Each host is auto-assigned a unique 2-letter rack name (`aa` through `zz`, giving 676 slots). Hosts are the compute substrate where VMs run.

### VM (Node)
A virtual machine provisioned on a host. Named automatically: `<datacenter_code><rack_name><sequence:02d>` (e.g., `dcaa01`, `dcab03`). Each VM gets a static IP from the managed pool, bridged networking, and cloud-init configuration.

### Cluster
A Kubernetes cluster built from VMs using k3s. Consists of control plane nodes and worker nodes distributed across hosts for availability.

## Project Structure

```
minicloud/
├── docker/                          # Dockerfile, docker-compose.yml
├── backend/
│   ├── pyproject.toml               # Python deps, pytest config
│   └── app/
│       ├── main.py                  # FastAPI app, lifespan, static serving
│       ├── config.py                # pydantic-settings (MC_ prefix)
│       ├── database.py              # Async SQLAlchemy engine + session
│       ├── models/                  # ORM models
│       ├── schemas/                 # Pydantic request/response schemas
│       ├── api/                     # FastAPI routers
│       ├── services/                # Business logic layer
│       ├── drivers/                 # Hypervisor driver implementations
│       ├── ssh/client.py            # asyncssh wrapper
│       └── templates/               # Jinja2 templates (cloud-init, WG)
├── frontend/
│   └── src/
│       ├── api/                     # Axios client + typed API modules
│       ├── types/index.ts           # TypeScript interfaces
│       ├── pages/                   # Page components
│       ├── components/              # Feature-grouped UI components
│       └── hooks/useApi.ts          # TanStack Query wrappers
└── tests/backend/                   # pytest-asyncio tests
```

## Backend Architecture

### Layered Design

```
HTTP Request
    │
    ▼
┌───────────┐     ┌─────────────┐     ┌───────────────┐     ┌──────────┐
│  Router   │────▶│  Service    │────▶│    Driver     │────▶│ SSH/Host │
│ (api/*.py)│     │(services/*) │     │(drivers/*.py) │     │          │
└───────────┘     └──────┬──────┘     └───────────────┘     └──────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │   Database    │
                 │  (SQLAlchemy) │
                 └───────────────┘
```

- **Routers** (`api/`): HTTP endpoint definitions, request validation, dependency injection of `AsyncSession`
- **Services** (`services/`): Business logic, instantiated per-request with a DB session
- **Drivers** (`drivers/`): Hypervisor abstraction — each OS has its own driver implementation
- **SSH Client** (`ssh/client.py`): asyncssh wrapper providing `run`, `run_safe`, `run_multi`, `upload`, `download`

### Database

SQLite via aiosqlite for simplicity and zero-config deployment. The async engine is created at startup, tables auto-created via `init_db()` in the FastAPI lifespan.

**Models:**

| Model | Table | Purpose |
|-------|-------|---------|
| Host | `hosts` | Physical machines with hardware/network info |
| VM | `vms` | Virtual machines with size, IP, state |
| IPAllocation | `ip_allocations` | IP address pool tracking |
| SSHKey | `ssh_keys` | SSH key pairs for VM access |
| Cluster | `clusters` | Kubernetes cluster metadata + kubeconfig |
| ClusterNode | `cluster_nodes` | Cluster membership (VM + role) |

### Key Design Decisions

1. **Async everywhere**: FastAPI + SQLAlchemy async + asyncssh for non-blocking SSH operations
2. **Driver pattern**: Abstract `HypervisorDriver` base class with `get_driver(os_type, ssh_client)` factory — enables supporting KVM, Multipass, and Hyper-V with the same service layer
3. **Cloud-init over SSH provisioning**: VMs get their config (hostname, SSH keys, network) via cloud-init ISO/config rather than post-boot SSH scripting — more reliable and idempotent
4. **Background tasks for long ops**: Cluster creation/deletion run in FastAPI `BackgroundTasks` with status polling from the frontend
5. **Static file serving**: In production, the FastAPI app serves the built React SPA directly — single container, single port

## Frontend Architecture

### State Management

- **Server state**: TanStack Query with query keys like `['hosts']`, `['vms']`, `['clusters']`
- **No client-side state management library** — Ant Design forms + query cache handle most needs
- **Optimistic updates**: Mutations invalidate relevant queries on success

### Page Structure

| Page | Purpose |
|------|---------|
| Dashboard | Overview of hosts, VMs, clusters |
| Hosts | Register, detect, manage physical machines |
| VMs | Provision, start/stop, monitor VMs |
| Clusters | Create/manage k3s clusters, add/remove nodes |
| SSH Keys | Generate or import SSH key pairs |
| IP Management | View allocations, reserve IPs |
| WireGuard | Manage inter-datacenter tunnels |

### API Layer

Each resource has a typed API module (e.g., `api/hosts.ts`) exporting an object with methods that call the backend. These are consumed by TanStack Query hooks in `hooks/useApi.ts`.
