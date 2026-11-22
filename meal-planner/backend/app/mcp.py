"""Minimal MCP client over Streamable HTTP (JSON-RPC), used by the backend to call careem-mcp."""

from __future__ import annotations

import itertools
import json
import logging
import threading
import time
from typing import Any

import httpx

from . import mcp_log

log = logging.getLogger("meal-planner.mcp")


class MCPError(Exception):
    """The MCP call failed at the protocol or transport level (not a business error)."""


class MCPClient:
    def __init__(self, url: str, timeout: float = 15.0):
        self.url = url
        self.http = httpx.Client(timeout=timeout)
        self.session: str | None = None
        self.ids = itertools.count(1)
        self.lock = threading.Lock()

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["mcp-session-id"] = self.session
            headers["mcp-protocol-version"] = "2025-06-18"
        return self.http.post(self.url, headers=headers, content=json.dumps(payload))

    def _connect(self) -> None:
        self.session = None
        rid = next(self.ids)
        r = self._post({"jsonrpc": "2.0", "id": rid, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "meal-planner", "version": "1.0.0"}}})
        if r.status_code != 200:
            raise MCPError(f"initialize failed: HTTP {r.status_code}")
        self.session = r.headers.get("mcp-session-id")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        rid = next(self.ids)
        r = self._post({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        if r.status_code == 404 and self.session:  # session expired (server restarted)
            raise _Reconnect()
        if r.status_code >= 400:
            raise MCPError(f"{method}: HTTP {r.status_code}")
        if r.headers.get("content-type", "").startswith("application/json"):
            msgs = [r.json()]
        else:
            msgs = [json.loads(l[5:]) for l in r.text.splitlines() if l.startswith("data:")]
        for m in msgs:
            if m.get("id") == rid:
                if "error" in m:
                    raise MCPError(m["error"].get("message", "MCP error"))
                return m["result"]
        raise MCPError(f"{method}: no response")

    def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and return its structured output. Tool-level failures (isError) raise
        MCPError; business failures stay in the returned object's "error" field. Every call is
        recorded for the "Behind the scenes" panel."""
        start = time.perf_counter()
        try:
            out = self._call(tool, args)
        except MCPError as e:
            mcp_log.record(tool, args, None, str(e), (time.perf_counter() - start) * 1000)
            raise
        mcp_log.record(tool, args, out, None, (time.perf_counter() - start) * 1000)
        return out

    def _call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            for attempt in (1, 2):
                try:
                    if self.session is None:
                        self._connect()
                    result = self._request("tools/call", {"name": tool, "arguments": args})
                    break
                except _Reconnect:
                    self.session = None
                    if attempt == 2:
                        raise MCPError("lost the MCP session twice") from None
                except httpx.HTTPError as e:
                    self.session = None
                    raise MCPError(f"Careem service unreachable: {e.__class__.__name__}") from e
        log.info("mcp %s %s", tool, json.dumps(args, separators=(",", ":"))[:300])
        if result.get("isError"):
            text = (result.get("content") or [{}])[0].get("text", "tool error")
            raise MCPError(text)
        sc = result.get("structuredContent")
        if sc is None:
            text = (result.get("content") or [{}])[0].get("text", "{}")
            sc = json.loads(text)
        return sc


class _Reconnect(Exception):
    pass
