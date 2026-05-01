from __future__ import annotations

import json

import pytest

from route_mini.decision import AuditDecision
from route_mini.providers import ModelCapabilities, ScriptedProvider, scripted_success
from route_mini.telemetry import Telemetry
from route_mini.types import Cost, Decision, Model, Provider, Request, Response


def test_cost_total() -> None:
    assert Cost(input=1.2, output=3.4).total == pytest.approx(4.6)


def test_model_key() -> None:
    assert Model("p", "m").key == "p:m"


def test_provider_type_has_name() -> None:
    assert Provider("p").name == "p"


def test_decision_type_keeps_route_reason() -> None:
    decision = Decision("r", Model("p", "m"), (Model("p", "m"),), "selected")
    assert decision.reason == "selected"


def test_request_estimated_input_tokens_uses_explicit_value() -> None:
    assert Request("a b c", max_tokens=1, input_tokens=7).estimated_input_tokens() == 7


def test_request_estimated_input_tokens_uses_words() -> None:
    assert Request("a b c", max_tokens=1).estimated_input_tokens() == 3


def test_request_estimated_input_tokens_never_zero() -> None:
    assert Request("", max_tokens=1).estimated_input_tokens() == 1


def test_response_with_metadata_merges() -> None:
    response = Response("x", Model("p", "m"), 1, 2, 3, Cost(0.1, 0.2), {"a": 1})
    updated = response.with_metadata(b=2)
    assert updated.metadata == {"a": 1, "b": 2}
    assert response.metadata == {"a": 1}


def test_model_capabilities_estimate_cost() -> None:
    caps = ModelCapabilities(Model("p", "m"), 10, 0.5, 2.0, 5)
    assert caps.estimate_cost(Request("a b", max_tokens=3)).total == pytest.approx(7.0)


def test_scripted_provider_returns_success_from_short_step() -> None:
    caps = ModelCapabilities(Model("p", "m"), 10, 0.1, 0.2, 5)
    provider = ScriptedProvider("p", (caps,), [scripted_success("ok", output_tokens=2)])
    response = provider.complete(caps.model, Request("one two", max_tokens=5))
    assert response.text == "ok"
    assert response.cost.total == pytest.approx(0.6)


def test_scripted_provider_returns_response_step() -> None:
    response = Response("raw", Model("p", "m"), 1, 1, 1, Cost())
    provider = ScriptedProvider("p", (ModelCapabilities(response.model, 10, 0, 0, 1),), [response])
    assert provider.complete(response.model, Request("x", 1)) is response


def test_scripted_provider_unknown_model_raises_provider_error() -> None:
    caps = ModelCapabilities(Model("p", "m"), 10, 0, 0, 1)
    provider = ScriptedProvider("p", (caps,), [scripted_success()])
    with pytest.raises(Exception, match="model not served"):
        provider.complete(Model("p", "other"), Request("x", 1))


def test_scripted_provider_exhaustion_raises_provider_error() -> None:
    caps = ModelCapabilities(Model("p", "m"), 10, 0, 0, 1)
    provider = ScriptedProvider("p", (caps,), [])
    with pytest.raises(Exception, match="script exhausted"):
        provider.complete(caps.model, Request("x", 1))


def test_decision_serialization_round_trip() -> None:
    decision = AuditDecision(
        request_id="r1",
        selected=Model("p", "m"),
        candidates=(Model("p", "m"),),
        reason="test",
        attempts=2,
        success=True,
        latency_ms=15,
        cost=Cost(1, 2),
        created_at=123.0,
    )
    clone = AuditDecision.from_dict(json.loads(json.dumps(decision.to_dict())))
    assert clone == decision


def test_decision_serialization_keeps_error_none() -> None:
    decision = AuditDecision("r", Model("p", "m"), (Model("p", "m"),), "x")
    assert AuditDecision.from_dict(decision.to_dict()).error is None


def test_telemetry_rollups_deterministic() -> None:
    telemetry = Telemetry()
    for latency in (10, 20, 30, 40):
        telemetry.record(
            AuditDecision(
                "r",
                Model("p", "m"),
                (Model("p", "m"),),
                "x",
                success=True,
                latency_ms=latency,
                cost=Cost(1, 1),
            )
        )
    rollup = telemetry.provider_rollups()["p"]
    assert rollup.total == 4
    assert rollup.success_rate == 1.0
    assert rollup.p50_latency_ms == 25
    assert rollup.p95_latency_ms == 40
    assert rollup.cost_to_date == 8


def test_telemetry_rollup_handles_failures() -> None:
    telemetry = Telemetry()
    telemetry.record(AuditDecision("r1", Model("p", "m"), (Model("p", "m"),), "x", success=True))
    telemetry.record(AuditDecision("r2", Model("p", "m"), (Model("p", "m"),), "x", success=False))
    assert telemetry.provider_rollups()["p"].success_rate == 0.5


def test_telemetry_empty_rollups() -> None:
    assert Telemetry().provider_rollups() == {}


def test_telemetry_ring_buffer_drops_oldest() -> None:
    telemetry = Telemetry(maxlen=1)
    telemetry.record(AuditDecision("old", Model("p", "m"), (Model("p", "m"),), "x"))
    telemetry.record(AuditDecision("new", Model("p", "m"), (Model("p", "m"),), "x"))
    assert telemetry.decisions()[0].request_id == "new"
