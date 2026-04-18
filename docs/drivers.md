# Hypervisor Drivers

## Overview

Minicloud uses a driver abstraction to support multiple hypervisors across different host operating systems. All hypervisor operations are performed via SSH from the Minicloud container to the host machine.

```
HypervisorDriver (ABC)
├── KVMDriver      — Linux hosts (libvirt/virsh/virt-install)
├── MultipassDriver — macOS hosts (multipass CLI)
└── HyperVDriver   — Windows hosts (PowerShell over SSH)
```

## Driver Interface

```python
class HypervisorDriver(ABC):
    @abstractmethod
    async def check_installed(self) -> bool:
        """Check if the hypervisor is installed and available."""

    @abstractmethod
    async def create_vm(self, name, cpu, ram_gb, disk_gb, os_image,
                        ip_address, gateway, subnet, dns,
                        ssh_public_key, bridge) -> None:
        """Create and start a new VM with the given specs."""

    @abstractmethod
    async def delete_vm(self, name) -> None:
        """Stop and remove a VM and its storage."""

    @abstractmethod
    async def start_vm(self, name) -> None:
        """Start a stopped VM."""

    @abstractmethod
    async def stop_vm(self, name) -> None:
        """Stop a running VM."""

    @abstractmethod
    async def get_vm_status(self, name) -> str:
        """Get VM power state: running, stopped, or unknown."""
```

## Driver Factory

```python
def get_driver(os_type: str, ssh_client: SSHClient) -> HypervisorDriver:
    match os_type:
        case "linux":   return KVMDriver(ssh_client)
        case "macos":   return MultipassDriver(ssh_client)
        case "windows": return HyperVDriver(ssh_client)
        case _:         raise ValueError(f"Unsupported OS: {os_type}")
```

## KVM Driver (Linux)

### Prerequisites on Host
- `qemu-kvm`, `libvirt-daemon-system`, `virtinst` (virt-install)
- `cloud-image-utils` (for `cloud-localds` to create cloud-init ISO)
- A bridge interface (`br0`) connected to the physical NIC

### VM Creation Flow

```
1. Download OS cloud image (if not cached)
   └─ e.g., ubuntu-22.04-server-cloudimg-amd64.img

2. Create VM disk (qcow2, backing file = cloud image)
   └─ qemu-img create -f qcow2 -b <base> -F qcow2 <vm>.qcow2 <disk_gb>G

3. Render cloud-init templates
   ├─ user-data: hostname, SSH key, packages
   ├─ meta-data: instance-id
   └─ network-config: static IP, gateway, DNS

4. Create cloud-init ISO
   └─ cloud-localds --network-config=network.cfg seed.iso user-data meta-data

5. Create and start VM via virt-install
   └─ virt-install --name <name> --vcpus <cpu> --memory <ram_mb>
      --disk <vm>.qcow2 --disk seed.iso,device=cdrom
      --network bridge=br0 --os-variant ubuntu22.04
      --noautoconsole --import

6. Wait for VM to become reachable via SSH
```

### VM Deletion
```bash
virsh destroy <name>          # Force stop
virsh undefine <name> --remove-all-storage  # Remove definition + disks
```

### VM Lifecycle
```bash
virsh start <name>            # Start
virsh shutdown <name>         # Graceful stop
virsh domstate <name>         # Status check
```

## Multipass Driver (macOS)

### Prerequisites on Host
- Multipass installed (`brew install multipass`)

### VM Creation Flow

```
1. Launch VM with cloud-init
   └─ multipass launch <image> --name <name>
      --cpus <cpu> --memory <ram>G --disk <disk>G
      --cloud-init <user-data-file>
      --network name=en0,mode=manual

2. Configure static IP inside the VM
   └─ SSH in and apply netplan config

3. Wait for VM to become reachable at static IP
```

### Key Differences from KVM
- Multipass handles image downloads internally
- Bridged networking uses `--network` flag with the host's physical interface
- Cloud-init user-data is passed directly (no ISO creation needed)
- Network config may require post-boot application via SSH

### VM Lifecycle
```bash
multipass start <name>
multipass stop <name>
multipass delete <name> --purge
multipass info <name>          # Status check
```

## Hyper-V Driver (Windows)

### Prerequisites on Host
- Hyper-V enabled (Windows Pro/Server)
- OpenSSH server running on Windows host
- External virtual switch configured (run once in an elevated PowerShell):

```powershell
New-VMSwitch -Name "External" -NetAdapterName "Ethernet" -AllowManagementOS $true
```

> Note: `-AllowManagementOS` requires a PowerShell boolean (`$true`), not a string (`"true"`).

### VM Creation Flow

```
1. Download OS cloud image (if not cached)

2. Create VM disk (VHDX converted from qcow2, or download VHDX directly)

3. Create cloud-init ISO
   └─ Use mkisofs/genisoimage via WSL or a Windows equivalent

4. Create VM via PowerShell
   └─ New-VM -Name <name> -MemoryStartupBytes <ram>
      -VHDPath <disk> -SwitchName "External"
   └─ Set-VMProcessor -VMName <name> -Count <cpu>
   └─ Add-VMDvdDrive -VMName <name> -Path <seed.iso>

5. Start VM
   └─ Start-VM -Name <name>

6. Wait for VM to become reachable via SSH
```

### VM Lifecycle
```powershell
Start-VM -Name <name>
Stop-VM -Name <name>
Remove-VM -Name <name> -Force
(Get-VM -Name <name>).State    # Status check
```

### Key Differences
- All commands run via PowerShell over SSH
- Disk format is VHDX (may need conversion from qcow2)
- Cloud-init ISO creation may use WSL or Windows tools
- Virtual switch must be pre-configured in "External" mode

## Error Handling

All drivers follow these conventions:

- **Check before act**: `check_installed()` verifies the hypervisor is available before any operations
- **Idempotent deletes**: `delete_vm()` succeeds even if the VM doesn't exist
- **Timeout on create**: VM creation waits for SSH reachability with a configurable timeout
- **SSH failures**: Propagated as driver errors with the original stderr output
- **Missing prerequisites**: Return clear error messages indicating what needs to be installed
