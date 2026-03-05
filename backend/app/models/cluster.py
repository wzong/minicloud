import enum
from datetime import datetime
from sqlalchemy import String, Integer, Enum, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ClusterStatus(str, enum.Enum):
    CREATING = "creating"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"
    DELETING = "deleting"


class NodeRole(str, enum.Enum):
    CONTROL_PLANE = "control_plane"
    WORKER = "worker"


class NodeStatus(str, enum.Enum):
    PROVISIONING = "provisioning"
    READY = "ready"
    NOT_READY = "not_ready"
    ERROR = "error"


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[ClusterStatus] = mapped_column(Enum(ClusterStatus), default=ClusterStatus.CREATING)
    k3s_version: Mapped[str] = mapped_column(String(32), default="stable")
    kubeconfig: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    nodes: Mapped[list["ClusterNode"]] = relationship("ClusterNode", back_populates="cluster", cascade="all, delete-orphan")


class ClusterNode(Base):
    __tablename__ = "cluster_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"), nullable=False)
    vm_id: Mapped[int] = mapped_column(ForeignKey("vms.id"), unique=True, nullable=False)
    role: Mapped[NodeRole] = mapped_column(Enum(NodeRole), nullable=False)
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus), default=NodeStatus.PROVISIONING)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cluster: Mapped["Cluster"] = relationship("Cluster", back_populates="nodes")
    vm: Mapped["VM"] = relationship("VM", back_populates="cluster_node")
