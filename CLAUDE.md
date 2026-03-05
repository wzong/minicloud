# Minicloud

Self-hosted AWS EKS for bare metal — a Docker-containerized web app that manages on-premises datacenters, provisions VMs on physical hosts via SSH, connects datacenters across NAT networks via WireGuard, and bootstraps Kubernetes clusters using k3s/k3sup.

## Tech Stack

- **Backend**: Python 3.12 / FastAPI / SQLAlchemy 2.0 (async) / aiosqlite / asyncssh / Jinja2
- **Frontend**: React 18 / TypeScript / Ant Design 5 / React Router 6 / TanStack Query / Vite
- **Infra**: Docker (multi-stage build), WireGuard, k3s + k3sup, SQLite

## Project Structure

```
minicloud/
├── docker/                          # Dockerfile (multi-stage Node→Python+WG+k3sup), docker-compose.yml
├── backend/
│   ├── pyproject.toml               # Python deps, pytest config (asyncio_mode=auto)
│   └── app/
│       ├── main.py                  # FastAPI app, lifespan (init_db), static file serving
│       ├── config.py                # pydantic-settings, MC_ env prefix, settings singleton
│       ├── database.py              # Async engine + session, Base, get_db dependency, init_db
│       ├── models/                  # SQLAlchemy 2.0 Mapped models: Host, VM, IPAllocation, SSHKey, Cluster, ClusterNode
│       ├── schemas/                 # Pydantic request/response: host, vm, ssh_key, cluster, ip, wireguard
│       ├── api/                     # FastAPI routers: hosts, vms, ssh_keys, clusters, ip, wireguard
│       ├── services/                # Business logic: host_service, vm_service, ip_manager, ssh_key_service, cluster_service, wireguard_service, rack_namer
│       ├── drivers/                 # HypervisorDriver ABC → KVMDriver, MultipassDriver, HyperVDriver
│       ├── ssh/client.py            # asyncssh wrapper: run, run_safe, run_multi, upload, download
│       └── templates/               # Jinja2: cloud-init (user-data, meta-data, network-config), wg0.conf
├── frontend/
│   └── src/
│       ├── api/                     # Axios client + typed API modules per resource
│       ├── types/index.ts           # TypeScript interfaces matching backend schemas
│       ├── pages/                   # Dashboard, Hosts, VMs, Clusters, SSHKeys, IPManagement, WireGuard
│       ├── components/              # hosts/, vms/, clusters/ subdirectories
│       └── hooks/useApi.ts          # TanStack Query wrappers
└── tests/backend/                   # pytest-asyncio + httpx AsyncClient, in-memory SQLite
```

## Key Conventions

- **Config**: All env vars use `MC_` prefix (e.g. `MC_DATACENTER_CODE`, `MC_IP_RANGE_START`)
- **DB models**: SQLAlchemy 2.0 `Mapped[]` style with `mapped_column()`, import `Base` from `app.database`
- **API pattern**: Each `api/*.py` creates a sub-router, includes it into the main `router` from `app.api`
- **Services**: Business logic in `services/`, instantiated per-request with `db: AsyncSession`
- **Drivers**: `get_driver(os_type, ssh_client)` factory returns KVM/Multipass/HyperV driver
- **VM naming**: `<dc_code><rack_name><sequence:02d>` (e.g. `dcaa01`)
- **Rack naming**: Sequential `aa` through `zz` (676 slots), auto-assigned on host registration
- **Frontend state**: TanStack Query for server state, query keys like `['hosts']`, `['vms']`, `['clusters']`
- **Frontend API**: Each `api/*.ts` module exports an object with typed methods (e.g. `hostsApi.list()`)

## Database Models

| Model | Table | Key Fields |
|-------|-------|-----------|
| Host | hosts | ip_address(unique), ssh_port, ssh_user, rack_name(unique 2-letter), os_type(enum), status(enum), cpu/ram/disk, gateway, subnet, dns, bridge, hypervisor_installed/type |
| VM | vms | name(unique), host_id(FK), ip_address(unique), status(enum), cpu/ram/disk, os_image, ssh_key_id(FK), rack_sequence |
| IPAllocation | ip_allocations | ip_address(unique+indexed), vm_id(FK nullable), is_reserved, notes |
| SSHKey | ssh_keys | name(unique), public_key, private_key_path, fingerprint |
| Cluster | clusters | name(unique), status(enum), k3s_version, kubeconfig(text) |
| ClusterNode | cluster_nodes | cluster_id(FK), vm_id(FK unique), role(enum), status(enum) |

## API Routes

- `GET/POST /api/hosts`, `GET/DELETE /api/hosts/{id}`, `POST /api/hosts/{id}/detect`, `POST /api/hosts/{id}/check-hypervisor`, `PUT /api/hosts/{id}/rack-name`
- `GET/POST /api/vms`, `GET/DELETE /api/vms/{id}`, `POST /api/vms/{id}/start|stop|refresh`, `GET /api/vms/by-rack`
- `GET /api/ssh-keys`, `POST /api/ssh-keys/generate|import`, `DELETE /api/ssh-keys/{id}`
- `GET /api/ip/allocations|available`, `POST/DELETE /api/ip/reserve`
- `GET/POST /api/clusters`, `GET/DELETE /api/clusters/{id}`, `POST /api/clusters/preview`, `GET/POST/DELETE /api/clusters/{id}/nodes`, `GET /api/clusters/{id}/kubeconfig|status`
- `GET /api/wireguard/status|public-key|peers`, `POST/DELETE /api/wireguard/peers`, `POST /api/wireguard/reload`

## Architecture Decisions

- **Hypervisor drivers**: Abstract base class with OS-specific implementations — KVM (Linux, virsh/virt-install), Multipass (macOS), Hyper-V (Windows, PowerShell over SSH)
- **Cloud-init**: Jinja2 templates for user-data (SSH keys, hostname), meta-data, network-config (static IP). ISO created via `cloud-localds` (KVM) or passed directly (Multipass)
- **WireGuard**: Container acts as gateway, peers stored in JSON file, config rendered from Jinja2 template, managed via `wg-quick`
- **k3sup**: Runs from inside the container, installs k3s on VMs via SSH. First CP node gets `--cluster`, additional CPs/workers use `k3sup join`
- **Background tasks**: Cluster creation/deletion use FastAPI `BackgroundTasks` with status polling
- **Node distribution**: Round-robin across hosts sorted by available RAM (CP nodes first for HA spread)

## Running

```bash
# Backend (dev)
cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --port 8080

# Frontend (dev)
cd frontend && npm run dev

# Tests
cd .. && source .venv/bin/activate && python -m pytest tests/backend/ -v

# Docker
cd docker && docker compose up --build
```
