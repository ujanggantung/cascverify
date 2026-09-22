#!/usr/bin/env python3
"""Probe which 9router models actually work (with retries)."""
import json, os, time, urllib.request, sys

BASE = "http://127.0.0.1:20128/v1/chat/completions"
KEY = os.environ.get("HERMES_CUSTOM_HERMES_API_KEY", "")

CANDIDATES = [
    "openrouter/google/gemma-4-26b-a4b-it:free",
    "openrouter/google/gemma-4-31b-it:free",
    "openrouter/qwen/qwen3-next-80b-a3b-instruct:free",
    "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/cohere/north-mini-code:free",
    "openrouter/poolside/laguna-m.1:free",
    "openrouter/poolside/laguna-xs.2:free",
    "mimo/mimo-v2.5",
    "mimo/mimo-v2.5-pro",
    "mimo/mimo-v2-flash",
    "tokenharbor",
    "bb/gpt-5.4-nano",
    "gcli/grok-4.5-low",
    "tokenrouter/z-ai/glm-5.3-free",
]

def probe(model, attempts=2):
    for a in range(attempts):
        try:
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
                "max_tokens": 10,
            }).encode()
            req = urllib.request.Request(BASE, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {KEY}",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            if "error" in d:
                msg = str(d["error"])[:90]
                if a == attempts - 1:
                    return f"ERR {msg}"
                time.sleep(2); continue
            c = d.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            if c.strip():
                return f"OK '{c.strip()[:20]}'"
            return "EMPTY"
        except Exception as e:
            if a == attempts - 1:
                return f"EXC {str(e)[:70]}"
            time.sleep(2)
    return "UNKNOWN"

working = []
for m in CANDIDATES:
    res = probe(m)
    flag = "✅" if res.startswith("OK") else "❌"
    print(f"{flag} {m:60s} {res}", flush=True)
    if res.startswith("OK"):
        working.append(m)

print("\n=== WORKING MODELS ===")
for m in working:
    print(f"  {m}")
with open(os.path.join(os.path.dirname(__file__), "..", "working_models.json"), "w") as f:
    json.dump(working, f, indent=2)