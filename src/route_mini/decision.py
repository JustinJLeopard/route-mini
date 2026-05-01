from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from route_mini.types import Cost, Model


@dataclass(frozen=True, slots=True)
class AuditDecision:
    request_id: str
    selected: Model
    candidates: tuple[Model, ...]
    reason: str
    fallback_from: tuple[Model, ...] = ()
    attempts: int = 0
    success: bool = False
    error: str | None = None
    latency_ms: int = 0
    cost: Cost = field(default_factory=Cost)
    created_at: float = field(default_factory=time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "selected": {"provider": self.selected.provider, "name": self.selected.name},
            "candidates": [
                {"provider": item.provider, "name": item.name} for item in self.candidates
            ],
            "reason": self.reason,
            "fallback_from": [
                {"provider": item.provider, "name": item.name} for item in self.fallback_from
            ],
            "attempts": self.attempts,
            "success": self.success,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "cost": {
                "input": self.cost.input,
                "output": self.cost.output,
                "total": self.cost.total,
            },
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditDecision:
        cost = data["cost"]
        return cls(
            request_id=str(data["request_id"]),
            selected=_model_from(data["selected"]),
            candidates=tuple(_model_from(item) for item in data["candidates"]),
            reason=str(data["reason"]),
            fallback_from=tuple(_model_from(item) for item in data.get("fallback_from", ())),
            attempts=int(data["attempts"]),
            success=bool(data["success"]),
            error=None if data.get("error") is None else str(data["error"]),
            latency_ms=int(data["latency_ms"]),
            cost=Cost(input=float(cost["input"]), output=float(cost["output"])),
            created_at=float(data["created_at"]),
        )


def _model_from(data: dict[str, Any]) -> Model:
    return Model(provider=str(data["provider"]), name=str(data["name"]))
