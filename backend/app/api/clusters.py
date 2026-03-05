from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.database import get_db
from app.schemas.cluster import (
    ClusterCreate, ClusterResponse, ClusterPreview,
    ClusterNodeResponse, ClusterStatusResponse, NodeAdd,
)

clusters_router = APIRouter(prefix="/clusters", tags=["clusters"])


@clusters_router.get("", response_model=list[ClusterResponse])
async def list_clusters(db: AsyncSession = Depends(get_db)):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    return await service.list_clusters()


@clusters_router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    cluster = await service.get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@clusters_router.post("/preview", response_model=ClusterPreview)
async def preview_cluster(data: ClusterCreate, db: AsyncSession = Depends(get_db)):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    return await service.preview_distribution(data)


@clusters_router.post("", response_model=ClusterResponse)
async def create_cluster(
    data: ClusterCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    return await service.create_cluster(data, background_tasks)


@clusters_router.delete("/{cluster_id}")
async def delete_cluster(
    cluster_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    await service.delete_cluster(cluster_id, background_tasks)
    return {"status": "deleting"}


@clusters_router.get("/{cluster_id}/nodes", response_model=list[ClusterNodeResponse])
async def get_cluster_nodes(cluster_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    return await service.get_nodes(cluster_id)


@clusters_router.post("/{cluster_id}/nodes")
async def add_cluster_nodes(
    cluster_id: int,
    data: NodeAdd,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    return await service.add_nodes(cluster_id, data, background_tasks)


@clusters_router.delete("/{cluster_id}/nodes/{node_id}")
async def remove_cluster_node(
    cluster_id: int,
    node_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    await service.remove_node(cluster_id, node_id, background_tasks)
    return {"status": "removing"}


@clusters_router.get("/{cluster_id}/kubeconfig")
async def get_kubeconfig(cluster_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    kubeconfig = await service.get_kubeconfig(cluster_id)
    if not kubeconfig:
        raise HTTPException(status_code=404, detail="Kubeconfig not available")
    return PlainTextResponse(kubeconfig)


@clusters_router.get("/{cluster_id}/status", response_model=ClusterStatusResponse)
async def get_cluster_status(cluster_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.cluster_service import ClusterService
    service = ClusterService(db)
    return await service.get_status(cluster_id)


router.include_router(clusters_router)
