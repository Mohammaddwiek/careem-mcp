# careem-mcp (Python)

Local careem-mcp server built from `spec/` (a copy of `../careem-mcp-sandbox/spec`), following
`spec/BUILD.md`. It answers every tool call from the scenario files and makes no network calls.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## CLI

Use `careem-mcp.ps1` / `careem-mcp.cmd` on Windows or `./careem-mcp.sh` in a POSIX shell.

| Command | What it does |
| --- | --- |
| `start` / `stop` / `status` | run the HTTP server in the background on `http://127.0.0.1:8787/mcp` |
| `logs [-n 50]` | tail `.run/server.log` (one line per tool call: tool, scenario, args) |
| `scenarios [tool]` | list scenarios and their match rules |
| `scenario <tool> <name>` | force a scenario (writes `.run/overrides.json`); omit `<name>` to clear |
| `reset` | clear all forced scenarios |
| `check` | render every scenario and validate it against the tool's output schema |

Other transports: `GET /sse` (legacy SSE), `python -m careem_mcp.server --stdio`.
Health: `GET /health`. Settings: `--port`, `--spec-dir`, `--overrides`, `--widget-domain`,
`--allowed-host` (for tunnels), `--no-output-schema`, `--no-meta`, or the `CAREEM_MCP_*` env vars.

## Tests

```powershell
.venv\Scripts\python -m pytest tests
```

Covers acceptance tests 1-12 from `spec/BUILD.md` §7 against a real server on a free port.

## Connect

```powershell
claude mcp add --transport http careem-mcp http://127.0.0.1:8787/mcp
```
