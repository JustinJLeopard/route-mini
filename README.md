# route-mini

[![CI](https://github.com/JustinJLeopard/route-mini/actions/workflows/ci.yml/badge.svg)](https://github.com/JustinJLeopard/route-mini/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Minimal reference for multi-provider LLM routing with fallback, budget, latency targets, and decision logging.

Motivation: today's Opus-502 incident on a major provider is a normal production shape. A request should pick the best eligible model, fall through when the primary is down, and leave an audit trail of what happened.

`route-mini` is part of the Delegate & Orchestrate public substrate family:
small, inspectable references for the parts an agent fleet needs before it can
be trusted with repeated work.

## What It Proves

- Provider fallback is policy, not a rescue branch hidden in application code.
- Budget and latency targets can participate in routing before a request runs.
- Every selection leaves a decision record: eligible models, attempted providers,
  fallback source, cost estimate, latency, and final reason.
- Tests use deterministic providers, so routing behavior is auditable without
  making live network calls.

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

## Related

- [JustAi](https://github.com/JustinJLeopard/JustAi) — orchestration control plane.
- [safe-mini](https://github.com/JustinJLeopard/safe-mini) — safe local execution substrate.
- [memory-mini](https://github.com/JustinJLeopard/memory-mini) — durable agent memory reference.
