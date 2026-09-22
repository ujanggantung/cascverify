"""CascToolBench — measuring persistent tool hallucinations through agent memory.

Package layout:
- env.py       : ToolEnv (in-process tool sandbox with failure injection + ground truth)
- tasks.py     : task suite generator (T1..T4)
- client.py    : OpenAI-compatible LLM client (urllib, no deps) for 9router
- runner.py    : ReAct agent loop with full trace capture
- verifier.py  : trace annotation / fabrication classification
- metrics.py   : cascade metrics (FR, MCI, CD, CB, RR, TFA)
"""

__version__ = "0.1.0"