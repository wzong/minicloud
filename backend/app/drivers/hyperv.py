import json
from app.drivers.base import HypervisorDriver, VMSpec, VMInfo


class HyperVDriver(HypervisorDriver):
    """Hyper-V driver for Windows hosts. All commands via PowerShell over SSH."""

    async def _ps(self, command: str) -> str:
        return await self.ssh.run(f'powershell -Command "{command}"')

    async def _ps_safe(self, command: str) -> tuple[bool, str]:
        return await self.ssh.run_safe(f'powershell -Command "{command}"')

    async def create_vm(self, spec: VMSpec) -> None:
        image_dir = "C:\\HyperV\\Images"
        vm_dir = f"C:\\HyperV\\VMs\\{spec.name}"

        # Ensure directories exist
        await self._ps(f"New-Item -ItemType Directory -Force -Path '{vm_dir}'")

        # Get external switch
        switch_output = await self._ps(
            "(Get-VMSwitch -SwitchType External | Select-Object -First 1).Name"
        )
        switch_name = switch_output.strip()
        if not switch_name:
            raise RuntimeError("No external virtual switch found in Hyper-V")

        # Create VM
        ram_bytes = spec.ram_mb * 1024 * 1024
        disk_bytes = spec.disk_gb * 1024 * 1024 * 1024
        vhd_path = f"{vm_dir}\\{spec.name}.vhdx"

        await self._ps(
            f"New-VHD -Path '{vhd_path}' -SizeBytes {disk_bytes} -Dynamic"
        )
        await self._ps(
            f"New-VM -Name '{spec.name}' -MemoryStartupBytes {ram_bytes} "
            f"-VHDPath '{vhd_path}' -SwitchName '{switch_name}' -Generation 2"
        )
        await self._ps(
            f"Set-VM -Name '{spec.name}' -ProcessorCount {spec.cpu_cores} "
            f"-AutomaticCheckpointsEnabled $false"
        )

        # Create cloud-init ISO if tools available
        ci_iso = f"{vm_dir}\\cidata.iso"
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        env = Environment(loader=FileSystemLoader(str(Path(__file__).parent.parent / "templates")))
        user_data = env.get_template("user-data.j2").render(
            hostname=spec.name,
            ssh_public_key=spec.ssh_public_key or "",
        )
        meta_data = env.get_template("meta-data.j2").render(
            instance_id=spec.name,
            hostname=spec.name,
        )

        # Write cloud-init files via WSL genisoimage
        await self._ps(f"New-Item -ItemType Directory -Force -Path '{vm_dir}\\cidata'")
        await self.ssh.run(f"echo '{user_data}' > /tmp/{spec.name}-user-data")
        await self.ssh.run(f"echo '{meta_data}' > /tmp/{spec.name}-meta-data")

        await self._ps_safe(
            f"wsl genisoimage -output {ci_iso} -volid cidata -joliet -rock "
            f"/tmp/{spec.name}-user-data /tmp/{spec.name}-meta-data"
        )

        # Add DVD drive with cloud-init ISO
        await self._ps_safe(
            f"Add-VMDvdDrive -VMName '{spec.name}' -Path '{ci_iso}'"
        )

        # Start VM
        await self._ps(f"Start-VM -Name '{spec.name}'")

    async def delete_vm(self, vm_name: str) -> None:
        await self._ps_safe(f"Stop-VM -Name '{vm_name}' -Force -ErrorAction SilentlyContinue")
        await self._ps(f"Remove-VM -Name '{vm_name}' -Force")
        await self._ps_safe(f"Remove-Item -Recurse -Force 'C:\\HyperV\\VMs\\{vm_name}'")

    async def start_vm(self, vm_name: str) -> None:
        await self._ps(f"Start-VM -Name '{vm_name}'")

    async def stop_vm(self, vm_name: str) -> None:
        await self._ps(f"Stop-VM -Name '{vm_name}'")

    async def get_vm_info(self, vm_name: str) -> VMInfo:
        output = await self._ps(
            f"Get-VM -Name '{vm_name}' | Select-Object Name, State, ProcessorCount, "
            f"MemoryAssigned | ConvertTo-Json"
        )
        data = json.loads(output)
        state_map = {0: "unknown", 2: "running", 3: "stopped", 6: "saved", 9: "paused"}
        state = state_map.get(data.get("State", 0), "unknown")
        return VMInfo(
            name=vm_name,
            state=state,
            cpu_cores=data.get("ProcessorCount", 0),
            ram_mb=data.get("MemoryAssigned", 0) // (1024 * 1024),
        )

    async def list_vms(self) -> list[VMInfo]:
        output = await self._ps(
            "Get-VM | Select-Object Name, State | ConvertTo-Json"
        )
        data = json.loads(output)
        if isinstance(data, dict):
            data = [data]
        vms = []
        state_map = {0: "unknown", 2: "running", 3: "stopped", 6: "saved", 9: "paused"}
        for entry in data:
            vms.append(VMInfo(
                name=entry["Name"],
                state=state_map.get(entry.get("State", 0), "unknown"),
            ))
        return vms
