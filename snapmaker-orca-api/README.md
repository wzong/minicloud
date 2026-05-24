# Snapmaker Orca API + UI

A web API and React UI wrapping [Snapmaker Orca Slicer](https://github.com/Snapmaker/OrcaSlicer)
(an OrcaSlicer fork). Upload a model, configure slicing parameters with full GUI parity,
and preview the resulting G-code in a browser-based 3D viewer.

## Architecture

- **Backend**: FastAPI (Python 3.12). Invokes the installed `snapmaker-orca` binary in CLI
  mode (`--slice`, `--load-settings`, `--load-filaments`, `--export-3mf`). Parses the
  produced G-code into a layer/move graph for the viewer.
- **Frontend**: React 18 + TypeScript + Vite + Ant Design 5 + TanStack Query.
  three.js G-code viewer with layer slider, feature coloring, and travel-move toggle.
- **Profiles**: Discovers Snapmaker Orca's bundled printer / filament / process profiles
  from the slicer's resources directory and exposes them as presets. Users override
  individual settings on top of a chosen preset.

## Configuration

Environment variables (prefix `SO_`):

| Var                       | Default                                         | Meaning |
|---------------------------|-------------------------------------------------|---------|
| `SO_SLICER_BIN`           | `/usr/bin/snapmaker-orca`                       | Path to the slicer executable |
| `SO_SLICER_RESOURCES_DIR` | `/usr/share/snapmaker-orca/resources`           | Directory containing `profiles/`, used to enumerate presets |
| `SO_WORK_DIR`             | `/var/lib/snapmaker-orca-api/work`              | Where uploads, configs, and G-code are written |
| `SO_DB_URL`               | `sqlite+aiosqlite:///./snapmaker_orca_api.db`   | Job database |
| `SO_HOST`                 | `0.0.0.0`                                       | Bind host |
| `SO_PORT`                 | `8090`                                          | Bind port |
| `SO_CORS_ORIGINS`         | `http://localhost:5173`                         | Comma-separated CORS origins |

## Running

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8090

# Frontend
cd frontend
npm install
npm run dev    # http://localhost:5173

# Tests
pytest tests/backend -v
```

## API

| Method | Path                          | Description |
|--------|-------------------------------|-------------|
| GET    | `/api/health`                 | Liveness + detected slicer version |
| GET    | `/api/settings/catalog`       | Categorised setting definitions for the UI |
| GET    | `/api/presets`                | Enumerated printer / filament / process presets |
| GET    | `/api/presets/{kind}/{name}`  | Resolved preset values (inheritance flattened) |
| POST   | `/api/uploads`                | Upload an `.stl` / `.3mf` / `.obj` model |
| POST   | `/api/slice`                  | Start a slice job — body: `upload_id`, `printer`, `filament`, `process`, `overrides` |
| GET    | `/api/jobs/{id}`              | Job state, progress, slicing stats |
| GET    | `/api/jobs/{id}/gcode`        | Download produced G-code |
| GET    | `/api/jobs/{id}/preview`      | Parsed G-code (layers, moves, stats) for the 3D viewer |
| GET    | `/api/jobs/{id}/logs`         | stdout/stderr from the slicer CLI |
| DELETE | `/api/jobs/{id}`              | Cancel / delete a job |

## Settings parity

The settings catalog (`backend/app/data/settings_catalog.json`) mirrors Snapmaker Orca's
tabs: **Quality**, **Strength**, **Speed**, **Support**, **Others**, **Multimaterial**,
**Filament**, and **Printer**. Each entry carries label, type, default, range, unit, and
tooltip metadata so the UI can render forms dynamically. Any setting not in the catalog
can still be passed through `overrides` — the API forwards unknown keys verbatim to the
slicer's JSON config.

## Status

Skeleton implementation. The core flow (upload → configure → slice → preview) works end
to end; the settings catalog ships with the most common ~100 settings across all tabs and
is designed to be extended by appending entries.
