from __future__ import annotations

from route_mini.policy import (
    BudgetCapPolicy,
    CheapestPolicy,
    FastestPolicy,
    LatencyCapPolicy,
    PreferListPolicy,
)
from route_mini.providers import ModelCapabilities
from route_mini.types import Request


def keys(items: tuple[ModelCapabilities, ...]) -> list[str]:
    return [item.model.key for item in items]


def test_cheapest_policy_orders_by_estimated_cost(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    assert keys(CheapestPolicy().apply((fast, cheap), route_request)) == ["cheap:mini", "fast:mini"]


def test_fastest_policy_orders_by_latency(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    assert keys(FastestPolicy().apply((cheap, fast), route_request)) == ["fast:mini", "cheap:mini"]


def test_prefer_list_policy_orders_by_provider(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    assert keys(PreferListPolicy(("fast",)).apply((cheap, fast), route_request)) == [
        "fast:mini",
        "cheap:mini",
    ]


def test_prefer_list_policy_orders_by_model_key(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    assert keys(PreferListPolicy(("cheap:mini",)).apply((fast, cheap), route_request)) == [
        "cheap:mini",
        "fast:mini",
    ]


def test_prefer_list_keeps_unknowns_after_known(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    assert (
        keys(PreferListPolicy(("missing", "fast")).apply((cheap, fast), route_request))[0]
        == "fast:mini"
    )


def test_budget_cap_blocks_expensive_provider(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    assert keys(BudgetCapPolicy(0.02).apply((cheap, fast), route_request)) == ["cheap:mini"]


def test_budget_cap_allows_equal_cost(route_request: Request, cheap: ModelCapabilities) -> None:
    assert keys(BudgetCapPolicy(0.012).apply((cheap,), route_request)) == ["cheap:mini"]


def test_budget_cap_can_return_empty(route_request: Request, fast: ModelCapabilities) -> None:
    assert BudgetCapPolicy(0.001).apply((fast,), route_request) == ()


def test_latency_cap_excludes_slow(
    route_request: Request, cheap: ModelCapabilities, slow: ModelCapabilities
) -> None:
    assert keys(LatencyCapPolicy(200).apply((cheap, slow), route_request)) == ["cheap:mini"]


def test_latency_cap_allows_equal_latency(route_request: Request, cheap: ModelCapabilities) -> None:
    assert keys(LatencyCapPolicy(120).apply((cheap,), route_request)) == ["cheap:mini"]


def test_composite_policy_filters_then_orders(
    route_request: Request,
    cheap: ModelCapabilities,
    fast: ModelCapabilities,
    slow: ModelCapabilities,
) -> None:
    policy = LatencyCapPolicy(200).then(CheapestPolicy())
    assert keys(policy.apply((fast, slow, cheap), route_request)) == ["cheap:mini", "fast:mini"]


def test_composite_policy_chain_is_left_to_right(
    route_request: Request, cheap: ModelCapabilities, fast: ModelCapabilities
) -> None:
    policy = CheapestPolicy().then(PreferListPolicy(("fast",)))
    assert keys(policy.apply((cheap, fast), route_request)) == ["fast:mini", "cheap:mini"]


def test_max_token_filter_is_left_to_router(
    cheap: ModelCapabilities, route_request: Request
) -> None:
    assert CheapestPolicy().apply((cheap,), route_request) == (cheap,)
