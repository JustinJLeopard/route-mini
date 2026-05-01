from __future__ import annotations

import pytest

from route_mini.fallback import ErrorKind, FallbackChain, ProviderError
from route_mini.types import Model


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (ProviderError(status_code=401), ErrorKind.AUTH),
        (ProviderError(status_code=403), ErrorKind.AUTH),
        (ProviderError(status_code=429), ErrorKind.RATE_LIMIT),
        (ProviderError(status_code=500), ErrorKind.PROVIDER_DOWN),
        (ProviderError(status_code=502), ErrorKind.PROVIDER_DOWN),
        (ProviderError(status_code=404), ErrorKind.BAD_REQUEST),
        (ProviderError(network=True), ErrorKind.NETWORK),
        (ProviderError(status_code=None), ErrorKind.UNKNOWN),
    ],
)
def test_classify_errors(error: ProviderError, kind: ErrorKind) -> None:
    assert FallbackChain().classify(error) == kind


def test_rate_limit_retries_before_fallthrough() -> None:
    decision = FallbackChain(max_retries=1).decide(ProviderError(status_code=429), attempt=0)
    assert decision.retry_same is True
    assert decision.fall_through is False
    assert decision.backoff_ms == 50


def test_rate_limit_falls_through_after_retry_limit() -> None:
    decision = FallbackChain(max_retries=1).decide(ProviderError(status_code=429), attempt=1)
    assert decision.retry_same is False
    assert decision.fall_through is True


def test_provider_down_falls_through_without_retry() -> None:
    decision = FallbackChain().decide(ProviderError(status_code=503), attempt=0)
    assert decision.retry_same is False
    assert decision.fall_through is True


def test_auth_error_blocks_fallback() -> None:
    decision = FallbackChain().decide(ProviderError(status_code=401), attempt=0)
    assert decision.retry_same is False
    assert decision.fall_through is False


def test_bad_request_blocks_fallback() -> None:
    decision = FallbackChain().decide(ProviderError(status_code=400), attempt=0)
    assert decision.fall_through is False


def test_network_can_retry_and_fall_through() -> None:
    decision = FallbackChain(max_retries=1).decide(ProviderError(network=True), attempt=0)
    assert decision.retry_same is True
    assert decision.fall_through is True
    assert decision.backoff_ms == 25


def test_unknown_falls_through() -> None:
    assert FallbackChain().decide(ProviderError(), attempt=0).fall_through is True


def test_order_promotes_primary() -> None:
    a = Model("a", "m")
    b = Model("b", "m")
    assert FallbackChain().order((a, b), primary=b) == (b, a)


def test_order_leaves_missing_primary_unchanged() -> None:
    a = Model("a", "m")
    b = Model("b", "m")
    assert FallbackChain().order((a,), primary=b) == (a,)


def test_negative_retries_rejected() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        FallbackChain(max_retries=-1)


def test_provider_error_string_for_network() -> None:
    assert str(ProviderError(network=True, message="offline")) == "network: offline"
