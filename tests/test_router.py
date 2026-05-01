from __future__ import annotations

import pytest

from route_mini.fallback import FallbackChain, ProviderError
from route_mini.policy import (
    BudgetCapPolicy,
    CheapestPolicy,
    FastestPolicy,
    LatencyCapPolicy,
    PreferListPolicy,
)
from route_mini.providers import ModelCapabilities, ScriptedProvider, scripted_success
from route_mini.router import FallbackExhaustedError, Router
from route_mini.telemetry import Telemetry
from route_mini.types import Request

from .conftest import provider


def test_happy_path_single_provider(route_request: Request, cheap: ModelCapabilities) -> None:
    router = Router((provider(cheap, "done"),), CheapestPolicy())
    decision, response = router.route(route_request)
    assert response.text == "done"
    assert decision.success is True
    assert decision.reason == "policy-selected"


def test_primary_down_502_fallback_to_secondary(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    primary = ScriptedProvider("fast", (fast,), [ProviderError(status_code=502)])
    secondary = provider(cheap, "backup")
    decision, response = Router((primary, secondary), PreferListPolicy(("fast", "cheap"))).route(
        route_request
    )
    assert response.text == "backup"
    assert decision.reason == "fallback-selected"
    assert [item.provider for item in decision.fallback_from] == ["fast"]


def test_429_retry_with_backoff_then_success(
    route_request: Request, cheap: ModelCapabilities
) -> None:
    p = ScriptedProvider(
        "cheap", (cheap,), [ProviderError(status_code=429), scripted_success("retry-ok")]
    )
    router = Router(
        (p,), CheapestPolicy(), fallback=FallbackChain(max_retries=1), sleep_seconds_per_ms=0
    )
    decision, response = router.route(route_request)
    assert response.text == "retry-ok"
    assert decision.attempts == 2
    assert len(p.calls) == 2


def test_budget_cap_blocks_expensive_provider_in_router(
    route_request: Request, fast: ModelCapabilities
) -> None:
    router = Router((provider(fast, "nope"),), BudgetCapPolicy(0.001))
    with pytest.raises(FallbackExhaustedError) as raised:
        router.route(route_request)
    assert raised.value.decision.reason == "no-route"


def test_latency_cap_excludes_slow_provider(
    route_request: Request, slow: ModelCapabilities, cheap: ModelCapabilities
) -> None:
    router = Router((provider(slow, "slow"), provider(cheap, "cheap")), LatencyCapPolicy(200))
    _, response = router.route(route_request)
    assert response.model.provider == "cheap"


def test_prefer_list_ordering(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    router = Router((provider(cheap, "cheap"), provider(fast, "fast")), PreferListPolicy(("fast",)))
    _, response = router.route(route_request)
    assert response.text == "fast"


def test_fallback_exhaustion_error(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    router = Router(
        (
            ScriptedProvider("cheap", (cheap,), [ProviderError(status_code=502)]),
            ScriptedProvider("fast", (fast,), [ProviderError(status_code=503)]),
        ),
        CheapestPolicy(),
    )
    with pytest.raises(FallbackExhaustedError) as raised:
        router.route(route_request)
    assert raised.value.decision.reason == "fallback-exhausted"
    assert raised.value.decision.attempts == 2


def test_auth_error_stops_without_secondary(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    secondary = provider(fast, "should-not-run")
    router = Router(
        (ScriptedProvider("cheap", (cheap,), [ProviderError(status_code=401)]), secondary),
        CheapestPolicy(),
    )
    with pytest.raises(FallbackExhaustedError) as raised:
        router.route(route_request)
    assert raised.value.decision.reason == "blocked-error"
    assert secondary.calls == []


def test_router_filters_models_by_max_tokens(
    route_request: Request, cheap: ModelCapabilities
) -> None:
    too_small = ModelCapabilities(cheap.model, 2, 0.001, 0.001, 100)
    router = Router((provider(too_small, "x"),), CheapestPolicy())
    with pytest.raises(FallbackExhaustedError):
        router.route(route_request)


def test_response_includes_request_id_metadata(
    route_request: Request, cheap: ModelCapabilities
) -> None:
    _, response = Router((provider(cheap, "ok"),), CheapestPolicy()).route(route_request)
    assert response.metadata["request_id"] == "req-000001"
    assert response.metadata["route_reason"] == "policy-selected"


def test_request_ids_increment(route_request: Request, cheap: ModelCapabilities) -> None:
    router = Router((provider(cheap, "one", "two"),), CheapestPolicy())
    first, _ = router.route(route_request)
    second, _ = router.route(route_request)
    assert first.request_id == "req-000001"
    assert second.request_id == "req-000002"


def test_fastest_policy_selects_fastest_provider(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    _, response = Router((provider(cheap, "cheap"), provider(fast, "fast")), FastestPolicy()).route(
        route_request
    )
    assert response.model.provider == "fast"


def test_cheapest_policy_selects_cheapest_provider(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    _, response = Router(
        (provider(cheap, "cheap"), provider(fast, "fast")), CheapestPolicy()
    ).route(route_request)
    assert response.model.provider == "cheap"


def test_network_error_can_retry_same_provider(
    route_request: Request, cheap: ModelCapabilities
) -> None:
    p = ScriptedProvider("cheap", (cheap,), [ProviderError(network=True), scripted_success("ok")])
    decision, response = Router(
        (p,), CheapestPolicy(), fallback=FallbackChain(max_retries=1)
    ).route(route_request)
    assert response.text == "ok"
    assert decision.attempts == 2


def test_network_error_falls_to_secondary_after_retry_limit(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    first = ScriptedProvider("cheap", (cheap,), [ProviderError(network=True)])
    second = provider(fast, "second")
    decision, response = Router(
        (first, second), CheapestPolicy(), fallback=FallbackChain(max_retries=0)
    ).route(route_request)
    assert response.text == "second"
    assert decision.fallback_from[0].provider == "cheap"


def test_telemetry_records_success(route_request: Request, cheap: ModelCapabilities) -> None:
    telemetry = Telemetry()
    router = Router((provider(cheap, "ok"),), CheapestPolicy(), telemetry=telemetry)
    router.route(route_request)
    assert len(telemetry.decisions()) == 1
    assert telemetry.decisions()[0].success is True


def test_telemetry_records_failure(route_request: Request, cheap: ModelCapabilities) -> None:
    telemetry = Telemetry()
    router = Router(
        (ScriptedProvider("cheap", (cheap,), [ProviderError(status_code=503)]),),
        CheapestPolicy(),
        telemetry=telemetry,
    )
    with pytest.raises(FallbackExhaustedError):
        router.route(route_request)
    assert telemetry.decisions()[0].success is False
