# Implementation Plan

Phased build plan for Minicloud, ordered by dependency and priority.

---

## Phase 1: Foundation

**Goal:** Runnable backend with database, config, and host management.

### 1.1 Project Scaffolding
- [x] Initialize repo structure (`backend/`, `frontend/`, `docker/`, `tests/`)
- [x] Set up `pyproject.toml` with dependencies (FastAPI, SQLAlchemy, aiosqlite, asyncssh, Jinja2, pydantic-settings)
- [x] Set up frontend with Vite + React + TypeScript + Ant Design

### 1.2 Backend Core
- [x] `config.py` — pydantic-settings with `MC_` env prefix
- [x] `database.py` — async SQLAlchemy engine, `Base`, `get_db` dependency, `init_db`
- [x] `main.py` — FastAPI app with lifespan (calls `init_db`), CORS, router includes

### 1.3 Host Management
- [x] `models/host.py` — Host model (ip_address, ssh_port, ssh_user, rack_name, os_type, status, hardware/network fields)
- [x] `schemas/host.py` — Pydantic create/response schemas
- [x] `services/rack_namer.py` — Sequential `aa`–`zz` rack name assignment
- [x] `services/host_service.py` — Register host, assign rack name, detect hardware/network via SSH
- [x] `ssh/client.py` — asyncssh wrapper (run, run_safe, run_multi, upload, download)
- [x] `api/hosts.py` — CRUD + detect + check-hypervisor endpoints
- [x] Tests: host registration, rack naming, detection mocking

### 1.4 SSH Key Management
- [x] `models/ssh_key.py` — SSHKey model
- [x] `schemas/ssh_key.py` — Pydantic schemas
- [x] `services/ssh_key_service.py` — Generate ed25519 keys, import existing, compute fingerprint
- [x] `api/ssh_keys.py` — Generate, import, list, delete endpoints
- [x] Tests: key generation, import

---

## Phase 2: VM Provisioning

**Goal:** Provision VMs with static IPs and cloud-init on any supported host OS.

### 2.1 IP Management
- [x] `models/ip_allocation.py` — IPAllocation model
- [x] `schemas/ip.py` — Pydantic schemas
- [x] `services/ip_manager.py` — Allocate next available IP from configured range, reserve, release
- [x] `api/ip.py` — Allocations, available, reserve/release endpoints
- [x] Tests: allocation, range exhaustion, reservation

### 2.2 Hypervisor Drivers
- [x] `drivers/base.py` — `HypervisorDriver` ABC with methods: `create_vm`, `delete_vm`, `start_vm`, `stop_vm`, `get_vm_status`, `check_installed`
- [x] `drivers/kvm.py` — KVMDriver using virsh/virt-install, cloud-localds for cloud-init ISO
- [x] `drivers/multipass.py` — MultipassDriver for macOS hosts
- [x] `drivers/hyperv.py` — HyperVDriver using PowerShell over SSH
- [x] `drivers/__init__.py` — `get_driver(os_type, ssh_client)` factory
- [x] Tests: driver factory, mock SSH commands

### 2.3 Cloud-Init Templates
- [x] `templates/cloud-init/user-data.j2` — Hostname, SSH authorized keys, package updates
- [x] `templates/cloud-init/meta-data.j2` — Instance ID, local hostname
- [x] `templates/cloud-init/network-config.j2` — Static IP, gateway, DNS (netplan format)

### 2.4 VM Service & API
- [x] `models/vm.py` — VM model (name, host_id FK, ip_address, status, size, os_image, ssh_key_id FK, rack_sequence)
- [x] `schemas/vm.py` — Pydantic schemas
- [x] `services/vm_service.py` — Create VM (auto-name, allocate IP, render cloud-init, call driver), delete, start, stop, refresh status
- [x] `api/vms.py` — CRUD + lifecycle + by-rack grouping
- [x] Tests: VM creation flow, naming, IP allocation integration

---

## Phase 3: Kubernetes Clusters

**Goal:** Bootstrap k3s clusters across VMs using k3sup.

### 3.1 Cluster Models
- [x] `models/cluster.py` — Cluster model (name, status, k3s_version, kubeconfig)
- [x] `models/cluster_node.py` — ClusterNode model (cluster_id FK, vm_id FK, role, status)
- [x] `schemas/cluster.py` — Pydantic schemas including preview response

### 3.2 Node Distribution
- [x] `services/cluster_service.py` — Round-robin node distribution across hosts sorted by available RAM
- [x] Preview endpoint returns planned distribution without creating anything
- [x] Control plane nodes placed first for HA spread across hosts

### 3.3 Cluster Lifecycle
- [x] Create: provision VMs, install k3s via k3sup (first CP gets `--cluster-init`, others join)
- [x] Background task for creation with status polling
- [x] Retrieve kubeconfig from first control plane node
- [x] Add/remove individual nodes post-creation
- [x] Delete: drain nodes, destroy VMs, clean up DB records (background task)
- [x] `api/clusters.py` — Full cluster CRUD + node management + kubeconfig + status polling
- [x] Tests: cluster creation mocking, node distribution logic

---

## Phase 4: Networking (WireGuard)

**Goal:** Connect datacenters across NAT networks via WireGuard tunnels.

### 4.1 WireGuard Service
- [x] `services/wireguard_service.py` — Manage WG interface, peer config stored as JSON file
- [x] `templates/wg0.conf.j2` — Jinja2 template for WireGuard config
- [x] Generate/read key pair, add/remove peers, reload interface via `wg-quick`

### 4.2 WireGuard API
- [x] `api/wireguard.py` — Status, public-key, peers CRUD, reload
- [x] Tests: peer management, config rendering

---

## Phase 5: Frontend

**Goal:** React SPA with full management UI.

### 5.1 Core Setup
- [x] Vite + React + TypeScript project
- [x] Ant Design 5 theme and layout (sidebar navigation)
- [x] React Router 6 with route definitions
- [x] Axios client with base URL config
- [x] TanStack Query provider

### 5.2 API Layer
- [x] `api/client.ts` — Axios instance
- [x] `api/hosts.ts`, `api/vms.ts`, `api/clusters.ts`, etc. — Typed API modules
- [x] `types/index.ts` — TypeScript interfaces matching backend schemas
- [x] `hooks/useApi.ts` — TanStack Query wrappers

### 5.3 Pages & Components
- [x] Dashboard — Summary cards (host count, VM count, cluster count), quick actions
- [x] Hosts — Table with register form, detect button, status badges, rack name edit
- [x] VMs — Table with create modal (host/size/image/key selection), lifecycle buttons, rack grouping view
- [x] Clusters — Create wizard (counts, sizes, preview distribution), node list, kubeconfig download, status polling
- [x] SSH Keys — Table with generate/import modals
- [x] IP Management — Allocation table, available IPs, reserve/release
- [x] WireGuard — Status display, peer list, add/remove peer

---

## Phase 6: Docker & Deployment

**Goal:** Single-container deployment with all services.

### 6.1 Dockerfile
- [x] Multi-stage build: Node (build frontend) -> Python + WireGuard + k3sup
- [x] Install system dependencies: wireguard-tools, cloud-image-utils, openssh-client
- [x] Copy built frontend into static serving directory
- [x] Entrypoint: start WireGuard (if configured), run uvicorn

### 6.2 Docker Compose
- [x] `docker-compose.yml` with environment variables, volume mounts (DB, keys, WG config)
- [x] `NET_ADMIN` capability for WireGuard
- [x] Port mappings: 8080 (web), 51820/udp (WireGuard)

---

## Future Considerations

These are not planned for initial implementation but noted for potential future work:

- **Multi-user auth**: API authentication and role-based access
- **Cluster upgrades**: Rolling k3s version upgrades
- **Storage**: Persistent volume provisioning (local-path, NFS)
- **Monitoring**: Prometheus/Grafana stack deployment on clusters
- **Helm/app deployment**: Deploy applications onto managed clusters
- **Auto-scaling**: Automatic node addition based on cluster resource usage
- **Backup/restore**: Database and cluster state backup
