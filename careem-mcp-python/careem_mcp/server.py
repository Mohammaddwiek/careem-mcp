"""careem-mcp local server: answers tools/call from the scenario files in spec/ (spec/BUILD.md)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import anyio
import mcp_types as types
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from mcp.server.lowlevel.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from . import spec

PROJECT_DIR = Path(__file__).resolve().parent.parent
WIDGET_URI = "ui://careem-mcp-app"
log = logging.getLogger("careem-mcp")


def widget_meta(domain: str) -> dict[str, Any]:
    return {
        "ui": {
            "resourceUri": WIDGET_URI,
            "csp": {
                "connectDomains": [domain],
                "resourceDomains": [
                    domain,
                    "https://careem.s3.eu-west-1.amazonaws.com",
                    "https://d1a3f4spazzrp4.cloudfront.net",
                    "https://careem-catalog-media.media.careem.com",
                    "https://partner-mot-prod.media.careem.com",
                ],
                "frameDomains": [],
                "baseUriDomains": [],
            },
        },
        "prefersBorder": False,
        "domain": domain,
        "annotations": {"ttlMs": 60000, "destructiveHint": False, "openWorldHint": False, "readOnlyHint": True},
    }


def widget_html(domain: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<meta name="color-scheme" content="light dark">\n'
        "<title>Careem MCP App</title>\n"
        f'<link rel="stylesheet" href="{domain}/assets/index.css">\n'
        "</head>\n"
        "<body>\n"
        '<div id="root"></div>\n'
        f'<script type="module" src="{domain}/assets/index.js"></script>\n'
        "</body>\n"
        "</html>\n"
    )


def read_overrides(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str)} if isinstance(data, dict) else {}


def _error_result(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)


class CareemMCP:
    def __init__(self, cfg: argparse.Namespace):
        self.cfg = cfg
        self.spec_dir = Path(cfg.spec_dir)
        self.overrides_path = Path(cfg.overrides)
        self.tools = spec.load_all(self.spec_dir)  # fail fast on any invalid file
        self.paths = {name: tf.path for name, tf in self.tools.items()}
        self.validators = {
            name: Draft202012Validator(tf.definition.get("inputSchema") or {"type": "object"})
            for name, tf in self.tools.items()
        }
        self.tool_list = [self._advertised(tf.definition) for _, tf in sorted(self.tools.items())]
        self.server: Server[Any] = Server(
            cfg.server_name,
            version=cfg.server_version,
            on_list_tools=self.list_tools,
            on_call_tool=self.call_tool,
            on_list_resources=self.list_resources if not cfg.no_meta else None,
            on_read_resource=self.read_resource if not cfg.no_meta else None,
        )

    # ------------------------------------------------------------ tools

    def _advertised(self, definition: dict[str, Any]) -> types.Tool:
        d = dict(definition)
        if self.cfg.no_output_schema:
            d.pop("outputSchema", None)
        if self.cfg.no_meta:
            d.pop("_meta", None)
        return types.Tool.model_validate(d)

    async def list_tools(self, ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=self.tool_list)

    async def call_tool(self, ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        name = params.name
        if name not in self.tools:
            raise MCPError(code=types.INVALID_PARAMS, message=f'unknown tool "{name}"')
        args: dict[str, Any] = dict(params.arguments or {})
        schema = self.tools[name].definition.get("inputSchema") or {}
        spec.apply_defaults(schema, args)
        err = best_match(self.validators[name].iter_errors(args))
        if err is not None:
            log.info("%s -> invalid arguments %s: %s", name, spec.compact(args), err.message)
            return _error_result(f'validating "arguments": {err.message}')

        try:
            tf = spec.parse_tool_file(self.paths[name])
        except (OSError, spec.SpecError) as e:
            log.error("%s -> parse error: %s", name, e)
            return _error_result("internal server error")

        forced = read_overrides(self.overrides_path).get(name)
        scenario, was_forced = spec.select(tf, args, forced)
        try:
            value = json.loads(spec.render(scenario.template, args))
        except (spec.RenderError, ValueError) as e:
            log.error("%s -> scenario %r render error: %s", name, scenario.name, e)
            return _error_result("internal server error")

        log.info(
            "%s -> %s%s %s", name, scenario.name, " (forced)" if was_forced else "", spec.compact(args)
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=spec.compact(value))],
            structured_content=value if isinstance(value, dict) else None,
            is_error=scenario.is_error,
        )

    # ------------------------------------------------------------ resources

    async def list_resources(self, ctx: Any, params: Any) -> types.ListResourcesResult:
        return types.ListResourcesResult(
            resources=[
                types.Resource.model_validate(
                    {
                        "uri": WIDGET_URI,
                        "name": WIDGET_URI,
                        "description": "Careem Widget",
                        "mimeType": "text/html;profile=mcp-app",
                        "_meta": widget_meta(self.cfg.widget_domain),
                    }
                )
            ]
        )

    async def read_resource(self, ctx: Any, params: types.ReadResourceRequestParams) -> types.ReadResourceResult:
        if str(params.uri) != WIDGET_URI:
            raise MCPError(code=types.INVALID_PARAMS, message=f"resource not found: {params.uri}")
        return types.ReadResourceResult(
            contents=[
                types.TextResourceContents.model_validate(
                    {
                        "uri": WIDGET_URI,
                        "mimeType": "text/html;profile=mcp-app",
                        "text": widget_html(self.cfg.widget_domain),
                        "_meta": widget_meta(self.cfg.widget_domain),
                    }
                )
            ]
        )

    def init_options(self) -> Any:
        return self.server.create_initialization_options(
            NotificationOptions(tools_changed=True, resources_changed=True)
        )

    # ------------------------------------------------------------ transports

    def http_app(self) -> Any:
        sse = SseServerTransport("/messages/")

        async def handle_sse(request: Request) -> Response:
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await self.server.run(streams[0], streams[1], self.init_options())
            return Response()

        async def health(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok", "tools": len(self.tools)})

        hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*", *self.cfg.allowed_host]
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
            + [f"https://{h}" for h in self.cfg.allowed_host],
        )
        app = self.server.streamable_http_app(
            streamable_http_path="/mcp",
            host=self.cfg.host,
            transport_security=security,
            custom_starlette_routes=[
                Route("/health", health, methods=["GET"]),
                Route("/sse", handle_sse, methods=["GET"]),
            ],
        )
        app.router.routes.append(Mount("/messages/", app=sse.handle_post_message))
        return app

    async def run_stdio(self) -> None:
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read, write):
            await self.server.run(read, write, self.init_options())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="careem-mcp", description="Local careem-mcp server")
    env = os.environ.get
    p.add_argument("--host", default=env("CAREEM_MCP_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(env("CAREEM_MCP_PORT", "8787")))
    p.add_argument("--stdio", action="store_true", help="serve MCP over stdio instead of HTTP")
    p.add_argument("--spec-dir", default=env("CAREEM_MCP_SPEC_DIR", str(PROJECT_DIR / "spec")))
    p.add_argument("--overrides", default=env("CAREEM_MCP_OVERRIDES", str(PROJECT_DIR / ".run" / "overrides.json")))
    p.add_argument("--server-name", default=env("CAREEM_MCP_SERVER_NAME", "careem-mcp-service"))
    p.add_argument("--server-version", default=env("CAREEM_MCP_SERVER_VERSION", "v1.0.0"))
    p.add_argument("--widget-domain", default=env("CAREEM_MCP_WIDGET_DOMAIN", "https://careem-mcp-app.pages.dev"))
    p.add_argument("--allowed-host", action="append", default=[], help="extra Host header to accept (tunnels)")
    p.add_argument("--no-output-schema", action="store_true", help="drop outputSchema from tools/list")
    p.add_argument("--no-meta", action="store_true", help="drop _meta and the widget resource")
    return p


def main(argv: list[str] | None = None) -> None:
    cfg = build_parser().parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(message)s")
    for noisy in ("mcp", "httpx", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    try:
        app = CareemMCP(cfg)
    except spec.SpecError as e:
        print(f"careem-mcp: {e}", file=sys.stderr)
        sys.exit(1)
    if cfg.stdio:
        anyio.run(app.run_stdio)
        return
    import uvicorn

    log.info("careem-mcp: %d tools, listening on http://%s:%d/mcp", len(app.tools), cfg.host, cfg.port)
    uvicorn.run(app.http_app(), host=cfg.host, port=cfg.port, log_level="warning")


if __name__ == "__main__":
    main()
