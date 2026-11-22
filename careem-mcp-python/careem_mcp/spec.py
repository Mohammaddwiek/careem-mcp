"""Loading tool files, choosing scenarios and rendering response templates (spec/BUILD.md §2-3)."""

from __future__ import annotations

import json
import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DUBAI = timezone(timedelta(hours=4))  # Asia/Dubai has no DST
SECTION_RE = re.compile(r"^## ")
BLOCK_RE = re.compile(r"^```json[ \t]+(match|response|error)[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
TOOL_BLOCK_RE = re.compile(r"^```json[ \t]+tool[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
PLACEHOLDER_RE = re.compile(r"\{\{(.*?)\}\}", re.S)
TIME_RE = re.compile(
    r"^(now|unixms|unix)([+-](?:[0-9.]+(?:ms|s|m|h))+)?"
    r"(?:@((?:[0-9.]+(?:ms|s|m|h))+))?"
    r"(?:\|(date|weekday|hhmm|daylabel))?$"
)
DURATION_PART_RE = re.compile(r"([+-]?)([0-9.]+)(ms|s|m|h)")
UNIT_SECONDS = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class SpecError(Exception):
    """A tool file is invalid. The message names the file (and scenario when relevant)."""


class RenderError(Exception):
    """A template could not be rendered."""


@dataclass
class Scenario:
    name: str
    match: Any | None  # None => default scenario
    template: str
    is_error: bool


@dataclass
class ToolFile:
    path: Path
    tool: str
    definition: dict[str, Any]
    scenarios: list[Scenario] = field(default_factory=list)

    def scenario(self, name: str) -> Scenario | None:
        for s in self.scenarios:
            if s.name.lower() == name.lower():
                return s
        return None


# ---------------------------------------------------------------- parsing


def _frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise SpecError(f"{path}: missing frontmatter")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise SpecError(f"{path}: unterminated frontmatter")
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = re.sub(r"\s+#.*$", "", value).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, text[end + 5 :]


def _sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    for line in body.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and SECTION_RE.match(line):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
    return [(title, "\n".join(lines) + "\n") for title, lines in sections]


def parse_tool_file(path: Path) -> ToolFile:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = _frontmatter(text, path)
    tool = meta.get("tool")
    if not tool:
        raise SpecError(f"{path}: frontmatter has no 'tool'")

    definition: dict[str, Any] | None = None
    scenarios: list[Scenario] = []
    for title, content in _sections(body):
        if title == "Definition":
            m = TOOL_BLOCK_RE.search(content)
            if not m:
                raise SpecError(f"{path}: Definition has no ```json tool block")
            try:
                definition = json.loads(m.group(1))
            except json.JSONDecodeError as e:
                raise SpecError(f"{path}: Definition is not valid JSON: {e}") from e
        elif title.startswith("Scenario:"):
            name = title[len("Scenario:") :].strip()
            where = f"{path}: scenario {name!r}"
            match: Any | None = None
            responses: list[tuple[str, str]] = []
            for kind, block in BLOCK_RE.findall(content):
                if kind == "match":
                    if match is not None:
                        raise SpecError(f"{where}: more than one match block")
                    try:
                        match = json.loads(block)
                    except json.JSONDecodeError as e:
                        raise SpecError(f"{where}: match is not valid JSON: {e}") from e
                else:
                    responses.append((kind, block))
            if len(responses) != 1:
                raise SpecError(f"{where}: needs exactly one response or error block, found {len(responses)}")
            kind, block = responses[0]
            scenarios.append(Scenario(name, match, block, kind == "error"))

    if definition is None:
        raise SpecError(f"{path}: no Definition section")
    if definition.get("name") != tool:
        raise SpecError(f"{path}: Definition name {definition.get('name')!r} != frontmatter tool {tool!r}")
    if not scenarios:
        raise SpecError(f"{path}: no scenarios")
    if not any(s.match is None for s in scenarios):
        raise SpecError(f"{path}: no default scenario (one without a match block)")
    for s in scenarios:
        try:
            json.loads(render(s.template, {}))
        except (RenderError, json.JSONDecodeError) as e:
            raise SpecError(f"{path}: scenario {s.name!r}: template invalid: {e}") from e
    return ToolFile(path, tool, definition, scenarios)


def load_all(spec_dir: Path) -> dict[str, ToolFile]:
    tools: dict[str, ToolFile] = {}
    files = sorted(p for p in (spec_dir / "tools").rglob("*.md") if p.name != "README.md")
    for path in files:
        tf = parse_tool_file(path)
        if tf.tool in tools:
            raise SpecError(f"{path}: duplicate tool {tf.tool!r} (also in {tools[tf.tool].path})")
        tools[tf.tool] = tf
    if not tools:
        raise SpecError(f"{spec_dir / 'tools'}: no tool files found")
    return tools


# ---------------------------------------------------------------- selection


def compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _text(got: Any) -> str:
    return got if isinstance(got, str) else compact(got)


def _json_equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def matches(want: Any, got: Any) -> bool:
    if isinstance(want, dict):
        return isinstance(got, dict) and all(k in got and matches(v, got[k]) for k, v in want.items())
    if isinstance(want, list):
        return isinstance(got, list) and all(any(matches(w, g) for g in got) for w in want)
    if isinstance(want, str):
        if want == "*":
            return got is not None
        if got is None:
            return False
        if want.startswith("~"):
            return want[1:].lower() in _text(got).lower()
        if want.startswith("="):
            return _text(got).lower() == want[1:].lower()
        return _text(got).lower() == want.lower()
    return _json_equal(want, got)


def select(tf: ToolFile, args: dict[str, Any], forced: str | None) -> tuple[Scenario, bool]:
    if forced:
        s = tf.scenario(forced)
        if s is not None:
            return s, True
    for s in tf.scenarios:
        if s.match is not None and matches(s.match, args):
            return s, False
    return next(s for s in tf.scenarios if s.match is None), False


# ---------------------------------------------------------------- rendering


def _duration(text: str) -> float:
    total = 0.0
    sign = 1
    for sgn, num, unit in DURATION_PART_RE.findall(text):
        if sgn:
            sign = -1 if sgn == "-" else 1
        total += sign * float(num) * UNIT_SECONDS[unit]
    return total


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _eval(expr: str, args: dict[str, Any], now: datetime) -> Any:
    expr = expr.strip()
    if expr == "args" or expr.startswith("args."):
        value: Any = args
        for part in expr.split(".")[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
                value = value[int(part)]
            else:
                return None
        return value
    if expr == "uuid":
        return str(uuid.uuid4())
    if expr.startswith("rand:"):
        m = re.fullmatch(r"rand:(\d+)-(\d+)", expr)
        if not m or int(m.group(1)) > int(m.group(2)):
            raise RenderError(f"bad rand expression {expr!r}")
        return random.randint(int(m.group(1)), int(m.group(2)))
    m = TIME_RE.match(expr)
    if not m:
        raise RenderError(f"unknown placeholder {{{{{expr}}}}}")
    base, offset, rounding, fmt = m.groups()
    ts = now.timestamp() + (_duration(offset) if offset else 0)
    if rounding:
        step = _duration(rounding)
        if step <= 0:
            raise RenderError(f"bad rounding in {expr!r}")
        ts = (ts // step) * step
    t = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    if fmt:
        if base != "now":
            raise RenderError(f"format only applies to now: {expr!r}")
        local = t.astimezone(DUBAI)
        if fmt == "date":
            return local.strftime("%Y-%m-%d")
        if fmt == "weekday":
            return WEEKDAYS[local.weekday()]
        if fmt == "hhmm":
            return local.strftime("%H:%M")
        return f"{WEEKDAYS[local.weekday()][:3]}, {_ordinal(local.day)} {MONTHS[local.month - 1]}"
    if base == "unix":
        return int(ts)
    if base == "unixms":
        return int(ts * 1000)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def render(template: str, args: dict[str, Any], now: datetime | None = None) -> str:
    """Replace every {{expr}} in a JSON template; returns JSON text."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    out: list[str] = []
    in_string = False
    i = 0
    n = len(template)
    while i < n:
        if template.startswith("{{", i):
            end = template.find("}}", i + 2)
            if end == -1:
                raise RenderError("unterminated {{")
            value = _eval(template[i + 2 : end], args, now)
            if in_string:
                s = value if isinstance(value, str) else compact(value)
                out.append(json.dumps(s, ensure_ascii=False)[1:-1])
            else:
                out.append(compact(value))
            i = end + 2
            continue
        ch = template[i]
        if ch == "\\" and in_string:
            out.append(template[i : i + 2])
            i += 2
            continue
        if ch == '"':
            in_string = not in_string
        out.append(ch)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------- input defaults


def apply_defaults(schema: dict[str, Any], value: Any) -> Any:
    if not isinstance(value, dict) or not isinstance(schema, dict):
        return value
    for key, sub in (schema.get("properties") or {}).items():
        if not isinstance(sub, dict):
            continue
        if key not in value and "default" in sub:
            value[key] = json.loads(json.dumps(sub["default"]))
        elif key in value:
            apply_defaults(sub, value[key])
    return value


# ---------------------------------------------------------------- honesty check (FORMAT.md)


def _first_type(schema: dict[str, Any]) -> str | None:
    t = schema.get("type")
    if isinstance(t, list):
        return next((x for x in t if x != "null"), None)
    return t


def sample_value(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return "sample"
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    t = _first_type(schema)
    if t is None:
        for key in ("anyOf", "oneOf"):
            if schema.get(key):
                return sample_value(schema[key][0])
        t = "object" if "properties" in schema else "string"
    if t == "string":
        return "sample"
    if t in ("integer", "number"):
        return 1
    if t == "boolean":
        return False
    if t == "array":
        return [sample_value(schema.get("items", {}))]
    if t == "object":
        return {k: sample_value(v) for k, v in (schema.get("properties") or {}).items()}
    return None


def _strip(v: Any) -> Any:
    if isinstance(v, str) and v[:1] in ("~", "="):
        return v[1:]
    return v


def overlay(sample: Any, match: Any) -> Any:
    if isinstance(match, dict):
        base = dict(sample) if isinstance(sample, dict) else {}
        for k, m in match.items():
            base[k] = overlay(base.get(k), m)
        return base
    if isinstance(match, list):
        item = sample[0] if isinstance(sample, list) and sample else None
        return [overlay(item, m) if isinstance(m, dict) else _strip(m) for m in match]
    if match == "*":
        return sample if sample is not None else "sample"
    return _strip(match)


def unknown_match_keys(schema: dict[str, Any], match: Any, prefix: str = "") -> list[str]:
    """Match keys that are not real input properties (only checked where the schema lists properties)."""
    bad: list[str] = []
    if not isinstance(match, dict) or not isinstance(schema, dict):
        return bad
    props = schema.get("properties")
    if props is None:
        return bad
    for k, v in match.items():
        if k not in props:
            bad.append(prefix + k)
            continue
        sub = props[k]
        if isinstance(v, dict):
            bad += unknown_match_keys(sub, v, f"{prefix}{k}.")
        elif isinstance(v, list) and isinstance(sub, dict):
            for el in v:
                bad += unknown_match_keys(sub.get("items", {}), el, f"{prefix}{k}[].")
    return bad
