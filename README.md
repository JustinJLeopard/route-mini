# route-mini

[![CI](https://github.com/JustinJLeopard/route-mini/actions/workflows/ci.yml/badge.svg)](https://github.com/JustinJLeopard/route-mini/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Minimal reference for multi-provider LLM routing with fallback, budget, latency targets, and decision logging.

Motivation: today's Opus-502 incident on a major provider is a normal production shape. A request should pick the best eligible model, fall through when the primary is down, and leave an audit trail of what happened.

## Install

```bash
pip install route-mini
```

For local development:

```bash
pip install -e ".[dev]"
```

## 30-Second Example

```bash
python examples/opus_down_demo.py
```

Output:

```text
selected=major-provider-backup:sonnet
reason=fallback-selected
fallback_from=['major-provider:opus']
attempts=2
text=fallback response
```

Core code makes no network calls. Providers are abstract, and tests use deterministic in-memory scripts.

## Docs

- [Usage](docs/USAGE.md)
- [Policies](docs/POLICIES.md)
- [Fallback](docs/FALLBACK.md)
