"""OpenAI-compatible client (urllib only, no deps). Talks to 9router on localhost:20128.

Handles: streaming (SSE), reasoning models (reasoning_content field), tool_call format.
Records actual model name per response (9router combos route dynamically).
"""

import json
import os
import urllib.request
import urllib.error
from typing import Optional


def _parse_sse(raw: str) -> dict:
    """Parse SSE stream -> single merged JSON dict."""
    merged = {}
    content_parts = []
    reasoning_parts = []
    tool_calls = {}
    model = ""
    usage = {}
    finish_reason = None

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(":") or line == "data: [DONE]":
            continue
        if not line.startswith("data: "):
            continue
        try:
            d = json.loads(line[6:])
        except json.JSONDecodeError:
            continue

        model = d.get("model", model)
        if d.get("usage"):
            usage = d["usage"]

        for choice in d.get("choices", []):
            finish_reason = choice.get("finish_reason") or finish_reason
            msg = choice.get("delta") or choice.get("message") or {}

            if msg.get("content"):
                content_parts.append(msg["content"])
            if msg.get("reasoning_content"):
                reasoning_parts.append(msg["reasoning_content"])

            for tc in msg.get("tool_calls") or []:
                idx = tc.get("index", 0)
                if idx not in tool_calls:
                    tool_calls[idx] = {"id": tc.get("id", ""), "type": "function",
                                       "function": {"name": "", "arguments": ""}}
                fn = tc.get("function") or {}
                if fn.get("name"):
                    tool_calls[idx]["function"]["name"] = fn["name"]
                if fn.get("arguments"):
                    tool_calls[idx]["function"]["arguments"] += fn["arguments"]

    return {
        "model": model,
        "content": "".join(content_parts),
        "reasoning_content": "".join(reasoning_parts),
        "tool_calls": list(tool_calls.values()),
        "finish_reason": finish_reason,
        "usage": usage,
    }


def _parse_body(raw: str) -> dict:
    """Handle all response shapes:
    1. pure JSON
    2. pure JSON + trailing 'data: [DONE]' (9router style)
    3. full SSE stream (many 'data: {...}' lines)
    """
    raw = raw.strip()

    # Case 1/2: starts with '{' -> decode first JSON object (tolerant of trailing junk)
    if raw.startswith("{"):
        try:
            d, _ = json.JSONDecoder().raw_decode(raw)
        except json.JSONDecodeError:
            d = None
        if isinstance(d, dict) and "choices" in d:
            d.pop("_manifest", None)  # C2PA junk from some providers
            try:
                choice = d["choices"][0]
                msg = choice.get("message", {}) or {}
                tc_list = msg.get("tool_calls") or []
                norm_tc = []
                for tc in tc_list:
                    fn = tc.get("function", {}) or {}
                    norm_tc.append({"id": tc.get("id", ""), "type": "function",
                                    "function": {"name": fn.get("name", ""),
                                                 "arguments": fn.get("arguments", "") or ""}})
                return {
                    "model": d.get("model", ""),
                    "content": (msg.get("content") or "").strip(),
                    "reasoning_content": msg.get("reasoning_content") or "",
                    "tool_calls": norm_tc,
                    "finish_reason": choice.get("finish_reason"),
                    "usage": d.get("usage", {}),
                }
            except (IndexError, KeyError):
                pass

    # Case 3: SSE stream
    if "data: " in raw:
        return _parse_sse(raw)

    return {"model": "", "content": "", "reasoning_content": "", "tool_calls": [],
            "finish_reason": None, "usage": {}}


class LLMClient:
    """Thin wrapper around OpenAI-compatible chat completions."""

    def __init__(self, base_url: str = "http://127.0.0.1:20128/v1",
                 api_key: Optional[str] = None, model: str = "tokenharbor",
                 timeout_s: int = 180, max_retries: int = 4,
                 backoff_base: float = 5.0, timeout_budget_s: int = 500):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("HERMES_CUSTOM_HERMES_API_KEY", "")
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout_budget_s = timeout_budget_s
        self.call_count = 0
        self.total_tokens = 0
        self.retry_count = 0

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None,
             max_tokens: int = 1500, temperature: float = 0.3) -> dict:
        """Send chat completion request with retry + exponential backoff.
        Returns parsed dict. Distinguishes hard errors (auth/400) from transient."""
        import time as _time

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
        data = json.dumps(payload).encode("utf-8")

        last_err = ""
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                    raw = r.read().decode()
                self.call_count += 1
                raw = strip_manifest(raw)
                result = _parse_body(raw)
                self.total_tokens += result.get("usage", {}).get("total_tokens", 0)
                return result
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:200]
                # 401/403/400 are permanent -> fail fast
                if e.code in (400, 401, 403):
                    return {"model": self.model, "content": "", "reasoning_content": "",
                            "tool_calls": [], "finish_reason": None, "usage": {},
                            "error": f"HTTP {e.code}: {body}"}
                last_err = f"HTTP {e.code}: {body}"
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = str(e)

            self.retry_count += 1
            if attempt < self.max_retries - 1:
                # backoff with jitter to avoid thundering herd
                delay = self.backoff_base * (2 ** attempt) + (attempt * 2.3)
                _time.sleep(min(delay, 60))

        return {"model": self.model, "content": "", "reasoning_content": "",
                "tool_calls": [], "finish_reason": None, "usage": {},
                "error": f"exhausted retries: {last_err}"}

    def summarize_usage(self) -> dict:
        return {"api_calls": self.call_count, "total_tokens": self.total_tokens,
                "retries": self.retry_count}


def strip_manifest(raw: str) -> str:
    """Remove C2PA _manifest blocks some providers inject into responses."""
    try:
        d = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    if isinstance(d, dict) and "_manifest" in d:
        d.pop("_manifest", None)
        return json.dumps(d, ensure_ascii=False)
    return raw