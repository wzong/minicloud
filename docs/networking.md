# Networking Design

## Overview

Minicloud manages two networking layers:

1. **Local networking** — Bridged VM networking within a datacenter (same NAT/LAN)
2. **Inter-datacenter networking** — WireGuard tunnels routing real LAN subnets across NAT boundaries

## Local VM Networking

### Bridged Network Architecture

```
                    Internet
                       │
                   ┌───┴────┐
                   │ Router │  (NAT gateway, e.g. 192.168.1.1)
                   └───┬────┘
                       │
          ─────────────┼──────────────── LAN (192.168.1.0/24)
              │        │       │
          ┌───┴───┐ ┌──┴──┐ ┌──┴──┐
          │Host A │ │HostB│ │HostC│
          │ br0   │ │ br0 │ │ br0 │
          │┌─┐┌─┐ │ │┌─┐  │ │┌─┐  │
          ││V││V│ │ ││V│  │ ││V│  │
          │└─┘└─┘ │ │└─┘  │ │└─┘  │
          └───────┘ └─────┘ └─────┘
```

Each host creates a bridge interface (`br0`) that connects VM virtual NICs to the physical LAN. VMs appear as first-class devices on the network with their own IP addresses.

### Static IP Allocation

- The admin configures an IP range via `MC_IP_RANGE_START` and `MC_IP_RANGE_END`
- The IP manager tracks allocations in the `ip_allocations` table
- Each VM gets the next available IP from the pool
- IPs can be manually reserved (e.g., for external services)
- On VM deletion, the IP is released back to the pool

### Cloud-Init Network Configuration

VMs receive their network config at boot via cloud-init (netplan format):

```yaml
network:
  version: 2
  ethernets:
    enp1s0:
      addresses:
        - 192.168.1.50/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
      routes:
        - to: 192.168.2.0/24
          via: 192.168.1.10
```

The gateway, subnet mask, and DNS are auto-detected from the host during registration. When WireGuard peers are configured, Minicloud also injects static routes for remote-datacenter subnets into the cloud-init network config. In the example above, `192.168.1.10` is the Minicloud container's LAN IP, and traffic destined for DC-B's `192.168.2.0/24` is routed through it into the WireGuard tunnel.

### Bridge Setup by OS

| OS | Hypervisor | Bridge Method |
|----|-----------|---------------|
| Linux | KVM | `brctl` or `ip link` to create `br0`, attach physical NIC |
| macOS | Multipass | Multipass handles bridged networking via `--network` flag |
| Windows | Hyper-V | Virtual switch in "External" mode bridges to physical NIC |

### Bridge Configuration Check

KVM VM creation passes `--network bridge={host.bridge_interface}` directly to
`virt-install`. If the named bridge is missing or misnamed on the host, VM
boot fails with confusing cloud-init / libvirt errors. To surface readiness
before the operator attempts to provision a VM, the Hosts dashboard exposes a
**Check Bridge** action per host that mirrors the existing **Check Hypervisor**
action.

**Persisted state:** `hosts.bridge_configured` (boolean) records the most
recent check result. The Hosts table and host detail drawer both render it as
a `Configured` / `Not configured` tag. The drawer auto-runs the check on open
when the host is not already marked configured.

**API:** `POST /api/hosts/{id}/check-bridge` → `BridgeCheck`:

```json
{
  "configured": true,
  "bridge_name": "br0",
  "output": "2: br0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...",
  "setup_commands": null
}
```

On failure, `setup_commands` contains an OS-appropriate remediation script
that the drawer renders in a copyable `Alert`.

**Detection per OS:**

| OS | Command | Success signal | Default when `host.bridge_interface` unset |
|----|---------|----------------|---------------------------------------------|
| Linux | `ip link show <bridge>` | Exit code 0 | First bridge reported by `ip -o link show type bridge` |
| macOS | `ifconfig <bridge>` | Exit code 0 | `bridge100` (auto-created by Multipass) |
| Windows | `Get-VMSwitch -Name <bridge>` | Non-empty output | First switch from `Get-VMSwitch -SwitchType External` |

The check is independent of **Check Hypervisor** — the two actions target
different host requirements and each persists its own boolean on the `Host`
model.

## IP Address Scheme

### Within a Datacenter

```
192.168.1.0/24 (example LAN — DC-A)
├── .1        — Router/gateway
├── .2-.19    — Reserved for hosts
├── .20-.249  — VM allocation pool (configurable)
├── .250-.254 — Reserved
└── .255      — Broadcast

192.168.2.0/24 (example LAN — DC-B)
├── .1        — Router/gateway
├── .2-.19    — Reserved for hosts
├── .20-.249  — VM allocation pool (configurable)
├── .250-.254 — Reserved
└── .255      — Broadcast
```

Each datacenter uses its own unique LAN subnet. VMs keep their real LAN IPs — there is no overlay network.

### WireGuard Tunnel Endpoints

WireGuard interface IPs are used **only** for the tunnel endpoints themselves (the Minicloud containers), not for VMs:

```
10.10.1.1/32  — DC-A Minicloud container (wg0)
10.10.2.1/32  — DC-B Minicloud container (wg0)
```

These addresses identify the WireGuard peers. All VM traffic uses real LAN IPs and is routed through the tunnel without NAT.

## Inter-Datacenter Networking (WireGuard)

### Architecture

```
  Datacenter A (NAT)                Datacenter B (NAT)
  ┌────────────────────┐            ┌────────────────────┐
  │ ┌────────────────┐ │            │ ┌────────────────┐ │
  │ │   Minicloud    │ │            │ │   Minicloud    │ │
  │ │   Container    │ │            │ │   Container    │ │
  │ │                │ │            │ │                │ │
  │ │ wg0: 10.10.1.1 ◄── UDP 51820 ──▶ wg0: 10.10.2.1  │ │
  │ │   /32          │ │   tunnel   │ │   /32          │ │
  │ └───────┬────────┘ │            │ └───────┬────────┘ │
  │         │ routes   │            │         │ routes   │
  │    Hosts & VMs     │            │    Hosts & VMs     │
  │  192.168.1.0/24    │            │  192.168.2.0/24    │
  └────────────────────┘            └────────────────────┘
```

### How It Works

1. Each Minicloud container runs a WireGuard interface (`wg0`)
2. On startup, a WireGuard key pair is generated (or loaded from persistent storage)
3. Admins exchange public keys + endpoints between datacenters via the UI
4. WireGuard config is rendered from a Jinja2 template and applied via `wg-quick`
5. The container acts as a router: it forwards traffic between the WireGuard tunnel and the local LAN
6. VMs in DC-A can reach VMs in DC-B using their real LAN IPs — no overlay, no NAT

### Routing Example

How `192.168.1.50` (VM in DC-A) reaches `192.168.2.50` (VM in DC-B):

```
  DC-A                                                  DC-B
  ┌─────────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │  1. VM 192.168.1.50 sends packet to 192.168.2.50                    │
  │     └─▶ Host's route: 192.168.2.0/24 → Minicloud container          │
  │                                                                     │
  │  2. Minicloud container (DC-A) receives the packet                  │
  │     └─▶ Kernel route: 192.168.2.0/24 via wg0                        │
  │     └─▶ WireGuard encrypts and sends to DC-B endpoint               │
  │                                                                     │
  │  3. Minicloud container (DC-B) receives on wg0                      │
  │     └─▶ WireGuard decrypts, packet destination is 192.168.2.50      │
  │     └─▶ Forwards to local LAN via eth0                              │
  │                                                                     │
  │  4. VM 192.168.2.50 receives the packet                             │
  │                                                                     │
  └─────────────────────────────────────────────────────────────────────┘
```

The return path works the same way in reverse — DC-B hosts route `192.168.1.0/24` to their local Minicloud container.

### Route Setup

For cross-datacenter routing to work, every host (and its VMs) must know to send remote-subnet traffic to the Minicloud container. This requires a static route on each host:

**On DC-A hosts** (to reach DC-B's `192.168.2.0/24`):
```bash
ip route add 192.168.2.0/24 via <minicloud-container-ip>
```

**On DC-B hosts** (to reach DC-A's `192.168.1.0/24`):
```bash
ip route add 192.168.1.0/24 via <minicloud-container-ip>
```

Where `<minicloud-container-ip>` is the Minicloud container's IP on the local LAN (e.g., the Docker host IP or a macvlan address).

VMs bridged onto the LAN inherit the host's routing, or can have routes added via cloud-init. Alternatively, the datacenter router can be configured with the static routes so all devices route automatically.

### Shared WireGuard Gateway

Multiple Minicloud instances on the same LAN can share a single WireGuard gateway. This is common when each NAT network has multiple datacenters — only one instance needs to run WireGuard.

```
  LAN (192.168.1.0/24)
  ─────────────────────────────────────────
      │              │              │
  ┌───┴────────┐ ┌───┴────────┐    │
  │ Minicloud  │ │ Minicloud  │    │
  │ Instance A │ │ Instance B │    │   To remote DCs
  │ (DC-A)     │ │ (DC-C)     │    │   via WireGuard
  │            │ │            │ ┌──┴──────────┐
  │ No WG      │ │ No WG      │ │ Minicloud    │
  └────────────┘ └────────────┘ │ Instance GW  │
                                │ wg0 active   │
                                │ 192.168.1.10 │
                                └──────────────┘
```

Set `MC_WG_GATEWAY_IP` on each instance to the LAN IP of the gateway container (e.g., `192.168.1.10`). When a VM is created, Minicloud reads the gateway's WireGuard peer list and injects static routes for each peer's `allowed_ips` into the VM's cloud-init network config, using `MC_WG_GATEWAY_IP` as the next-hop.

- The gateway instance does **not** need `MC_WG_GATEWAY_IP` set — it uses its own WireGuard interface for routing
- Instances without WireGuard still need the peers JSON file available (or a copy of it) so they can read the remote subnets
- Routes are only injected at VM creation time; existing VMs are not updated automatically

### Peer Configuration

Peers are stored in a JSON file (persisted via Docker volume):

```json
{
  "peers": [
    {
      "name": "datacenter-b",
      "public_key": "abc123...",
      "endpoint": "203.0.113.1:51820",
      "allowed_ips": "192.168.2.0/24"
    }
  ]
}
```

The `allowed_ips` field lists the **real LAN subnets** behind the peer, not overlay addresses. WireGuard uses this both for routing (packets to `192.168.2.0/24` go to this peer) and as a cryptographic access control (this peer is only allowed to send packets from `192.168.2.0/24`).

### WireGuard Config Template

```ini
[Interface]
Address = {{ wg_address }}
ListenPort = {{ wg_port }}
PrivateKey = {{ private_key }}
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

{% for peer in peers %}
[Peer]
# {{ peer.name }}
PublicKey = {{ peer.public_key }}
Endpoint = {{ peer.endpoint }}
AllowedIPs = {{ peer.allowed_ips }}
PersistentKeepalive = 25
{% endfor %}
```

`AllowedIPs` for each peer contains the remote datacenter's real LAN subnet (e.g., `192.168.2.0/24`), telling WireGuard to route that subnet through the tunnel.

### Constraints

- **LAN subnets must not overlap across datacenters.** Each datacenter must use a distinct subnet (e.g., `192.168.1.0/24` and `192.168.2.0/24`). Overlapping subnets would create ambiguous routes and break cross-datacenter connectivity.
- **IP forwarding must be enabled** on the Minicloud container (`sysctl net.ipv4.ip_forward=1`).
- **The Minicloud container must be reachable** on the LAN from hosts and VMs so it can act as a next-hop router.

### Container Requirements

The Docker container needs:
- `NET_ADMIN` capability (for WireGuard and iptables)
- UDP port 51820 exposed
- IP forwarding enabled (`sysctl net.ipv4.ip_forward=1`)
- `wireguard-tools` installed
