from app.drivers.base import HypervisorDriver, VMSpec, VMInfo
from app.drivers.kvm import KVMDriver
from app.drivers.multipass import MultipassDriver
from app.drivers.hyperv import HyperVDriver


def get_driver(os_type, ssh_client) -> HypervisorDriver:
    os_val = os_type.value if hasattr(os_type, 'value') else str(os_type)
    if os_val == "linux":
        return KVMDriver(ssh_client)
    elif os_val == "macos":
        return MultipassDriver(ssh_client)
    elif os_val == "windows":
        return HyperVDriver(ssh_client)
    else:
        raise ValueError(f"Unsupported OS type: {os_type}")
