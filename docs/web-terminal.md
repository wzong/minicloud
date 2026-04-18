# Web SSH Terminal

## Motivation

Operators previously had to leave the Minicloud UI and `ssh` from a workstation to debug a misbehaving Host or a freshly provisioned VM. The web terminal surfaces a one-click shell on every Host and VM row, reusing the credentials Minicloud already stores for normal operations. No new auth surface is introduced — if the backend can manage the machine, the UI can shell into it.

## User Experience

- A **Terminal** button (Ant Design `<CodeOutlined/>`) appears in the action `Space` of every row in the Hosts and VMs tables (and in the mobile Card actions, since both pages render the same `actionButtons` / `vmActions` callback).
- The button is disabled unless the target is healthy:
  - Hosts: `status === 'online'`
  - VMs: `status === 'running'` (and the VM has a `ssh_key_id`)
- Clicking opens a right-side `Drawer` (width 900 on desktop, full-screen on mobile) that mounts an xterm.js terminal connected via WebSocket.
- Resize the Drawer or the window → `FitAddon` reflows the terminal and a control frame tells the remote PTY (verifiable with `echo $COLUMNS`).
- Closing the Drawer disposes the terminal, closes the WebSocket, terminates the remote process and disconnects the SSH session.

## Architecture

```
Browser                         FastAPI                       Target
┌─────────────────┐   WS    ┌────────────────────┐   SSH   ┌──────────┐
│ TerminalDrawer  │◄──────► │ /api/{hosts|vms}/  │◄──────► │ Host/VM  │
│ (xterm.js +     │ binary  │   {id}/terminal    │  PTY +  │ shell    │
│  FitAddon)      │ + JSON  │ proxy_terminal()   │  stdio  │          │
└─────────────────┘         └────────────────────┘         └──────────┘
```

### Wire protocol

A single WebSocket carries two interleaved channels using FastAPI's frame-type discrimination:

| Direction | Frame | Meaning |
|-----------|-------|---------|
| Client → Server | **binary** | Raw stdin bytes (typed keys, paste, escape sequences) |
| Client → Server | **text** (JSON) | Control message: `{"type":"resize","cols":N,"rows":M}` |
| Server → Client | **binary** | Raw stdout/stderr bytes |

Using JSON only on the rare control path keeps the hot data path zero-overhead and avoids interpreting user keystrokes as text (which would mishandle binary bytes from things like `vim`, `less`, or terminal mouse reporting).

### WebSocket close codes

| Code | Cause |
|------|-------|
| `1000` | Normal close (drawer closed by user) |
| `1011` | SSH connect or shell-start failure (a red ANSI message is sent first) |
| `4404` | Host/VM record not found |
| `4409` | VM is not in `running` state |
| `4412` | VM has no `ssh_key_id` or the referenced `SSHKey` was deleted |

## Backend

### `SSHClient.start_shell` — `backend/app/ssh/client.py`

Adds the only new asyncssh primitive needed for interactive sessions:

```python
async def start_shell(self, term_type="xterm-256color", term_size=(80, 24)):
    if not self._conn:
        await self.connect()
    return await self._conn.create_process(
        term_type=term_type, term_size=term_size, encoding=None,
    )
```

`encoding=None` keeps stdin/stdout as raw `bytes` so PTY escape sequences pass through untouched. The returned `SSHClientProcess` exposes `stdin.write`, `stdout.read`, `stderr.read`, `change_terminal_size`, and `terminate` — all the primitives the proxy needs.

### `proxy_terminal` — `backend/app/ssh/terminal.py`

Bidirectional pump shared by both endpoints. Three concurrent tasks:

1. **ws → ssh**: `await websocket.receive()`; binary → `process.stdin.write(bytes)`; text → JSON `resize` → `process.change_terminal_size(cols, rows)`.
2. **stdout → ws**: chunked 4 KiB reads → `websocket.send_bytes(...)`.
3. **stderr → ws**: same as above on the other stream.

`asyncio.wait(..., FIRST_COMPLETED)` short-circuits as soon as any side closes; the surviving tasks are cancelled and awaited. The `finally` block guarantees `process.terminate()`, `ssh_client.disconnect()`, and `websocket.close()` regardless of how the connection ended (clean disconnect, network drop, exception, or backend shutdown).

Connect uses `asyncio.wait_for(..., timeout=30)` so a dead host never wedges a worker. Failures are reported in-band as a red ANSI message before close so the user sees a real error instead of an opaque socket close.

### Routes — `backend/app/api/terminal.py`

- `GET ws://…/api/hosts/{host_id}/terminal` — looks up `Host`, builds an `SSHClient` via `HostService(db).get_ssh_client(host)` (the existing host-credential builder, promoted from `_get_ssh_client` to public).
- `GET ws://…/api/vms/{vm_id}/terminal` — looks up `VM`, validates `status == running` and `ssh_key_id is not None`, loads the joined `SSHKey`, then constructs `SSHClient(host=vm.ip_address, port=22, username="ubuntu", key_path=ssh_key.private_key_path)`. The username matches the `ubuntu` cloud-init user injected during provisioning (`vm_service._provision_vm`).

The router self-registers via `router.include_router(terminal_router)` and is imported from `app/api/__init__.py`, mirroring every other router module.

## Frontend

### `TerminalDrawer` — `frontend/src/components/terminal/TerminalDrawer.tsx`

- Props: `{ open, onClose, wsPath, title }`. The page passes the WebSocket path so one component serves both Hosts and VMs.
- On mount: instantiate `Terminal`, attach `FitAddon`, `term.open(container)`, then `fit.fit()` on the next frame (after the Drawer animation has measured the container).
- WebSocket URL is built from `window.location` (`wss://` over HTTPS, `ws://` otherwise) so it works behind any reverse proxy without extra config.
- `binaryType = 'arraybuffer'` so server frames arrive as `Uint8Array` (cheaper than Blob).
- `term.onData` → `ws.send(TextEncoder.encode(data))` (binary stdin).
- `term.onResize` and `ResizeObserver` → JSON resize control frame (also sent once on `onopen` to seed the remote PTY before the user types).
- Cleanup on close/unmount: dispose xterm, disconnect observer, close socket. `destroyOnClose` on the Drawer also forces React to unmount when hidden.

### Page integration

Both `HostsPage.tsx` and `VMsPage.tsx` add a single `useState<Host|VM|null>` for the open target, a `<Tooltip><Button icon={<CodeOutlined/>}/></Tooltip>` inside the existing `actionButtons` / `vmActions` `Space` (so it appears in both desktop table rows and mobile Card actions automatically), and a single `<TerminalDrawer/>` rendered at page level. No changes are needed to the API client (`frontend/src/api/`) — WebSockets are constructed directly from `window.location`.

## Security & Limitations

- **Authentication is inherited from the HTTP origin.** This release does not add per-WebSocket auth; it assumes the existing UI is behind whatever access control the operator already runs. If/when the REST API gains real auth (cookies, OIDC, etc.), the WebSocket routes will pick it up via the same `Depends(get_db)` middleware chain.
- **No session recording** — interactions are point-to-point. Add an `aiofiles` tee in `proxy_terminal` if audit trails become a requirement.
- **One process per connection** — no shared sessions or multiplexing. Closing the Drawer kills the remote shell.
- **`known_hosts=None`** is inherited from `SSHClient.connect`. This matches existing Minicloud behaviour but means MITM is not detected; tracked alongside the broader SSH hardening work.

## Verification

1. `cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --port 8080`
2. `cd frontend && npm install && npm run dev`
3. Add a Host, wait for `online`. Click **Terminal** → Drawer opens within ~2 s with a shell prompt.
4. `whoami`, `uname -a`, `echo $COLUMNS $LINES`, `stty -a` — confirms PTY + size.
5. Resize the Drawer → rerun `echo $COLUMNS` → value updates.
6. Run `top`, then `q`; open `vi /tmp/x` — arrow keys, Ctrl-C, Ctrl-D all behave.
7. Open/close the Drawer 5× — `ss -tnp | grep :22` shows no leaked sockets.
8. Provision a VM → wait for `running` → click **Terminal** → `ubuntu@…` prompt appears.
9. Stop sshd on the host → button shows red error line and the WS closes.
10. `python -m pytest tests/backend/ -v` — existing tests still pass.

## Files Touched

| File | Change |
|------|--------|
| `backend/app/ssh/client.py` | + `start_shell()` |
| `backend/app/ssh/terminal.py` | new — `proxy_terminal()` |
| `backend/app/api/terminal.py` | new — two WebSocket routes |
| `backend/app/api/__init__.py` | import the new module |
| `backend/app/services/host_service.py` | `_get_ssh_client` → public `get_ssh_client` (alias kept) |
| `frontend/package.json` | + `@xterm/xterm`, `@xterm/addon-fit` |
| `frontend/src/components/terminal/TerminalDrawer.tsx` | new — xterm.js Drawer |
| `frontend/src/pages/HostsPage.tsx` | Terminal button + drawer wiring |
| `frontend/src/pages/VMsPage.tsx` | Terminal button + drawer wiring |
