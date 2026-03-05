from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    model_config = {"env_prefix": "MC_"}

    datacenter_code: str = "dc"
    ip_range_start: str = "10.100.0.10"
    ip_range_end: str = "10.100.0.254"
    ip_subnet_mask: str = "255.255.255.0"
    ip_gateway: str = "10.100.0.1"
    ip_dns: str = "8.8.8.8,8.8.4.4"
    db_path: str = "/app/data/minicloud.db"
    ssh_key_dir: str = "/app/data/ssh_keys"
    wg_private_key_path: str = "/app/data/wg_private.key"
    wg_port: int = 51820
    wg_address: str = "10.200.0.1/24"
    wg_gateway_ip: str = ""

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    @property
    def dns_servers(self) -> list[str]:
        return [s.strip() for s in self.ip_dns.split(",")]


settings = Settings()
