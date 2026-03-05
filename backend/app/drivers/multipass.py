import json
from app.drivers.base import HypervisorDriver, VMSpec, VMInfo

TEMPLATE_DIR = __import__("pathlib").Path(__file__).parent.parent / "templates"


class MultipassDriver(HypervisorDriver):
    """Multipass hypervisor driver for macOS hosts."""

    async def create_vm(self, spec: VMSpec) -> None:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

        # Generate cloud-init user-data
        user_data = env.get_template("user-data.j2").render(
            hostname=spec.name,
            ssh_public_key=spec.ssh_public_key or "",
        )

        # Write cloud-init to temp file on host
        ci_path = f"/tmp/cloud-init-{spec.name}.yaml"
        await self.ssh.run(f"cat > {ci_path} << 'CLOUDINIT_EOF'\n{user_data}\nCLOUDINIT_EOF")

        # Launch VM
        await self.ssh.run(
            f"multipass launch --name {spec.name} "
            f"--cpus {spec.cpu_cores} --memory {spec.ram_mb}M --disk {spec.disk_gb}G "
            f"--cloud-init {ci_path} "
            f"--network name={spec.bridge},mode=manual"
        )

        # Configure static IP via netplan
        netplan_config = f"""network:
  version: 2
  ethernets:
    extra0:
      dhcp4: false
      addresses:
        - {spec.ip_address}/{self._prefix_from_mask(spec.subnet_mask)}
      routes:
        - to: default
          via: {spec.gateway}
      nameservers:
        addresses: [{', '.join(spec.dns_servers)}]"""

        if spec.routes:
            for route in spec.routes:
                netplan_config += f"\n        - to: {route['to']}"
                netplan_config += f"\n          via: {route['via']}"

        await self.ssh.run(
            f'multipass exec {spec.name} -- sudo bash -c '
            f'"echo \'{netplan_config}\' > /etc/netplan/10-custom.yaml && netplan apply"'
        )

        # Cleanup
        await self.ssh.run(f"rm -f {ci_path}")

    def _prefix_from_mask(self, mask: str) -> int:
        if "/" in mask:
            return int(mask.split("/")[1])
        try:
            import ipaddress
            return ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
        except Exception:
            return 24

    async def delete_vm(self, vm_name: str) -> None:
        await self.ssh.run_safe(f"multipass stop {vm_name}")
        await self.ssh.run(f"multipass delete {vm_name} --purge")

    async def start_vm(self, vm_name: str) -> None:
        await self.ssh.run(f"multipass start {vm_name}")

    async def stop_vm(self, vm_name: str) -> None:
        await self.ssh.run(f"multipass stop {vm_name}")

    async def get_vm_info(self, vm_name: str) -> VMInfo:
        output = await self.ssh.run(f"multipass info {vm_name} --format json")
        data = json.loads(output)
        info = data.get("info", {}).get(vm_name, {})
        state = info.get("state", "unknown").lower()
        return VMInfo(
            name=vm_name,
            state=state,
            cpu_cores=info.get("cpu_count", 0),
            ram_mb=0,
        )

    async def list_vms(self) -> list[VMInfo]:
        output = await self.ssh.run("multipass list --format json")
        data = json.loads(output)
        vms = []
        for entry in data.get("list", []):
            vms.append(VMInfo(
                name=entry["name"],
                state=entry.get("state", "unknown").lower(),
            ))
        return vms
