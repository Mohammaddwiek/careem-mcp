"""Acceptance tests from spec/BUILD.md §7, run against a real server over Streamable HTTP."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from careem_mcp import spec
from careem_mcp.cli import check

PROJECT = Path(__file__).resolve().parent.parent
SPEC = PROJECT / "spec"
HOME = {"latitude": 25.0866, "longitude": 55.1474}
FORBIDDEN = ["mock", "sandbox", "sbx", "fake", "dummy", "example.com"]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RawClient:
    """Minimal JSON-RPC over Streamable HTTP, so tests see exactly what goes over the wire."""

    def __init__(self, url: str):
        self.url = url
        self.http = httpx.Client(timeout=10)
        self.session: str | None = None
        self.next_id = 0

    def _post(self, payload: dict) -> httpx.Response:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["mcp-session-id"] = self.session
            headers["mcp-protocol-version"] = "2025-06-18"
        return self.http.post(self.url, headers=headers, content=json.dumps(payload))

    def request(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        rid = self.next_id
        r = self._post({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        if "mcp-session-id" in r.headers:
            self.session = r.headers["mcp-session-id"]
        if r.headers.get("content-type", "").startswith("application/json"):
            msgs = [r.json()]
        else:
            msgs = [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]
        for m in msgs:
            if m.get("id") == rid:
                return m
        raise AssertionError(f"no response for {method}: {r.status_code} {r.text[:300]}")

    def notify(self, method: str) -> None:
        self._post({"jsonrpc": "2.0", "method": method})

    def call(self, name: str, args: dict) -> dict:
        msg = self.request("tools/call", {"name": name, "arguments": args})
        assert "result" in msg, msg
        return msg["result"]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    overrides = tmp_path_factory.mktemp("run") / "overrides.json"
    overrides.write_text("{}")
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "careem_mcp.server", "--port", str(port), "--overrides", str(overrides)],
        cwd=PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(base + "/health", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError(proc.stderr.read().decode())
    yield {"base": base, "overrides": overrides}
    proc.kill()
    proc.wait()


@pytest.fixture(scope="module")
def client(server):
    c = RawClient(server["base"] + "/mcp")
    init = c.request(
        "initialize",
        {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "acceptance", "version": "1"}},
    )
    c.init_result = init["result"]
    c.notify("notifications/initialized")
    return c


def tool_files() -> dict[str, spec.ToolFile]:
    return spec.load_all(SPEC)


# 1
def test_initialize(client):
    r = client.init_result
    assert r["serverInfo"] == {"name": "careem-mcp-service", "version": "v1.0.0"}
    assert "instructions" not in r
    assert "title" not in r["serverInfo"]
    assert "tools" in r["capabilities"] and "resources" in r["capabilities"]


def test_health(server):
    assert httpx.get(server["base"] + "/health").json() == {"status": "ok", "tools": 42}


# 2
def test_tools_list_matches_definitions(client):
    files = tool_files()
    tools = client.request("tools/list")["result"]["tools"]
    assert len(tools) == len(files) == 42
    for t in tools:
        assert t == files[t["name"]].definition, t["name"]


def test_resources(client):
    res = client.request("resources/list")["result"]["resources"]
    assert [r["uri"] for r in res] == ["ui://careem-mcp-app"]
    assert res[0]["mimeType"] == "text/html;profile=mcp-app"
    assert res[0]["_meta"]["domain"] == "https://careem-mcp-app.pages.dev"
    read = client.request("resources/read", {"uri": "ui://careem-mcp-app"})["result"]["contents"][0]
    assert read["uri"] == "ui://careem-mcp-app"
    assert read["_meta"] == res[0]["_meta"]
    assert "https://careem-mcp-app.pages.dev/assets/index.js" in read["text"]


# 3
def test_menu_by_id(client):
    r = client.call("food_get_restaurant_menu", {"restaurant_id": 30104, **HOME})
    assert r["isError"] is False
    assert r["structuredContent"]["restaurant"]["id"] == 30104
    assert r["structuredContent"]["restaurant"]["name"]["value"] == "Morning Syrniki Café"
    assert json.loads(r["content"][0]["text"]) == r["structuredContent"]


# 4
def test_menu_other_restaurant(client):
    r = client.call("food_get_restaurant_menu", {"restaurant_id": 30101, **HOME})
    assert r["structuredContent"]["restaurant"]["name"]["value"] == "Shawarma Station"


# 5
def test_menu_unknown_restaurant_default(client):
    r = client.call("food_get_restaurant_menu", {"restaurant_id": 1, **HOME})
    assert r["isError"] is False
    assert r["structuredContent"]["error"] == "failed to get restaurant menu: unexpected response status 404"


# 6
def test_menu_invalid_arguments(client):
    r = client.call("food_get_restaurant_menu", {"restaurant_id": "x", **HOME})
    assert r["isError"] is True
    assert r["content"][0]["text"].startswith('validating "arguments"')
    r = client.call("food_get_restaurant_menu", {})
    assert r["isError"] is True


# 7
def test_merchant_search(client):
    r = client.call("food_merchant_search", {"query": "sushi", **HOME})
    assert r["structuredContent"]["restaurants"][0]["id"] == 30102
    r = client.call("food_merchant_search", {"query": "NOPE", **HOME})
    assert r["structuredContent"]["restaurants"] == []
    r = client.call("food_merchant_search", {"query": "sushi", "longitude": 55.1474})
    assert r["isError"] is True


# 8
def test_reverse_geocode(client):
    r = client.call("reverse_geocode", HOME)
    assert r["structuredContent"]["location"]["locationUuid"] == "LOC-50001"
    r = client.call("reverse_geocode", {"latitude": 91, "longitude": 55})
    assert "error" in r["structuredContent"]


# 9
def test_forced_scenario_without_restart(client, server):
    server["overrides"].write_text(json.dumps({"food_get_restaurant_menu": "upstream-unavailable"}))
    try:
        r = client.call("food_get_restaurant_menu", {"restaurant_id": 30104, **HOME})
        assert "error" in r["structuredContent"]
    finally:
        server["overrides"].write_text("{}")
    r = client.call("food_get_restaurant_menu", {"restaurant_id": 30104, **HOME})
    assert r["structuredContent"]["restaurant"]["name"]["value"] == "Morning Syrniki Café"


# 10
def test_unknown_tool(client):
    msg = client.request("tools/call", {"name": "does_not_exist", "arguments": {}})
    assert msg["error"]["code"] == -32602
    assert 'unknown tool "does_not_exist"' in msg["error"]["message"]


# 11
def test_every_scenario_validates_against_output_schema():
    assert check(SPEC) == []


# 12
def test_nothing_observable_hints_at_local_copy(client):
    blobs = [
        json.dumps(client.init_result),
        json.dumps(client.request("tools/list")["result"]),
        json.dumps(client.request("resources/list")["result"]),
        json.dumps(client.request("resources/read", {"uri": "ui://careem-mcp-app"})["result"]),
    ]
    for tf in tool_files().values():
        for s in tf.scenarios:
            blobs.append(spec.render(s.template, {}))
    text = "\n".join(blobs).lower()
    for word in FORBIDDEN:
        assert word not in text, word


# extra: placeholder rendering rules (BUILD.md §3 "Placeholders")
def test_placeholders():
    from datetime import datetime, timezone

    now = datetime(2026, 10, 7, 0, 30, 0, tzinfo=timezone.utc)  # 04:30 in Dubai, a Wednesday
    out = json.loads(
        spec.render(
            '{"a": "id {{args.x}}", "b": {{args.x}}, "c": "{{args.o}}", "d": {{args.missing}},'
            ' "e": "{{now}}", "f": "{{now+1h30m}}", "g": "{{now+2h@20m|hhmm}}", "h": "{{now|date}}",'
            ' "i": "{{now+48h|daylabel}}", "j": {{unix}}, "k": "{{now|weekday}}", "l": "{{args.q}}"}',
            {"x": 5, "o": {"k": 1}, "q": 'he said "hi"'},
            now,
        )
    )
    assert out == {
        "a": "id 5",
        "b": 5,
        "c": '{"k":1}',
        "d": None,
        "e": "2026-10-07T00:30:00Z",
        "f": "2026-10-07T02:00:00Z",
        "g": "06:20",
        "h": "2026-10-07",
        "i": "Fri, 9th Oct",
        "j": int(now.timestamp()),
        "k": "Wednesday",
        "l": 'he said "hi"',
    }
    with pytest.raises(spec.RenderError):
        spec.render('{"x": "{{bogus}}"}', {})


def test_matching_rules():
    m = spec.matches
    assert m({"q": "~pizza"}, {"q": "Big PIZZA place"})
    assert m({"n": "5"}, {"n": 5}) and m({"n": 5}, {"n": 5}) and not m({"n": 5}, {"n": "5"})
    assert m({"p": "*"}, {"p": 0}) and not m({"p": "*"}, {"p": None}) and not m({"p": "*"}, {})
    assert m({"c": "=*"}, {"c": "*"}) and not m({"c": "=*"}, {"c": "x"})
    assert m({"t": ["milk"]}, {"t": ["bread", "Milk"]}) and m({"t": []}, {"t": ["x"]})
    assert m({"loc": {"city": "dubai"}}, {"loc": {"city": "Dubai", "x": 1}})
    assert not m({"b": True}, {"b": 1}) and m({"z": None}, {"z": None}) and not m({"z": None}, {})


def test_output_schema_validator_is_real():
    """Guard against test 11 passing vacuously: a broken response must fail validation."""
    tf = tool_files()["is_grocery_area_serviceable"]
    v = Draft202012Validator(tf.definition["outputSchema"])
    assert list(v.iter_errors({"page": "x"}))  # missing 'serviceable'
