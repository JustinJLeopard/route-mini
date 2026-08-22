# route-mini

[![CI](https://github.com/JustinJLeopard/route-mini/actions/workflows/ci.yml/badge.svg)](https://github.com/JustinJLeopard/route-mini/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Minimal reference for multi-provider LLM routing with fallback, budget, latency targets, and decision logging.

Motivation: today's Opus-502 incident on a major provider is a normal production shape. A request should pick the best eligible model, fall through when the primary is down, and leave an audit trail of what happened.

`route-mini` is part of the Delegate & Orchestrate public substrate family:
small, inspectable references for the parts an agent fleet needs before it can
be trusted with repeated work.

## What to Inspect

- [`policy.py`](src/route_mini/policy.py) orders or filters declared model
  capabilities by preference, estimated cost, or p50 latency; policies can be
  composed.
- [`fallback.py`](src/route_mini/fallback.py) classifies provider errors and
  decides when to retry, fall through, or stop.
- [`decision.py`](src/route_mini/decision.py) and
  [`telemetry.py`](src/route_mini/telemetry.py) record selections, attempts,
  outcomes, latency, and cost.
- Tests and [`examples/opus_down_demo.py`](examples/opus_down_demo.py) use
  deterministic `ScriptedProvider` instances. The core package supplies
  provider-agnostic routing primitives and makes no live provider calls.

## Install

`route-mini` is not published on PyPI. Install version `0.1.0` from the exact
Git revision used to verify this README:

```bash
python -m pip install \
  "route-mini @ git+https://github.com/JustinJLeopard/route-mini.git@826e79a7f59779853fa2845c2736bfdfa59a6ef6"
```

For local development:

```bash
git clone https://github.com/JustinJLeopard/route-mini.git
cd route-mini
python -m pip install -e ".[dev]"
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
