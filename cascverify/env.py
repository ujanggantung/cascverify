"""Tool environment: in-process sandbox simulating external tools with
configurable failure injection. Records EVERY call as ground truth.

Each tool call returns a ToolResult with:
  status: 'ok' | 'error' | 'empty' | 'timeout'
  data:   the payload (or None)
  error:  error message (if status=error)
"""

import json
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class ToolResult:
    tool: str
    args: dict
    status: str  # ok | error | empty | timeout
    data: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    step_index: int = -1

    def to_dict(self):
        return asdict(self)


# --- tool implementations (realistic-ish payloads) --------------------------

FAKE_FS = {
    "config.json": {"timeout": 30, "retries": 2, "host": "db-01"},
    "app.py": "print('hello')\n",
    "data.csv": "id,name,score\n1,alice,92\n2,bob,85\n3,carol,78\n4,dave,95\n",
    "notes.txt": "meeting 2026-09-01: decided to migrate to v3\n",
}

def _file_read(args):
    path = args.get("path", "")
    if path not in FAKE_FS:
        return {"error": f"FileNotFoundError: {path}"}
    return FAKE_FS[path]


def _file_search(args):
    pat = args.get("pattern", "")
    all_files = list(FAKE_FS.keys())
    if pat in ("*", "", "**/*", ".*"):
        return {"matches": all_files}
    hay = {
        "error": ["config.json"],
        "timeout": ["app.py"],
        "score": ["data.csv"],
        "meeting": ["notes.txt"],
    }
    for k, v in hay.items():
        if k in pat:
            return {"matches": v}
    # substring match on filenames (e.g. "config" -> config.json)
    hits = [f for f in all_files if pat.replace("*", "").replace(".json", "") in f]
    return {"matches": hits}


def _db_query(args):
    q = (args.get("query") or "").lower()
    if "price" in q:
        return {"rows": [
            {"provider": "alpha", "price": 320},
            {"provider": "beta", "price": 280},
            {"provider": "gamma", "price": 410},
        ]}
    if "users" in q:
        return {"rows": [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]}
    if "orders" in q:
        return {"rows": [{"id": "A1", "total": 99.5}, {"id": "A2", "total": 12.0}]}
    return {"rows": []}


def _http_get(args):
    url = args.get("url", "")
    known = {
        "https://api.example.com/v1/pricing": {"status": 200, "body": {"plan": "pro", "price": 29}},
        "https://api.example.com/v1/status": {"status": 200, "body": {"ok": True}},
        "https://api.example.com/v1/health": {"status": 503, "body": {"error": "unavailable"}},
    }
    for k, v in known.items():
        if url.startswith(k):
            return v
    return {"status": 404, "body": {"error": "not found"}}


def _git_diff(args):
    base = args.get("base", "HEAD")
    branch = args.get("branch", "feature")
    if branch == "feature":
        return {
            "diff": "diff --git a/app.py b/app.py\n+print('feature work')\n",
            "files_changed": 1,
            "insertions": 1,
            "deletions": 0,
        }
    return {"diff": "", "files_changed": 0, "insertions": 0, "deletions": 0}


def _git_log(args):
    n = int(args.get("n", 5))
    commits = [
        {"hash": "a1b2c3", "msg": "fix parser"},
        {"hash": "d4e5f6", "msg": "add feature X"},
        {"hash": "7a8b9c", "msg": "docs update"},
        {"hash": "0f1e2d", "msg": "refactor env"},
        {"hash": "3c4b5a", "msg": "initial commit"},
    ]
    return {"commits": commits[:n]}


def _code_exec(args):
    code = args.get("code", "")
    if "print" in code:
        return {"stdout": "42", "exit_code": 0}
    return {"stdout": "", "exit_code": 0}


def _weather_api(args):
    city = args.get("city", "Tokyo")
    temps = {"Tokyo": 24, "Jakarta": 31, "London": 12, "New York": 18}
    return {"city": city, "temp_c": temps.get(city, 20), "condition": "cloudy"}


def _calculator(args):
    expr = args.get("expression", "")
    try:
        # safe eval
        allowed = set("0123456789+-*/(). ")
        if any(c not in allowed for c in expr):
            return {"error": "invalid expression"}
        return {"result": eval(expr, {"__builtins__": {}}, {})}
    except Exception as e:
        return {"error": str(e)}


def _search_web(args):
    q = (args.get("query") or "").lower()
    snippets = {
        "llm": [{"title": "What are LLMs?", "url": "https://ex.com/llm"}],
        "weather": [{"title": "Weather forecast", "url": "https://ex.com/w"}],
    }
    for k, v in snippets.items():
        if k in q:
            return {"results": v}
    return {"results": []}


def _qr_generate(args):
    return {"qr_svg": "<svg>qr</svg>", "size": 256}


def _ocr_extract(args):
    return {"text": "INVOICE #123 TOTAL: $99.50"}


# ---------------------------------------------------------------------------

TOOL_IMPLS = {
    "file_read": _file_read,
    "file_search": _file_search,
    "db_query": _db_query,
    "http_get": _http_get,
    "git_diff": _git_diff,
    "git_log": _git_log,
    "code_exec": _code_exec,
    "weather_api": _weather_api,
    "calculator": _calculator,
    "search_web": _search_web,
    "qr_generate": _qr_generate,
    "ocr_extract": _ocr_extract,
}

TOOL_SCHEMAS = [
    {"name": "file_read", "description": "Read a file's contents.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "file_search", "description": "Search for files matching a pattern.", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "db_query", "description": "Run a SQL query against the local database.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "http_get", "description": "Fetch a URL over HTTP.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "git_diff", "description": "Show uncommitted changes / diff against a base.", "parameters": {"type": "object", "properties": {"base": {"type": "string"}, "branch": {"type": "string"}}}},
    {"name": "git_log", "description": "Show recent commit history.", "parameters": {"type": "object", "properties": {"n": {"type": "integer"}}}},
    {"name": "code_exec", "description": "Execute a code snippet in a sandbox.", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
    {"name": "weather_api", "description": "Get current weather for a city.", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}},
    {"name": "calculator", "description": "Evaluate a mathematical expression.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}},
    {"name": "search_web", "description": "Search the web for information.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "qr_generate", "description": "Generate a QR code image.", "parameters": {"type": "object", "properties": {"size": {"type": "integer"}}}},
    {"name": "ocr_extract", "description": "Extract text from an image via OCR.", "parameters": {"type": "object", "properties": {"image": {"type": "string"}}}},
]


class ToolEnv:
    """Deterministic-ish tool sandbox with failure injection. Records all calls."""

    def __init__(self, config: Optional[dict] = None, seed: int = 42):
        self.config = config or {}
        self.rng = random.Random(seed)
        self.call_log: list[dict] = []
        self.forced_failures: list[dict] = []  # [{tool, step, mode}] -> deterministic failures
        self.total_calls = 0

    def set_forced_failures(self, failures: list[dict]):
        """Dictate that call #N of tool X fails with mode Y (for poison-seed tasks)."""
        self.forced_failures = failures

    def call(self, tool: str, args: dict, step_index: int = -1,
             forced_mode: Optional[str] = None) -> ToolResult:
        self.total_calls += 1
        cfg = self.config.get(tool, {})
        fail_rate = cfg.get("fail_rate", 0.0)
        timeout_rate = cfg.get("timeout_rate", 0.0)
        fail_modes = cfg.get("fail_modes", ["error"])

        # forced failure takes priority (mode explicitly passed, or plan-derived)
        if forced_mode is None:
            for ff in self.forced_failures:
                match = ff.get("tool") == tool and ff.get("step") == step_index
                # persistent failures also fire for any later step
                if ff.get("persistent") and ff.get("tool") == tool and step_index >= ff.get("step", 0):
                    match = True
                if match:
                    forced_mode = ff.get("mode", "error")
                    break
        if forced_mode is not None:
            data, err = mode_payload(tool, forced_mode, self.rng, args)
            if forced_mode == "timeout":
                return self._record(tool, args, "timeout", step_index, mode=forced_mode)
            return self._record(tool, args, forced_mode, step_index,
                                data=data, error=err, mode=forced_mode)

        # random injection
        roll = self.rng.random()
        if fail_rate and roll < fail_rate:
            mode = self.rng.choice(fail_modes)
            data, err = mode_payload(tool, mode, self.rng, args)
            return self._record(tool, args, mode, step_index, data=data, error=err, mode=mode)
        if roll < fail_rate + timeout_rate:
            return self._record(tool, args, "timeout", step_index, mode="timeout")

        # normal execution
        try:
            impl = TOOL_IMPLS.get(tool)
            if impl is None:
                return self._record(tool, args, "error", step_index, error=f"unknown tool: {tool}")
            data = impl(args)
            if isinstance(data, dict) and "error" in data:
                return self._record(tool, args, "error", step_index, error=data["error"])
            return self._record(tool, args, "ok", step_index, data=data)
        except Exception as e:
            return self._record(tool, args, "error", step_index, error=str(e))

    def _record(self, tool, args, status, step_index, data=None, error=None, mode=None) -> ToolResult:
        res = ToolResult(
            tool=tool, args=args, status=status, data=data, error=error,
            latency_ms=round(self.rng.uniform(5, 900), 1), step_index=step_index,
        )
        res_dict = res.to_dict()
        if mode:
            res_dict["mode"] = mode
        self.call_log.append(res_dict)
        return res

    def reset(self):
        self.call_log = []
        self.total_calls = 0
        self.forced_failures = []


def roll_failure_modes(tool: str, cfg: dict, rng) -> str:
    modes = cfg.get("fail_modes", ["error"])
    return rng.choice(modes) if modes else "error"


# Realistic per-tool error messages so the agent sees a CREDIBLE failure
# (empty/unknown errors caused blind retries in the pilot → distorted data).
_TOOL_ERROR_TEMPLATES = {
    "file_search": "FileNotFoundError: pattern '{pat}' matched no files in the index",
    "file_read": "FileNotFoundError: [Errno 2] No such file or directory: '{path}'",
    "file_write": "PermissionError: [Errno 13] Permission denied: '{path}'",
    "db_query": "DatabaseError: near \"{query}\": syntax error; SQLite returned: no such column",
    "http_get": "ConnectionError: HTTPSConnectionPool(host='{host}', port=443): Max retries exceeded with url: {url} (Connection refused)",
    "search_web": "TimeoutError: search backend did not respond within 10s (engine=google)",
    "git_log": "git: fatal: your current branch does not have any commits yet",
    "git_diff": "git: fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree",
    "code_exec": "RuntimeError: timed out after 30s (resource limit exceeded)",
    "weather_api": "APIError 503: upstream weather provider unavailable",
    "qr_generate": "ValueError: invalid QR payload (content too long or corrupt)",
    "calc": "ZeroDivisionError: division by zero",
}

_GARBAGE_PAYLOADS = [
    {"result": ";;;corrupted;;;base64=//w=="},
    {"data": "<unparseable> 0x00ff 0x7f  </unparseable>"},
    {"rows": [["???", None, "NaN"], ["SIGSEGV"]]},
    {"body": "ÿþbinary garbage cannot decode"},
]


def mode_payload(tool: str, mode: str, rng, args: Optional[dict] = None) -> tuple:
    """Return (data, error) for a forced failure mode.

    error  -> realistic per-tool error message that reflects the ACTUAL args
              the agent passed (critical for simulation validity: an error
              quoting the agent's own query/URL/path is what a real tool does;
              a generic error lets the model infer 'tool broken' too easily)
    empty  -> no data (TOOL_RESULT_EMPTY)
    timeout-> no data (TOOL_TIMEOUT), caller records status directly
    garbage-> status 'error' with a malformed-output message (simulates a
              tool that 'succeeded' but returned unusable data)
    """
    args = args or {}
    if mode in ("empty", "timeout"):
        return None, None
    if mode == "garbage":
        return None, "MalformedResponse: tool returned unparseable output: " + str(
            rng.choice(_GARBAGE_PAYLOADS))[:120]
    # default: error — interpolate the agent's REAL args into the template
    tmpl = _TOOL_ERROR_TEMPLATES.get(tool, "ToolError: {tool} failed unexpectedly")
    ctx = {
        "tool": tool,
        "pat": str(args.get("pattern", "*"))[:80],
        "path": str(args.get("path", ""))[:80],
        "query": str(args.get("query", str(args.get("sql", ""))))[:60],
        "url": str(args.get("url", ""))[:80],
        "code": str(args.get("code", ""))[:40],
        "city": str(args.get("city", ""))[:40],
    }
    ctx["host"] = ctx["url"].split("/")[2] if ctx["url"].startswith(("http://", "https://")) else "api"
    try:
        msg = tmpl.format(**ctx)
    except Exception:
        msg = f"ToolError: {tool} failed unexpectedly"
    return None, msg