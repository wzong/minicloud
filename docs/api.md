# API Reference

All endpoints are prefixed with `/api`.

## Hosts

Manage physical machines that serve as hypervisor hosts.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/hosts` | List all hosts |
| `POST` | `/hosts` | Register a new host (ip_address, ssh_port, ssh_user) |
| `GET` | `/hosts/{id}` | Get host details |
| `DELETE` | `/hosts/{id}` | Remove a host |
| `POST` | `/hosts/{id}/detect` | Auto-detect hardware/network info via SSH |
| `POST` | `/hosts/{id}/check-hypervisor` | Check if hypervisor is installed, detect type |
| `PUT` | `/hosts/{id}/rack-name` | Override the auto-assigned rack name |

### Host Schema

```json
{
  "id": 1,
  "ip_address": "192.168.1.100",
  "ssh_port": 22,
  "ssh_user": "root",
  "rack_name": "aa",
  "os_type": "linux",           // linux | macos | windows
  "status": "online",           // online | offline | unknown
  "cpu_cores": 16,
  "ram_gb": 64,
  "disk_gb": 500,
  "gateway": "192.168.1.1",
  "subnet": "255.255.255.0",
  "dns": "8.8.8.8",
  "bridge": "br0",
  "hypervisor_installed": true,
  "hypervisor_type": "kvm"
}
```

## VMs

Provision and manage virtual machines on registered hosts.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/vms` | List all VMs |
| `POST` | `/vms` | Create a new VM |
| `GET` | `/vms/{id}` | Get VM details |
| `DELETE` | `/vms/{id}` | Destroy a VM |
| `POST` | `/vms/{id}/start` | Start a stopped VM |
| `POST` | `/vms/{id}/stop` | Stop a running VM |
| `POST` | `/vms/{id}/refresh` | Refresh VM status from host |
| `GET` | `/vms/by-rack` | List VMs grouped by rack (host) |

### VM Create Request

```json
{
  "host_id": 1,
  "cpu_cores": 2,
  "ram_gb": 4,
  "disk_gb": 20,
  "os_image": "ubuntu-22.04",
  "ssh_key_id": 1
}
```

### VM Schema

```json
{
  "id": 1,
  "name": "dcaa01",
  "host_id": 1,
  "ip_address": "192.168.1.50",
  "status": "running",         // running | stopped | creating | error | unknown
  "cpu_cores": 2,
  "ram_gb": 4,
  "disk_gb": 20,
  "os_image": "ubuntu-22.04",
  "ssh_key_id": 1,
  "rack_sequence": 1
}
```

## SSH Keys

Manage SSH key pairs used for VM access.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ssh-keys` | List all SSH keys |
| `POST` | `/ssh-keys/generate` | Generate a new key pair |
| `POST` | `/ssh-keys/import` | Import an existing public key |
| `DELETE` | `/ssh-keys/{id}` | Delete a key pair |

### SSH Key Schema

```json
{
  "id": 1,
  "name": "default",
  "public_key": "ssh-ed25519 AAAA...",
  "private_key_path": "/app/data/keys/default",
  "fingerprint": "SHA256:..."
}
```

## IP Management

Manage the IP address allocation pool.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ip/allocations` | List all IP allocations |
| `GET` | `/ip/available` | List available IPs in the range |
| `POST` | `/ip/reserve` | Reserve an IP (with optional notes) |
| `DELETE` | `/ip/reserve` | Release a reserved IP |

### IP Allocation Schema

```json
{
  "ip_address": "192.168.1.50",
  "vm_id": 1,
  "is_reserved": false,
  "notes": ""
}
```

## Clusters

Create and manage Kubernetes (k3s) clusters.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/clusters` | List all clusters |
| `POST` | `/clusters` | Create a new cluster (async, returns immediately) |
| `GET` | `/clusters/{id}` | Get cluster details |
| `DELETE` | `/clusters/{id}` | Destroy cluster and its VMs (async) |
| `POST` | `/clusters/preview` | Preview node distribution without creating |
| `GET` | `/clusters/{id}/nodes` | List nodes in a cluster |
| `POST` | `/clusters/{id}/nodes` | Add node(s) to a cluster |
| `DELETE` | `/clusters/{id}/nodes` | Remove specific node(s) |
| `GET` | `/clusters/{id}/kubeconfig` | Download kubeconfig |
| `GET` | `/clusters/{id}/status` | Poll cluster creation/deletion status |

### Cluster Create Request

```json
{
  "name": "prod",
  "control_plane_count": 3,
  "worker_count": 5,
  "cp_cpu": 2,
  "cp_ram_gb": 4,
  "cp_disk_gb": 20,
  "worker_cpu": 4,
  "worker_ram_gb": 8,
  "worker_disk_gb": 40,
  "ssh_key_id": 1,
  "k3s_version": "v1.28.4+k3s1",
  "os_image": "ubuntu-22.04"
}
```

### Cluster Schema

```json
{
  "id": 1,
  "name": "prod",
  "status": "ready",          // creating | ready | error | deleting
  "k3s_version": "v1.28.4+k3s1",
  "control_plane_count": 3,
  "worker_count": 5,
  "kubeconfig": "..."
}
```

## WireGuard

Manage inter-datacenter WireGuard tunnels.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/wireguard/status` | Get WireGuard interface status |
| `GET` | `/wireguard/public-key` | Get this instance's WG public key |
| `GET` | `/wireguard/peers` | List configured peers |
| `POST` | `/wireguard/peers` | Add a peer (another datacenter) |
| `DELETE` | `/wireguard/peers` | Remove a peer |
| `POST` | `/wireguard/reload` | Reload WireGuard configuration |

### Peer Schema

```json
{
  "name": "datacenter-ny",
  "public_key": "abc123...",
  "endpoint": "203.0.113.1:51820",
  "allowed_ips": "10.10.0.0/24"
}
```
