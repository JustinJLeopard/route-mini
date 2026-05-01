from __future__ import annotations

from abc import ABC, abstractmethod

from route_mini.providers import ModelCapabilities
from route_mini.types import Request


class Policy(ABC):
    @abstractmethod
    def apply(
        self, candidates: tuple[ModelCapabilities, ...], request: Request
    ) -> tuple[ModelCapabilities, ...]:
        raise NotImplementedError

    def then(self, next_policy: Policy) -> Policy:
        return CompositePolicy((self, next_policy))


class CompositePolicy(Policy):
    def __init__(self, policies: tuple[Policy, ...]):
        self.policies = policies

    def apply(
        self, candidates: tuple[ModelCapabilities, ...], request: Request
    ) -> tuple[ModelCapabilities, ...]:
        remaining = candidates
        for policy in self.policies:
            remaining = policy.apply(remaining, request)
        return remaining


class CheapestPolicy(Policy):
    def apply(
        self, candidates: tuple[ModelCapabilities, ...], request: Request
    ) -> tuple[ModelCapabilities, ...]:
        return tuple(
            sorted(candidates, key=lambda candidate: candidate.estimate_cost(request).total)
        )


class FastestPolicy(Policy):
    def apply(
        self, candidates: tuple[ModelCapabilities, ...], request: Request
    ) -> tuple[ModelCapabilities, ...]:
        return tuple(sorted(candidates, key=lambda candidate: candidate.latency_p50_ms))


class PreferListPolicy(Policy):
    def __init__(self, preferred: tuple[str, ...]):
        self.preferred = preferred

    def apply(
        self, candidates: tuple[ModelCapabilities, ...], request: Request
    ) -> tuple[ModelCapabilities, ...]:
        rank = {name: index for index, name in enumerate(self.preferred)}
        fallback = len(rank)
        return tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    rank.get(candidate.model.key, rank.get(candidate.model.provider, fallback)),
                    candidate.model.key,
                ),
            )
        )


class BudgetCapPolicy(Policy):
    def __init__(self, max_cost: float):
        self.max_cost = max_cost

    def apply(
        self, candidates: tuple[ModelCapabilities, ...], request: Request
    ) -> tuple[ModelCapabilities, ...]:
        return tuple(
            candidate
            for candidate in candidates
            if candidate.estimate_cost(request).total <= self.max_cost
        )


class LatencyCapPolicy(Policy):
    def __init__(self, max_p50_ms: int):
        self.max_p50_ms = max_p50_ms

    def apply(
        self, candidates: tuple[ModelCapabilities, ...], request: Request
    ) -> tuple[ModelCapabilities, ...]:
        return tuple(
            candidate for candidate in candidates if candidate.latency_p50_ms <= self.max_p50_ms
        )
