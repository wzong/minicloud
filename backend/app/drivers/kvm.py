import ipaddress
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from app.drivers.base import HypervisorDriver, VMSpec, VMInfo


CLOUD_IMAGES = {
    "ubuntu-22.04": "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img",
    "ubuntu-24.04": "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img",
    "debian-12": "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2",
}

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class KVMDriver(HypervisorDriver):
    """KVM/libvirt hypervisor driver for Linux hosts."""

    def _get_image_url(self, os_image: str) -> str:
        return CLOUD_IMAGES.get(os_image, CLOUD_IMAGES["ubuntu-22.04"])

    def _subnet_to_prefix(self, subnet_mask: str) -> int:
        try:
            # Handle CIDR notation like "10.100.0.5/24"
            if "/" in subnet_mask:
                return int(subnet_mask.split("/")[1])
            # Handle dotted notation like "255.255.255.0"
            return ipaddress.IPv4Network(f"0.0.0.0/{subnet_mask}").prefixlen
        except (ValueError, Exception):
            return 24

    async def create_vm(self, spec: VMSpec) -> None:
        image_dir = "/var/lib/libvirt/images"
        base_image = f"{image_dir}/base-{spec.os_image}.qcow2"
        vm_disk = f"{image_dir}/{spec.name}.qcow2"
        ci_dir = f"/tmp/cloud-init-{spec.name}"

        # Download base image if not cached or is corrupt (zero-size)
        image_url = self._get_image_url(spec.os_image)
        await self.ssh.run(
            f"if [ ! -f {base_image} ] || [ ! -s {base_image} ]; then "
            f"rm -f {base_image} && "
            f"wget -O {base_image} {image_url} || "
            f"(rm -f {base_image} && echo 'ERROR: failed to download base image' >&2 && exit 1); "
            f"fi"
        )

        # Create disk from base image
        await self.ssh.run(
            f"qemu-img create -f qcow2 -b {base_image} -F qcow2 {vm_disk} {spec.disk_gb}G"
        )

        # Generate cloud-init files
        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

        user_data = env.get_template("user-data.j2").render(
            hostname=spec.name,
            ssh_public_key=spec.ssh_public_key or "",
        )
        meta_data = env.get_template("meta-data.j2").render(
            instance_id=spec.name,
            hostname=spec.name,
        )
        prefix_length = self._subnet_to_prefix(spec.subnet_mask)
        network_config = env.get_template("network-config.j2").render(
            ip_address=spec.ip_address,
            prefix_length=prefix_length,
            gateway=spec.gateway,
            dns_servers=spec.dns_servers,
            routes=spec.routes or [],
        )

        # Upload cloud-init files
        await self.ssh.run(f"mkdir -p {ci_dir}")
        await self.ssh.run(f"cat > {ci_dir}/user-data << 'CLOUDINIT_EOF'\n{user_data}\nCLOUDINIT_EOF")
        await self.ssh.run(f"cat > {ci_dir}/meta-data << 'CLOUDINIT_EOF'\n{meta_data}\nCLOUDINIT_EOF")
        await self.ssh.run(f"cat > {ci_dir}/network-config << 'CLOUDINIT_EOF'\n{network_config}\nCLOUDINIT_EOF")

        # Create cloud-init ISO
        ci_iso = f"{image_dir}/{spec.name}-cidata.iso"
        await self.ssh.run(
            f"cloud-localds -N {ci_dir}/network-config {ci_iso} {ci_dir}/user-data {ci_dir}/meta-data"
        )

        # Create VM with virt-install
        await self.ssh.run(
            f"virt-install --name {spec.name} "
            f"--ram {spec.ram_mb} --vcpus {spec.cpu_cores} "
            f"--import --disk {vm_disk} --disk {ci_iso},device=cdrom "
            f"--network bridge={spec.bridge},model=virtio "
            f"--os-variant ubuntu22.04 --graphics none --noautoconsole"
        )

        # Cleanup temp cloud-init dir
        await self.ssh.run(f"rm -rf {ci_dir}")

    async def delete_vm(self, vm_name: str) -> None:
        # Try graceful shutdown first
        await self.ssh.run_safe(f"virsh shutdown {vm_name}")
        # Force destroy and undefine
        await self.ssh.run_safe(f"virsh destroy {vm_name}")
        await self.ssh.run(f"virsh undefine {vm_name} --remove-all-storage")

    async def start_vm(self, vm_name: str) -> None:
        await self.ssh.run(f"virsh start {vm_name}")

    async def stop_vm(self, vm_name: str) -> None:
        await self.ssh.run(f"virsh shutdown {vm_name}")

    async def get_vm_info(self, vm_name: str) -> VMInfo:
        output = await self.ssh.run(f"virsh dominfo {vm_name}")
        state = "unknown"
        cpu = 0
        ram = 0
        for line in output.splitlines():
            if line.startswith("State:"):
                state = line.split(":", 1)[1].strip()
            elif line.startswith("CPU(s):"):
                cpu = int(line.split(":", 1)[1].strip())
            elif line.startswith("Max memory:"):
                ram = int(line.split(":", 1)[1].strip().split()[0]) // 1024  # KiB to MiB

        return VMInfo(name=vm_name, state=state, cpu_cores=cpu, ram_mb=ram)

    async def list_vms(self) -> list[VMInfo]:
        output = await self.ssh.run("virsh list --all --name")
        vms = []
        for name in output.splitlines():
            name = name.strip()
            if name:
                info = await self.get_vm_info(name)
                vms.append(info)
        return vms
