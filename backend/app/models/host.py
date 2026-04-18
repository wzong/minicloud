import enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Enum, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class OSType(str, enum.Enum):
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class HostStatus(str, enum.Enum):
    PENDING = "pending"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class Host(Base):
    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_user: Mapped[str] = mapped_column(String(64), nullable=False)
    ssh_key_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ssh_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rack_name: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    os_type: Mapped[OSType | None] = mapped_column(Enum(OSType), nullable=True)
    status: Mapped[HostStatus] = mapped_column(Enum(HostStatus), default=HostStatus.PENDING)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gateway: Mapped[str | None] = mapped_column(String(45), nullable=True)
    subnet_mask: Mapped[str | None] = mapped_column(String(45), nullable=True)
    dns_servers: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bridge_interface: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hypervisor_installed: Mapped[bool] = mapped_column(Boolean, default=False)
    hypervisor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bridge_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    vms: Mapped[list["VM"]] = relationship("VM", back_populates="host")
