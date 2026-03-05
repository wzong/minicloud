import enum
from datetime import datetime
from sqlalchemy import String, Integer, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VMStatus(str, enum.Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DELETING = "deleting"


class VM(Base):
    __tablename__ = "vms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id"), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    status: Mapped[VMStatus] = mapped_column(Enum(VMStatus), default=VMStatus.CREATING)
    cpu_cores: Mapped[int] = mapped_column(Integer, default=2)
    ram_mb: Mapped[int] = mapped_column(Integer, default=2048)
    disk_gb: Mapped[int] = mapped_column(Integer, default=20)
    os_image: Mapped[str] = mapped_column(String(256), default="ubuntu-22.04")
    ssh_key_id: Mapped[int | None] = mapped_column(ForeignKey("ssh_keys.id"), nullable=True)
    rack_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    host: Mapped["Host"] = relationship("Host", back_populates="vms")
    ssh_key: Mapped["SSHKey | None"] = relationship("SSHKey")
    ip_allocation: Mapped["IPAllocation | None"] = relationship("IPAllocation", back_populates="vm", uselist=False)
    cluster_node: Mapped["ClusterNode | None"] = relationship("ClusterNode", back_populates="vm", uselist=False)
