from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from route_mini.types import Model


class ErrorKind(StrEnum):
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    PROVIDER_DOWN = "provider_down"
    NETWORK = "network"
    BAD_REQUEST = "bad_request"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProviderError(Exception):
    status_code: int | None = None
    message: str = "provider error"
    network: bool = False

    def __str__(self) -> str:
        code = "network" if self.network else self.status_code
        return f"{code}: {self.message}"


@dataclass(frozen=True, slots=True)
class FallbackDecision:
    kind: ErrorKind
    retry_same: bool
    fall_through: bool
    backoff_ms: int


class FallbackChain:
    def __init__(
        self, max_retries: int = 1, rate_limit_backoff_ms: int = 50, network_backoff_ms: int = 25
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.max_retries = max_retries
        self.rate_limit_backoff_ms = rate_limit_backoff_ms
        self.network_backoff_ms = network_backoff_ms

    def classify(self, error: ProviderError) -> ErrorKind:
        if error.network:
            return ErrorKind.NETWORK
        if error.status_code in {401, 403}:
            return ErrorKind.AUTH
        if error.status_code == 429:
            return ErrorKind.RATE_LIMIT
        if error.status_code is not None and 500 <= error.status_code <= 599:
            return ErrorKind.PROVIDER_DOWN
        if error.status_code is not None and 400 <= error.status_code <= 499:
            return ErrorKind.BAD_REQUEST
        return ErrorKind.UNKNOWN

    def decide(self, error: ProviderError, attempt: int) -> FallbackDecision:
        kind = self.classify(error)
        if kind == ErrorKind.RATE_LIMIT:
            return FallbackDecision(
                kind=kind,
                retry_same=attempt < self.max_retries,
                fall_through=attempt >= self.max_retries,
                backoff_ms=self.rate_limit_backoff_ms,
            )
        if kind == ErrorKind.NETWORK:
            return FallbackDecision(
                kind=kind,
                retry_same=attempt < self.max_retries,
                fall_through=True,
                backoff_ms=self.network_backoff_ms,
            )
        if kind == ErrorKind.PROVIDER_DOWN:
            return FallbackDecision(kind=kind, retry_same=False, fall_through=True, backoff_ms=0)
        if kind in {ErrorKind.AUTH, ErrorKind.BAD_REQUEST}:
            return FallbackDecision(kind=kind, retry_same=False, fall_through=False, backoff_ms=0)
        return FallbackDecision(kind=kind, retry_same=False, fall_through=True, backoff_ms=0)

    def order(
        self, candidates: tuple[Model, ...], primary: Model | None = None
    ) -> tuple[Model, ...]:
        if primary is None or primary not in candidates:
            return candidates
        return (primary, *(candidate for candidate in candidates if candidate != primary))
