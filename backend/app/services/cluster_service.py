import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, BackgroundTasks

from app.models.host import Host
from app.models.vm import VM, VMStatus
from app.models.cluster import Cluster, ClusterNode, ClusterStatus, NodeRole, NodeStatus
from app.models.ssh_key import SSHKey
from app.schemas.cluster import ClusterCreate, ClusterPreview, ClusterStatusResponse, NodeAdd
from app.services.vm_service import VMService
from app.schemas.vm import VMCreate


class ClusterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_clusters(self) -> list[dict]:
        result = await self.db.execute(select(Cluster).order_by(Cluster.name))
        clusters = []
        for cluster in result.scalars().all():
            nodes = await self._get_nodes_for_cluster(cluster.id)
            cp_count = sum(1 for n in nodes if n["role"] == "control_plane")
            worker_count = sum(1 for n in nodes if n["role"] == "worker")
            clusters.append({
                "id": cluster.id,
                "name": cluster.name,
                "status": cluster.status.value if hasattr(cluster.status, 'value') else cluster.status,
                "k3s_version": cluster.k3s_version,
                "control_plane_count": cp_count,
                "worker_count": worker_count,
                "created_at": cluster.created_at,
                "updated_at": cluster.updated_at,
                "nodes": nodes,
            })
        return clusters

    async def get_cluster(self, cluster_id: int) -> dict | None:
        cluster = await self.db.get(Cluster, cluster_id)
        if not cluster:
            return None
        nodes = await self._get_nodes_for_cluster(cluster_id)
        cp_count = sum(1 for n in nodes if n["role"] == "control_plane")
        worker_count = sum(1 for n in nodes if n["role"] == "worker")
        return {
            "id": cluster.id,
            "name": cluster.name,
            "status": cluster.status.value if hasattr(cluster.status, 'value') else cluster.status,
            "k3s_version": cluster.k3s_version,
            "control_plane_count": cp_count,
            "worker_count": worker_count,
            "created_at": cluster.created_at,
            "updated_at": cluster.updated_at,
            "nodes": nodes,
        }

    async def _get_nodes_for_cluster(self, cluster_id: int) -> list[dict]:
        result = await self.db.execute(
            select(ClusterNode, VM.name, VM.ip_address, Host.ip_address, Host.rack_name)
            .join(VM, ClusterNode.vm_id == VM.id)
            .join(Host, VM.host_id == Host.id)
            .where(ClusterNode.cluster_id == cluster_id)
            .order_by(ClusterNode.role, VM.name)
        )
        nodes = []
        for node, vm_name, vm_ip, host_ip, rack_name in result.all():
            nodes.append({
                "id": node.id,
                "cluster_id": node.cluster_id,
                "vm_id": node.vm_id,
                "role": node.role.value if hasattr(node.role, 'value') else node.role,
                "status": node.status.value if hasattr(node.status, 'value') else node.status,
                "vm_name": vm_name,
                "vm_ip": vm_ip,
                "host_ip": host_ip,
                "rack_name": rack_name,
                "created_at": node.created_at,
            })
        return nodes

    async def preview_distribution(self, data: ClusterCreate) -> dict:
        hosts = await self._get_available_hosts(data.host_ids)
        if not hosts:
            raise HTTPException(status_code=400, detail="No available hosts")

        total_vms = data.control_plane_count + data.worker_count
        distribution = {}

        # Sort hosts by available RAM descending
        hosts_sorted = sorted(hosts, key=lambda h: h.ram_mb or 0, reverse=True)

        # Round-robin distribution: CP nodes first, then workers
        cp_remaining = data.control_plane_count
        worker_remaining = data.worker_count
        host_idx = 0

        for host in hosts_sorted:
            host_key = f"{host.id}"
            distribution[host_key] = {"control_plane": 0, "worker": 0}

        # Distribute CP nodes (spread for HA)
        while cp_remaining > 0:
            host = hosts_sorted[host_idx % len(hosts_sorted)]
            distribution[str(host.id)]["control_plane"] += 1
            cp_remaining -= 1
            host_idx += 1

        # Distribute workers
        while worker_remaining > 0:
            host = hosts_sorted[host_idx % len(hosts_sorted)]
            distribution[str(host.id)]["worker"] += 1
            worker_remaining -= 1
            host_idx += 1

        return {
            "distribution": distribution,
            "total_vms": total_vms,
            "total_cpu": total_vms * data.cpu_cores,
            "total_ram_mb": total_vms * data.ram_mb,
            "total_disk_gb": total_vms * data.disk_gb,
        }

    async def _get_available_hosts(self, host_ids: list[int] | None = None) -> list[Host]:
        query = select(Host).where(Host.status == "online")
        if host_ids:
            query = query.where(Host.id.in_(host_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_cluster(self, data: ClusterCreate, background_tasks: BackgroundTasks) -> dict:
        # Check name uniqueness
        existing = await self.db.execute(select(Cluster).where(Cluster.name == data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Cluster name already exists")

        cluster = Cluster(
            name=data.name,
            status=ClusterStatus.CREATING,
            k3s_version=data.k3s_version,
        )
        self.db.add(cluster)
        await self.db.commit()
        await self.db.refresh(cluster)

        # Schedule background provisioning
        background_tasks.add_task(
            self._provision_cluster, cluster.id, data
        )

        return await self.get_cluster(cluster.id)

    async def _provision_cluster(self, cluster_id: int, data: ClusterCreate) -> None:
        from app.database import async_session

        async with async_session() as db:
            try:
                cluster = await db.get(Cluster, cluster_id)
                vm_service = VMService(db)

                # Get distribution
                preview = await self.preview_distribution.__wrapped__(self, data)
                distribution = preview["distribution"]

                # Create VMs and assign to cluster
                cp_vms = []
                worker_vms = []

                for host_id_str, counts in distribution.items():
                    host_id = int(host_id_str)
                    for _ in range(counts["control_plane"]):
                        vm_data = VMCreate(
                            host_id=host_id,
                            cpu_cores=data.cpu_cores,
                            ram_mb=data.ram_mb,
                            disk_gb=data.disk_gb,
                            os_image=data.os_image,
                            ssh_key_id=data.ssh_key_id,
                        )
                        vm_dict = await vm_service.create_vm(vm_data)
                        node = ClusterNode(
                            cluster_id=cluster_id,
                            vm_id=vm_dict["id"],
                            role=NodeRole.CONTROL_PLANE,
                            status=NodeStatus.PROVISIONING,
                        )
                        db.add(node)
                        cp_vms.append(vm_dict)

                    for _ in range(counts["worker"]):
                        vm_data = VMCreate(
                            host_id=host_id,
                            cpu_cores=data.cpu_cores,
                            ram_mb=data.ram_mb,
                            disk_gb=data.disk_gb,
                            os_image=data.os_image,
                            ssh_key_id=data.ssh_key_id,
                        )
                        vm_dict = await vm_service.create_vm(vm_data)
                        node = ClusterNode(
                            cluster_id=cluster_id,
                            vm_id=vm_dict["id"],
                            role=NodeRole.WORKER,
                            status=NodeStatus.PROVISIONING,
                        )
                        db.add(node)
                        worker_vms.append(vm_dict)

                await db.flush()

                # Get SSH key for k3sup
                ssh_key = await db.get(SSHKey, data.ssh_key_id)
                key_path = ssh_key.private_key_path

                # Wait for VMs to be SSH-reachable
                all_vms = cp_vms + worker_vms
                for vm in all_vms:
                    await self._wait_for_ssh(vm["ip_address"], key_path)

                # Install first CP node
                first_cp = cp_vms[0]
                kubeconfig_path = f"/app/data/kubeconfigs/{data.name}.yaml"
                await self._run_k3sup(
                    f"k3sup install --ip {first_cp['ip_address']} --user ubuntu "
                    f"--ssh-key {key_path} --k3s-channel {data.k3s_version} "
                    f"--local-path {kubeconfig_path} --cluster"
                )

                # Join additional CP nodes
                for cp_vm in cp_vms[1:]:
                    await self._run_k3sup(
                        f"k3sup join --ip {cp_vm['ip_address']} "
                        f"--server-ip {first_cp['ip_address']} --server "
                        f"--user ubuntu --ssh-key {key_path}"
                    )

                # Join workers
                for w_vm in worker_vms:
                    await self._run_k3sup(
                        f"k3sup join --ip {w_vm['ip_address']} "
                        f"--server-ip {first_cp['ip_address']} "
                        f"--user ubuntu --ssh-key {key_path}"
                    )

                # Read and store kubeconfig
                from pathlib import Path
                kc_path = Path(kubeconfig_path)
                if kc_path.exists():
                    cluster.kubeconfig = kc_path.read_text()

                # Update statuses
                cluster.status = ClusterStatus.RUNNING
                result = await db.execute(
                    select(ClusterNode).where(ClusterNode.cluster_id == cluster_id)
                )
                for node in result.scalars().all():
                    node.status = NodeStatus.READY

                await db.commit()

            except Exception as e:
                cluster = await db.get(Cluster, cluster_id)
                if cluster:
                    cluster.status = ClusterStatus.ERROR
                    await db.commit()

    async def _wait_for_ssh(self, ip: str, key_path: str, timeout: int = 300) -> None:
        import asyncssh
        for _ in range(timeout // 5):
            try:
                conn = await asyncssh.connect(
                    ip, username="ubuntu", client_keys=[key_path],
                    known_hosts=None, connect_timeout=5,
                )
                conn.close()
                return
            except Exception:
                await asyncio.sleep(5)
        raise TimeoutError(f"SSH to {ip} not reachable after {timeout}s")

    async def _run_k3sup(self, command: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"k3sup failed: {stderr.decode()}")
        return stdout.decode()

    async def delete_cluster(self, cluster_id: int, background_tasks: BackgroundTasks) -> None:
        cluster = await self.db.get(Cluster, cluster_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")

        cluster.status = ClusterStatus.DELETING
        await self.db.commit()

        background_tasks.add_task(self._delete_cluster_vms, cluster_id)

    async def _delete_cluster_vms(self, cluster_id: int) -> None:
        from app.database import async_session

        async with async_session() as db:
            result = await db.execute(
                select(ClusterNode).where(ClusterNode.cluster_id == cluster_id)
            )
            nodes = list(result.scalars().all())

            vm_service = VMService(db)
            for node in nodes:
                try:
                    # Uninstall k3s on the VM first
                    vm = await db.get(VM, node.vm_id)
                    if vm:
                        script = "k3s-uninstall.sh" if node.role == NodeRole.CONTROL_PLANE else "k3s-agent-uninstall.sh"
                        try:
                            from app.ssh.client import SSHClient
                            ssh_key = await db.execute(select(SSHKey).where(SSHKey.id == vm.ssh_key_id))
                            key = ssh_key.scalar_one_or_none()
                            if key:
                                async with SSHClient(host=vm.ip_address, username="ubuntu", key_path=key.private_key_path) as ssh:
                                    await ssh.run_safe(f"/usr/local/bin/{script}")
                        except Exception:
                            pass

                    await db.delete(node)
                    await db.flush()

                    if vm:
                        await vm_service.delete_vm(vm.id)
                except Exception:
                    pass

            cluster = await db.get(Cluster, cluster_id)
            if cluster:
                await db.delete(cluster)
            await db.commit()

    async def get_nodes(self, cluster_id: int) -> list[dict]:
        return await self._get_nodes_for_cluster(cluster_id)

    async def add_nodes(self, cluster_id: int, data: NodeAdd, background_tasks: BackgroundTasks) -> dict:
        cluster = await self.db.get(Cluster, cluster_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")

        background_tasks.add_task(self._add_nodes_bg, cluster_id, data)
        return {"status": "adding nodes"}

    async def _add_nodes_bg(self, cluster_id: int, data: NodeAdd) -> None:
        from app.database import async_session

        async with async_session() as db:
            try:
                # Get first CP node IP
                result = await db.execute(
                    select(ClusterNode, VM)
                    .join(VM, ClusterNode.vm_id == VM.id)
                    .where(
                        ClusterNode.cluster_id == cluster_id,
                        ClusterNode.role == NodeRole.CONTROL_PLANE,
                    )
                    .limit(1)
                )
                row = result.first()
                if not row:
                    return
                _, first_cp_vm = row

                cluster = await db.get(Cluster, cluster_id)
                vm_service = VMService(db)

                for _ in range(data.count):
                    vm_create = VMCreate(
                        host_id=data.host_id,
                        ssh_key_id=None,  # Will need to be passed
                    )
                    vm_dict = await vm_service.create_vm(vm_create)

                    role = NodeRole.CONTROL_PLANE if data.role == "control_plane" else NodeRole.WORKER
                    node = ClusterNode(
                        cluster_id=cluster_id,
                        vm_id=vm_dict["id"],
                        role=role,
                        status=NodeStatus.PROVISIONING,
                    )
                    db.add(node)
                    await db.flush()

                    # Get SSH key from existing node's VM
                    vm = await db.get(VM, vm_dict["id"])
                    ssh_key = await db.get(SSHKey, vm.ssh_key_id) if vm.ssh_key_id else None
                    key_path = ssh_key.private_key_path if ssh_key else None

                    if key_path:
                        await self._wait_for_ssh(vm_dict["ip_address"], key_path)

                        cmd = f"k3sup join --ip {vm_dict['ip_address']} --server-ip {first_cp_vm.ip_address} --user ubuntu --ssh-key {key_path}"
                        if data.role == "control_plane":
                            cmd += " --server"
                        await self._run_k3sup(cmd)

                    node.status = NodeStatus.READY

                await db.commit()
            except Exception:
                pass

    async def remove_node(self, cluster_id: int, node_id: int, background_tasks: BackgroundTasks) -> None:
        node = await self.db.get(ClusterNode, node_id)
        if not node or node.cluster_id != cluster_id:
            raise HTTPException(status_code=404, detail="Node not found")

        # Check quorum for CP removal
        if node.role == NodeRole.CONTROL_PLANE:
            result = await self.db.execute(
                select(func.count(ClusterNode.id)).where(
                    ClusterNode.cluster_id == cluster_id,
                    ClusterNode.role == NodeRole.CONTROL_PLANE,
                )
            )
            cp_count = result.scalar()
            if cp_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last control plane node")

        background_tasks.add_task(self._remove_node_bg, cluster_id, node_id)

    async def _remove_node_bg(self, cluster_id: int, node_id: int) -> None:
        from app.database import async_session

        async with async_session() as db:
            node = await db.get(ClusterNode, node_id)
            if not node:
                return

            vm = await db.get(VM, node.vm_id)
            if vm:
                # Drain and delete from k8s
                ssh_key = await db.get(SSHKey, vm.ssh_key_id) if vm.ssh_key_id else None
                key_path = ssh_key.private_key_path if ssh_key else None

                if key_path:
                    # Get first CP for kubectl
                    result = await db.execute(
                        select(VM)
                        .join(ClusterNode, ClusterNode.vm_id == VM.id)
                        .where(
                            ClusterNode.cluster_id == cluster_id,
                            ClusterNode.role == NodeRole.CONTROL_PLANE,
                            ClusterNode.id != node_id,
                        )
                        .limit(1)
                    )
                    cp_vm = result.scalar_one_or_none()
                    if cp_vm:
                        try:
                            from app.ssh.client import SSHClient
                            async with SSHClient(host=cp_vm.ip_address, username="ubuntu", key_path=key_path) as ssh:
                                await ssh.run_safe(f"kubectl drain {vm.name} --ignore-daemonsets --delete-emptydir-data --force")
                                await ssh.run_safe(f"kubectl delete node {vm.name}")
                        except Exception:
                            pass

                    # Uninstall k3s
                    try:
                        from app.ssh.client import SSHClient
                        script = "k3s-uninstall.sh" if node.role == NodeRole.CONTROL_PLANE else "k3s-agent-uninstall.sh"
                        async with SSHClient(host=vm.ip_address, username="ubuntu", key_path=key_path) as ssh:
                            await ssh.run_safe(f"/usr/local/bin/{script}")
                    except Exception:
                        pass

            await db.delete(node)
            await db.flush()

            # Delete VM
            if vm:
                vm_service = VMService(db)
                try:
                    await vm_service.delete_vm(vm.id)
                except Exception:
                    pass

            await db.commit()

    async def get_kubeconfig(self, cluster_id: int) -> str | None:
        cluster = await self.db.get(Cluster, cluster_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        return cluster.kubeconfig

    async def get_status(self, cluster_id: int) -> ClusterStatusResponse:
        cluster = await self.db.get(Cluster, cluster_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")

        status = cluster.status.value if hasattr(cluster.status, 'value') else cluster.status
        messages = {
            "creating": "Cluster is being provisioned...",
            "running": "Cluster is running",
            "degraded": "Some nodes are not ready",
            "error": "Cluster encountered an error",
            "deleting": "Cluster is being deleted...",
        }

        # Calculate progress for creating status
        progress = None
        if status == "creating":
            result = await self.db.execute(
                select(func.count(ClusterNode.id)).where(
                    ClusterNode.cluster_id == cluster_id,
                    ClusterNode.status == NodeStatus.READY,
                )
            )
            ready = result.scalar()
            result = await self.db.execute(
                select(func.count(ClusterNode.id)).where(
                    ClusterNode.cluster_id == cluster_id,
                )
            )
            total = result.scalar()
            if total > 0:
                progress = int((ready / total) * 100)

        return ClusterStatusResponse(
            status=status,
            message=messages.get(status, "Unknown status"),
            progress=progress,
        )
