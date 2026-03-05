from fastapi import APIRouter

router = APIRouter()

from app.api import hosts, vms, ssh_keys, clusters, ip, wireguard  # noqa
