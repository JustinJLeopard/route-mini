from __future__ import annotations

import pytest

from route_mini.providers import ModelCapabilities, ScriptedProvider, scripted_success
from route_mini.types import Model, Request


def caps(
    provider: str, model: str, cost: float = 0.001, latency: int = 100, max_tokens: int = 100
) -> ModelCapabilities:
    return ModelCapabilities(
        model=Model(provider=provider, name=model),
        max_tokens=max_tokens,
        cost_per_input_token=cost,
        cost_per_output_token=cost,
        latency_p50_ms=latency,
    )


@pytest.fixture
def route_request() -> Request:
    return Request(prompt="route this", max_tokens=10, input_tokens=2)


@pytest.fixture
def cheap() -> ModelCapabilities:
    return caps("cheap", "mini", cost=0.001, latency=120)


@pytest.fixture
def fast() -> ModelCapabilities:
    return caps("fast", "mini", cost=0.003, latency=20)


@pytest.fixture
def slow() -> ModelCapabilities:
    return caps("slow", "large", cost=0.002, latency=900)


def provider(capability: ModelCapabilities, *texts: str) -> ScriptedProvider:
    return ScriptedProvider(
        capability.model.provider,
        (capability,),
        [
            scripted_success(text=text, output_tokens=3, latency_ms=capability.latency_p50_ms)
            for text in texts
        ],
    )
