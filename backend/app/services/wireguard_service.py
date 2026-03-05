import json
import asyncio
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.schemas.wireguard import WGPeerCreate, WGPeerResponse, WGStatusResponse

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
PEERS_FILE = Path("/app/data/wg_peers.json")


class WireGuardService:
    def _load_peers(self) -> list[dict]:
        if PEERS_FILE.exists():
            data = json.loads(PEERS_FILE.read_text())
            return data.get("peers", [])
        return []

    def _save_peers(self, peers: list[dict]) -> None:
        PEERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PEERS_FILE.write_text(json.dumps({"peers": peers}, indent=2))

    async def generate_keypair(self) -> tuple[str, str]:
        proc = await asyncio.create_subprocess_shell(
            "wg genkey",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        private_key = stdout.decode().strip()

        proc = await asyncio.create_subprocess_shell(
            f"echo '{private_key}' | wg pubkey",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        public_key = stdout.decode().strip()

        return private_key, public_key

    async def _ensure_keys(self) -> tuple[str, str]:
        key_path = Path(settings.wg_private_key_path)
        if key_path.exists():
            private_key = key_path.read_text().strip()
            proc = await asyncio.create_subprocess_shell(
                f"echo '{private_key}' | wg pubkey",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            public_key = stdout.decode().strip()
            return private_key, public_key

        private_key, public_key = await self.generate_keypair()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(private_key)
        return private_key, public_key

    async def regenerate_config(self) -> None:
        private_key, _ = await self._ensure_keys()
        peers = self._load_peers()

        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        config = env.get_template("wg0.conf.j2").render(
            private_key=private_key,
            address=settings.wg_address,
            listen_port=settings.wg_port,
            peers=peers,
        )

        config_path = Path("/etc/wireguard/wg0.conf")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config)

        # Reload WireGuard
        proc = await asyncio.create_subprocess_shell(
            "wg-quick down wg0 2>/dev/null; wg-quick up wg0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    async def get_status(self) -> WGStatusResponse:
        _, public_key = await self._ensure_keys()

        proc = await asyncio.create_subprocess_shell(
            "wg show wg0 2>/dev/null",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode().strip()
        is_up = bool(output)

        peers_info = self._parse_wg_show(output) if is_up else []

        return WGStatusResponse(
            interface="wg0",
            public_key=public_key,
            listen_port=settings.wg_port,
            address=settings.wg_address,
            is_up=is_up,
            peers=peers_info,
        )

    def _parse_wg_show(self, output: str) -> list[WGPeerResponse]:
        peers = []
        saved_peers = {p["public_key"]: p for p in self._load_peers()}
        current = {}

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("peer:"):
                if current:
                    peers.append(self._make_peer_response(current, saved_peers))
                current = {"public_key": line.split(":", 1)[1].strip()}
            elif line.startswith("endpoint:"):
                current["endpoint"] = line.split(":", 1)[1].strip()
            elif line.startswith("allowed ips:"):
                current["allowed_ips"] = line.split(":", 1)[1].strip()
            elif line.startswith("latest handshake:"):
                current["latest_handshake"] = line.split(":", 1)[1].strip()
            elif line.startswith("transfer:"):
                parts = line.split(":", 1)[1].strip().split(",")
                if len(parts) == 2:
                    current["transfer_rx"] = parts[0].strip()
                    current["transfer_tx"] = parts[1].strip()

        if current:
            peers.append(self._make_peer_response(current, saved_peers))

        return peers

    def _make_peer_response(self, current: dict, saved_peers: dict) -> WGPeerResponse:
        pub_key = current.get("public_key", "")
        saved = saved_peers.get(pub_key, {})
        return WGPeerResponse(
            datacenter_code=saved.get("datacenter_code", "unknown"),
            public_key=pub_key,
            endpoint=current.get("endpoint", saved.get("endpoint", "")),
            allowed_ips=current.get("allowed_ips", saved.get("allowed_ips", "")),
            comment=saved.get("comment"),
            latest_handshake=current.get("latest_handshake"),
            transfer_rx=current.get("transfer_rx"),
            transfer_tx=current.get("transfer_tx"),
        )

    async def get_public_key(self) -> dict:
        _, public_key = await self._ensure_keys()
        return {"public_key": public_key}

    async def list_peers(self) -> list[WGPeerResponse]:
        peers = self._load_peers()
        return [
            WGPeerResponse(
                datacenter_code=p["datacenter_code"],
                public_key=p["public_key"],
                endpoint=p["endpoint"],
                allowed_ips=p["allowed_ips"],
                comment=p.get("comment"),
            )
            for p in peers
        ]

    async def add_peer(self, data: WGPeerCreate) -> WGPeerResponse:
        peers = self._load_peers()
        # Check for duplicate
        for p in peers:
            if p["datacenter_code"] == data.datacenter_code:
                raise ValueError(f"Peer with datacenter code '{data.datacenter_code}' already exists")

        peer = {
            "datacenter_code": data.datacenter_code,
            "public_key": data.public_key,
            "endpoint": data.endpoint,
            "allowed_ips": data.allowed_ips,
            "comment": data.comment,
        }
        peers.append(peer)
        self._save_peers(peers)
        await self.regenerate_config()

        return WGPeerResponse(**peer)

    async def remove_peer(self, datacenter_code: str) -> None:
        peers = self._load_peers()
        peers = [p for p in peers if p["datacenter_code"] != datacenter_code]
        self._save_peers(peers)
        await self.regenerate_config()
