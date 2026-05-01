from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from route_mini.fallback import ProviderError
from route_mini.types import Cost, Model, Request, Response


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    model: Model
    max_tokens: int
    cost_per_input_token: float
    cost_per_output_token: float
    latency_p50_ms: int

    def estimate_cost(self, request: Request) -> Cost:
        return Cost(
            input=request.estimated_input_tokens() * self.cost_per_input_token,
            output=request.max_tokens * self.cost_per_output_token,
        )


class Provider(ABC):
    name: str

    @abstractmethod
    def models(self) -> tuple[ModelCapabilities, ...]:
        raise NotImplementedError

    @abstractmethod
    def complete(self, model: Model, request: Request) -> Response:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ScriptedSuccess:
    text: str = "ok"
    output_tokens: int = 1
    latency_ms: int | None = None


ScriptedStep = Response | ScriptedSuccess | ProviderError


class ScriptedProvider(Provider):
    def __init__(
        self, name: str, capabilities: Iterable[ModelCapabilities], script: Iterable[ScriptedStep]
    ):
        self.name = name
        self._capabilities = tuple(capabilities)
        self._script: deque[ScriptedStep] = deque(script)
        self.calls: list[tuple[Model, Request]] = []

    def models(self) -> tuple[ModelCapabilities, ...]:
        return self._capabilities

    def complete(self, model: Model, request: Request) -> Response:
        self.calls.append((model, request))
        if not self._script:
            raise ProviderError(status_code=503, message=f"{self.name} script exhausted")
        step = self._script.popleft()
        if isinstance(step, ProviderError):
            raise step
        if isinstance(step, Response):
            return step
        caps = self._capability_for(model)
        output_tokens = step.output_tokens
        cost = Cost(
            input=request.estimated_input_tokens() * caps.cost_per_input_token,
            output=output_tokens * caps.cost_per_output_token,
        )
        return Response(
            text=step.text,
            model=model,
            input_tokens=request.estimated_input_tokens(),
            output_tokens=output_tokens,
            latency_ms=step.latency_ms if step.latency_ms is not None else caps.latency_p50_ms,
            cost=cost,
        )

    def _capability_for(self, model: Model) -> ModelCapabilities:
        for capability in self._capabilities:
            if capability.model == model:
                return capability
        raise ProviderError(status_code=400, message=f"model not served: {model.key}")


def scripted_success(
    text: str = "ok", output_tokens: int = 1, latency_ms: int | None = None
) -> ScriptedSuccess:
    return ScriptedSuccess(text=text, output_tokens=output_tokens, latency_ms=latency_ms)
