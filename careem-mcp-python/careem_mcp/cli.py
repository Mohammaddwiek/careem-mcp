"""careem-mcp CLI: start, stop, status, logs, scenarios [tool], scenario <tool> [name], reset, check."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from jsonschema import Draft202012Validator

from . import live, spec
from .server import PROJECT_DIR

RUN_DIR = PROJECT_DIR / ".run"
PID_FILE = RUN_DIR / "server.pid"
LOG_FILE = RUN_DIR / "server.log"
OVERRIDES = Path(os.environ.get("CAREEM_MCP_OVERRIDES", RUN_DIR / "overrides.json"))
SPEC_DIR = Path(os.environ.get("CAREEM_MCP_SPEC_DIR", PROJECT_DIR / "spec"))
CART_STATE = Path(os.environ.get("CAREEM_MCP_CART_STATE", RUN_DIR / "cart.json"))
CATALOG = Path(os.environ.get("CAREEM_MCP_CATALOG", PROJECT_DIR / "catalog" / "quik.json"))
PORT = int(os.environ.get("CAREEM_MCP_PORT", "8787"))
HOST = os.environ.get("CAREEM_MCP_HOST", "127.0.0.1")


def _alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes

        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(handle, ctypes.byref(code))
        k32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return None
    return pid if _alive(pid) else None


def _health() -> dict | None:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def cmd_start(extra: list[str]) -> int:
    if _pid():
        print(f"already running (pid {_pid()}) on http://{HOST}:{PORT}/mcp")
        return 0
    RUN_DIR.mkdir(exist_ok=True)
    if not OVERRIDES.exists():
        OVERRIDES.write_text("{}\n")
    log = open(LOG_FILE, "ab")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(
        [sys.executable, "-m", "careem_mcp.server", "--host", HOST, "--port", str(PORT), *extra],
        cwd=PROJECT_DIR,
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )
    PID_FILE.write_text(str(proc.pid))
    for _ in range(50):
        if proc.poll() is not None:
            print(f"server exited with code {proc.returncode}; see {LOG_FILE}")
            return 1
        h = _health()
        if h:
            print(f"started (pid {proc.pid}): http://{HOST}:{PORT}/mcp, {h['tools']} tools")
            return 0
        time.sleep(0.2)
    print(f"server did not become healthy; see {LOG_FILE}")
    return 1


def cmd_stop() -> int:
    pid = _pid()
    if not pid:
        print("not running")
        PID_FILE.unlink(missing_ok=True)
        return 0
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        import signal

        os.kill(pid, signal.SIGTERM)
    for _ in range(25):
        if not _alive(pid):
            break
        time.sleep(0.2)
    PID_FILE.unlink(missing_ok=True)
    print(f"stopped (pid {pid})")
    return 0


def cmd_status() -> int:
    pid, h = _pid(), _health()
    if pid and h:
        print(f"running (pid {pid}): http://{HOST}:{PORT}/mcp, {h['tools']} tools")
    elif h:
        print(f"something is serving http://{HOST}:{PORT} ({h['tools']} tools) but not started by this CLI")
    else:
        print("not running")
    forced = _read_overrides()
    if forced:
        print("forced scenarios: " + ", ".join(f"{t} -> {s}" for t, s in sorted(forced.items())))
    return 0 if h else 1


def cmd_logs(lines: int) -> int:
    if not LOG_FILE.exists():
        print("no log yet")
        return 0
    for line in LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]:
        print(line)
    return 0


def _read_overrides() -> dict[str, str]:
    try:
        data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_overrides(data: dict[str, str]) -> None:
    OVERRIDES.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def cmd_scenarios(tool: str | None) -> int:
    tools = spec.load_all(SPEC_DIR)
    forced = _read_overrides()
    names = [tool] if tool else sorted(tools)
    for name in names:
        if name not in tools:
            print(f"unknown tool {name!r}")
            return 1
        print(name)
        for s in tools[name].scenarios:
            tags = []
            if s.match is None:
                tags.append("default")
            else:
                tags.append("match " + spec.compact(s.match))
            if s.is_error:
                tags.append("isError")
            if forced.get(name, "").lower() == s.name.lower():
                tags.append("FORCED")
            print(f"  {s.name:<34} {'; '.join(tags)}")
    return 0


def cmd_scenario(tool: str, name: str | None) -> int:
    tools = spec.load_all(SPEC_DIR)
    if tool not in tools:
        print(f"unknown tool {tool!r}")
        return 1
    data = _read_overrides()
    if name is None:
        data.pop(tool, None)
        _write_overrides(data)
        print(f"{tool}: cleared, scenarios chosen by arguments again")
        return 0
    s = tools[tool].scenario(name)
    if s is None:
        print(f"{tool} has no scenario {name!r}; options: {', '.join(x.name for x in tools[tool].scenarios)}")
        return 1
    data[tool] = s.name
    _write_overrides(data)
    print(f"{tool}: forced to {s.name}")
    return 0


def cmd_reset() -> int:
    _write_overrides({})
    print("all scenario overrides cleared")
    return 0


def cmd_cart(action: str) -> int:
    basket = live.Basket(CART_STATE)
    if action == "reset":
        basket.reset()
        print("basket reset to the starting basket")
    elif action == "clear":
        basket.clear()
        print("basket emptied")
    catalog = live.load_catalog(CATALOG)
    for line in basket.lines:
        p = catalog.get(int(line["catalog_item_id"]))
        name = p.name if p else f"unknown item {line['catalog_item_id']}"
        cost = live.line_price(p, line["count"])["total"] if p else 0.0
        print(f"  {line['count']:>3} x {name:<36} AED {cost:>7.2f}   {line['item_uuid']}")
    pr = live.price(basket, catalog)
    if not basket.lines:
        print("  (empty)")
    print(f"  subtotal {pr['subtotal']:.2f} + delivery {pr['delivery']:.2f} + service {pr['service']:.2f}"
          f" = AED {pr['total']:.2f}" + (f" (saving {pr['saving']:.2f})" if pr["saving"] else ""))
    return 0


def check(spec_dir: Path = SPEC_DIR) -> list[str]:
    """FORMAT.md 'Keeping scenarios honest': render every scenario forced, validate against outputSchema."""
    problems: list[str] = []
    for name, tf in sorted(spec.load_all(spec_dir).items()):
        in_schema = tf.definition.get("inputSchema") or {}
        out_schema = tf.definition.get("outputSchema")
        validator = Draft202012Validator(out_schema) if out_schema else None
        base = spec.sample_value(in_schema)
        for s in tf.scenarios:
            where = f"{name} / {s.name}"
            if s.match is not None:
                for key in spec.unknown_match_keys(in_schema, s.match):
                    problems.append(f"{where}: match key {key!r} is not an input")
            if s.is_error:
                continue
            args = spec.overlay(base, s.match) if s.match is not None else base
            try:
                value = json.loads(spec.render(s.template, args))
            except (spec.RenderError, ValueError) as e:
                problems.append(f"{where}: render failed: {e}")
                continue
            if validator:
                for err in validator.iter_errors(value):
                    path = "/".join(str(p) for p in err.absolute_path) or "(root)"
                    problems.append(f"{where}: {path}: {err.message}")
    return problems


def cmd_check() -> int:
    problems = check()
    for p in problems:
        print(p)
    print("ok: every scenario validates" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="careem-mcp")
    sub = p.add_subparsers(dest="cmd", required=True)
    start = sub.add_parser("start", help="start the HTTP server in the background")
    start.add_argument("--live-cart", action="store_true", help="live catalog + editable basket")
    cart = sub.add_parser("cart", help="show the live basket; 'reset' restores the starting basket, 'clear' empties it")
    cart.add_argument("action", nargs="?", choices=["show", "reset", "clear"], default="show")
    sub.add_parser("stop")
    sub.add_parser("status")
    logs = sub.add_parser("logs")
    logs.add_argument("-n", type=int, default=50)
    sc = sub.add_parser("scenarios", help="list scenarios")
    sc.add_argument("tool", nargs="?")
    one = sub.add_parser("scenario", help="force a scenario (omit name to clear)")
    one.add_argument("tool")
    one.add_argument("name", nargs="?")
    sub.add_parser("reset", help="clear all forced scenarios")
    sub.add_parser("check", help="validate every scenario against its output schema")
    a, extra = p.parse_known_args(argv)
    if extra and a.cmd != "start":
        p.error(f"unrecognized arguments: {' '.join(extra)}")
    try:
        if a.cmd == "start":  # any other flags go to the server (e.g. --allowed-host for tunnels)
            return cmd_start((["--live-cart"] if a.live_cart else []) + extra)
        if a.cmd == "cart":
            return cmd_cart(a.action)
        if a.cmd == "stop":
            return cmd_stop()
        if a.cmd == "status":
            return cmd_status()
        if a.cmd == "logs":
            return cmd_logs(a.n)
        if a.cmd == "scenarios":
            return cmd_scenarios(a.tool)
        if a.cmd == "scenario":
            return cmd_scenario(a.tool, a.name)
        if a.cmd == "reset":
            return cmd_reset()
        return cmd_check()
    except spec.SpecError as e:
        print(f"careem-mcp: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
