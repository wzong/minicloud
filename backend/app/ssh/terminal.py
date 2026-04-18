import asyncio
import json
import logging

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.ssh.client import SSHClient

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 30
READ_CHUNK_BYTES = 4096


async def _send_error(websocket: WebSocket, message: str) -> None:
    if websocket.client_state == WebSocketState.CONNECTED:
        try:
            await websocket.send_bytes(f"\r\n\x1b[31m{message}\x1b[0m\r\n".encode())
        except Exception:
            pass


async def proxy_terminal(websocket: WebSocket, ssh_client: SSHClient) -> None:
    await websocket.accept()

    try:
        await asyncio.wait_for(ssh_client.connect(), timeout=CONNECT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        await _send_error(websocket, "SSH connection timed out")
        await websocket.close(code=1011)
        return
    except Exception as exc:
        await _send_error(websocket, f"SSH connection failed: {exc}")
        await websocket.close(code=1011)
        return

    try:
        process = await ssh_client.start_shell()
    except Exception as exc:
        await _send_error(websocket, f"Failed to start shell: {exc}")
        await ssh_client.disconnect()
        await websocket.close(code=1011)
        return

    async def ws_to_ssh() -> None:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()
            if "bytes" in msg and msg["bytes"] is not None:
                process.stdin.write(msg["bytes"])
            elif "text" in msg and msg["text"] is not None:
                try:
                    payload = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "resize":
                    cols = int(payload.get("cols", 80))
                    rows = int(payload.get("rows", 24))
                    try:
                        process.change_terminal_size(cols, rows)
                    except Exception:
                        pass

    async def stream_to_ws(stream) -> None:
        while True:
            data = await stream.read(READ_CHUNK_BYTES)
            if not data:
                return
            await websocket.send_bytes(data)

    tasks = [
        asyncio.create_task(ws_to_ssh()),
        asyncio.create_task(stream_to_ws(process.stdout)),
        asyncio.create_task(stream_to_ws(process.stderr)),
    ]

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                logger.warning("Terminal proxy task error: %s", exc)
    finally:
        try:
            process.terminate()
        except Exception:
            pass
        try:
            await ssh_client.disconnect()
        except Exception:
            pass
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception:
                pass
