from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, slots=True)
class Provider:
    name: str


@dataclass(frozen=True, slots=True)
class Cost:
    input: float = 0.0
    output: float = 0.0

    @property
    def total(self) -> float:
        return self.input + self.output


@dataclass(frozen=True, slots=True)
class Model:
    provider: str
    name: str

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.name}"


@dataclass(frozen=True, slots=True)
class Request:
    prompt: str
    max_tokens: int
    input_tokens: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def estimated_input_tokens(self) -> int:
        if self.input_tokens is not None:
            return self.input_tokens
        return max(1, len(self.prompt.split()))


@dataclass(frozen=True, slots=True)
class Response:
    text: str
    model: Model
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost: Cost
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def with_metadata(self, **items: Any) -> Response:
        merged = dict(self.metadata)
        merged.update(items)
        return Response(
            text=self.text,
            model=self.model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            latency_ms=self.latency_ms,
            cost=self.cost,
            metadata=MappingProxyType(merged),
        )


@dataclass(frozen=True, slots=True)
class Decision:
    request_id: str
    selected: Model
    candidates: tuple[Model, ...]
    reason: str
