import os
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.hashes import SHA256
import hashlib
import base64

from app.models.ssh_key import SSHKey
from app.config import settings


class SSHKeyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_keys(self) -> list[SSHKey]:
        result = await self.db.execute(select(SSHKey).order_by(SSHKey.name))
        return list(result.scalars().all())

    async def generate_key(self, name: str) -> SSHKey:
        # Check name uniqueness
        existing = await self.db.execute(select(SSHKey).where(SSHKey.name == name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="SSH key with this name already exists")

        # Generate RSA 4096-bit key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Serialize public key
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        ).decode()

        # Compute fingerprint
        fingerprint = self._compute_fingerprint(public_key)

        # Save private key to file
        key_dir = Path(settings.ssh_key_dir).expanduser()
        key_dir.mkdir(parents=True, exist_ok=True)
        key_path = key_dir / name
        key_path.write_bytes(private_pem)
        os.chmod(key_path, 0o600)

        # Save to DB
        ssh_key = SSHKey(
            name=name,
            public_key=public_ssh,
            private_key_path=str(key_path),
            fingerprint=fingerprint,
        )
        self.db.add(ssh_key)
        await self.db.commit()
        await self.db.refresh(ssh_key)
        return ssh_key

    async def import_key(self, name: str, private_key_pem: str) -> SSHKey:
        existing = await self.db.execute(select(SSHKey).where(SSHKey.name == name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="SSH key with this name already exists")

        try:
            private_key = serialization.load_ssh_private_key(
                private_key_pem.encode(), password=None
            )
        except (ValueError, Exception):
            try:
                private_key = serialization.load_pem_private_key(
                    private_key_pem.encode(), password=None
                )
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid private key format")

        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        ).decode()

        fingerprint = self._compute_fingerprint(public_key)

        # Save private key
        key_dir = Path(settings.ssh_key_dir).expanduser()
        key_dir.mkdir(parents=True, exist_ok=True)
        key_path = key_dir / name

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(private_pem)
        os.chmod(key_path, 0o600)

        ssh_key = SSHKey(
            name=name,
            public_key=public_ssh,
            private_key_path=str(key_path),
            fingerprint=fingerprint,
        )
        self.db.add(ssh_key)
        await self.db.commit()
        await self.db.refresh(ssh_key)
        return ssh_key

    async def delete_key(self, key_id: int) -> None:
        key = await self.db.get(SSHKey, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="SSH key not found")

        # Delete key file
        key_path = Path(key.private_key_path).expanduser()
        if key_path.exists():
            key_path.unlink()

        await self.db.delete(key)
        await self.db.commit()

    def _compute_fingerprint(self, public_key) -> str:
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )
        # Parse OpenSSH format to get raw key data
        parts = pub_bytes.split(b" ")
        if len(parts) >= 2:
            key_data = base64.b64decode(parts[1])
        else:
            key_data = pub_bytes
        digest = hashlib.sha256(key_data).digest()
        return "SHA256:" + base64.b64encode(digest).rstrip(b"=").decode()
