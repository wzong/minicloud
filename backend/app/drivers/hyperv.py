import json
from app.drivers.base import HypervisorDriver, VMSpec, VMInfo


CLOUD_IMAGES = {
    "ubuntu-22.04": "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.vhd",
    "ubuntu-24.04": "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.vhd",
    "debian-12": "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.vhd",
}


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
        await self._ps(f"New-Item -ItemType Directory -Force -Path '{image_dir}'")

        # Download and cache base image as VHDX
        image_url = CLOUD_IMAGES.get(spec.os_image, CLOUD_IMAGES["ubuntu-22.04"])
        base_vhd = f"{image_dir}\\base-{spec.os_image}.vhd"
        base_vhdx = f"{image_dir}\\base-{spec.os_image}.vhdx"
        await self._ps(
            f"if (-not (Test-Path '{base_vhdx}') -or (Get-Item '{base_vhdx}').Length -eq 0) {{"
            f"  Remove-Item -Force '{base_vhd}' -ErrorAction SilentlyContinue; "
            f"  Remove-Item -Force '{base_vhdx}' -ErrorAction SilentlyContinue; "
            f"  Write-Host 'Downloading base image...'; "
            f"  Invoke-WebRequest -Uri '{image_url}' -OutFile '{base_vhd}' -UseBasicParsing; "
            f"  if (-not (Test-Path '{base_vhd}') -or (Get-Item '{base_vhd}').Length -eq 0) {{"
            f"    throw 'Failed to download base image for {spec.os_image}' }}; "
            f"  Convert-VHD -Path '{base_vhd}' -DestinationPath '{base_vhdx}' -VHDType Dynamic; "
            f"  Remove-Item -Force '{base_vhd}' "
            f"}}"
        )

        # Get external switch
        switch_output = await self._ps(
            "(Get-VMSwitch -SwitchType External | Select-Object -First 1).Name"
        )
        switch_name = switch_output.strip()
        if not switch_name:
            raise RuntimeError("No external virtual switch found in Hyper-V")

        # Create differencing disk from base image and provision VM
        ram_bytes = spec.ram_mb * 1024 * 1024
        vhd_path = f"{vm_dir}\\{spec.name}.vhdx"

        await self._ps(
            f"New-VHD -Path '{vhd_path}' -ParentPath '{base_vhdx}' -Differencing"
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
        import ipaddress as _ipaddress
        import base64
        env = Environment(loader=FileSystemLoader(str(Path(__file__).parent.parent / "templates")))
        user_data = env.get_template("user-data.j2").render(
            hostname=spec.name,
            ssh_public_key=spec.ssh_public_key or "",
        )
        meta_data = env.get_template("meta-data.j2").render(
            instance_id=spec.name,
            hostname=spec.name,
        )
        try:
            if "/" in spec.subnet_mask:
                prefix_length = int(spec.subnet_mask.split("/")[1])
            else:
                prefix_length = _ipaddress.IPv4Network(f"0.0.0.0/{spec.subnet_mask}").prefixlen
        except Exception:
            prefix_length = 24
        network_config = env.get_template("network-config.j2").render(
            ip_address=spec.ip_address,
            prefix_length=prefix_length,
            gateway=spec.gateway,
            dns_servers=spec.dns_servers,
            routes=spec.routes or [],
        )

        # Write cloud-init files to a temp dir with correct names for the ISO
        ci_tmp = f"{vm_dir}\\cidata"
        await self._ps(f"New-Item -ItemType Directory -Force -Path '{ci_tmp}'")

        for filename, content in [
            ("user-data", user_data),
            ("meta-data", meta_data),
            ("network-config", network_config),
        ]:
            b64 = base64.b64encode(content.encode()).decode()
            await self._ps(
                f"[System.Text.Encoding]::UTF8.GetString("
                f"[System.Convert]::FromBase64String('{b64}')) | "
                f"Set-Content -Path '{ci_tmp}\\{filename}' -NoNewline"
            )

        await self._ps_safe(
            f"wsl genisoimage -output $(wslpath '{ci_iso}') -volid cidata -joliet -rock "
            f"$(wslpath '{ci_tmp}')"
        )

        # Cleanup temp cloud-init dir
        await self._ps_safe(f"Remove-Item -Recurse -Force '{ci_tmp}'")

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
