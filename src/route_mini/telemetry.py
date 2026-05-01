from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median

from route_mini.decision import AuditDecision


@dataclass(frozen=True, slots=True)
class ProviderRollup:
    provider: str
    total: int
    successes: int
    success_rate: float
    p50_latency_ms: int
    p95_latency_ms: int
    cost_to_date: float


class Telemetry:
    def __init__(self, maxlen: int = 1_000):
        self._decisions: deque[AuditDecision] = deque(maxlen=maxlen)

    def record(self, decision: AuditDecision) -> None:
        self._decisions.append(decision)

    def decisions(self) -> tuple[AuditDecision, ...]:
        return tuple(self._decisions)

    def provider_rollups(self) -> dict[str, ProviderRollup]:
        providers = sorted({decision.selected.provider for decision in self._decisions})
        return {provider: self._rollup(provider) for provider in providers}

    def _rollup(self, provider: str) -> ProviderRollup:
        decisions = [
            decision for decision in self._decisions if decision.selected.provider == provider
        ]
        latencies = [decision.latency_ms for decision in decisions]
        successes = sum(1 for decision in decisions if decision.success)
        return ProviderRollup(
            provider=provider,
            total=len(decisions),
            successes=successes,
            success_rate=successes / len(decisions) if decisions else 0.0,
            p50_latency_ms=_percentile(latencies, 50),
            p95_latency_ms=_percentile(latencies, 95),
            cost_to_date=sum(decision.cost.total for decision in decisions),
        )


def _percentile(values: Iterable[int], percentile: int) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    if percentile == 50:
        return int(median(ordered))
    index = min(len(ordered) - 1, round((percentile / 100) * (len(ordered) - 1)))
    return ordered[index]
