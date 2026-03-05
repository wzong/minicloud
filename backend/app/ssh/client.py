import asyncssh
from typing import Optional


class SSHClient:
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        key_path: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path
        self.password = password
        self._conn: Optional[asyncssh.SSHClientConnection] = None

    async def connect(self) -> None:
        kwargs = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "known_hosts": None,
        }
        if self.key_path:
            kwargs["client_keys"] = [self.key_path]
        if self.password:
            kwargs["password"] = self.password
        self._conn = await asyncssh.connect(**kwargs)

    async def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    async def run(self, command: str) -> str:
        if not self._conn:
            await self.connect()
        result = await self._conn.run(command, check=False)
        if result.exit_status != 0:
            raise SSHCommandError(
                command=command,
                exit_status=result.exit_status,
                stderr=result.stderr or "",
            )
        return (result.stdout or "").strip()

    async def run_multi(self, commands: list[str]) -> list[str]:
        results = []
        for cmd in commands:
            results.append(await self.run(cmd))
        return results

    async def run_safe(self, command: str) -> tuple[bool, str]:
        """Run command returning (success, output) without raising on failure."""
        if not self._conn:
            await self.connect()
        result = await self._conn.run(command, check=False)
        success = result.exit_status == 0
        output = (result.stdout or "").strip() if success else (result.stderr or "").strip()
        return success, output

    async def upload(self, local_path: str, remote_path: str) -> None:
        if not self._conn:
            await self.connect()
        await asyncssh.scp(local_path, (self._conn, remote_path))

    async def download(self, remote_path: str, local_path: str) -> None:
        if not self._conn:
            await self.connect()
        await asyncssh.scp((self._conn, remote_path), local_path)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()


class SSHCommandError(Exception):
    def __init__(self, command: str, exit_status: int, stderr: str):
        self.command = command
        self.exit_status = exit_status
        self.stderr = stderr
        super().__init__(f"Command '{command}' failed (exit {exit_status}): {stderr}")
