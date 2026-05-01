from __future__ import annotations

from itertools import count
from time import sleep

from route_mini.decision import AuditDecision
from route_mini.fallback import FallbackChain, ProviderError
from route_mini.policy import Policy
from route_mini.providers import ModelCapabilities, Provider
from route_mini.telemetry import Telemetry
from route_mini.types import Cost, Model, Request, Response


class FallbackExhaustedError(RuntimeError):
    def __init__(self, decision: AuditDecision):
        super().__init__(decision.error or "fallback exhausted")
        self.decision = decision


class Router:
    def __init__(
        self,
        providers: tuple[Provider, ...],
        policy: Policy,
        fallback: FallbackChain | None = None,
        telemetry: Telemetry | None = None,
        sleep_seconds_per_ms: float = 0.0,
    ):
        self.providers = {provider.name: provider for provider in providers}
        self.policy = policy
        self.fallback = fallback or FallbackChain()
        self.telemetry = telemetry or Telemetry()
        self.sleep_seconds_per_ms = sleep_seconds_per_ms
        self._ids = count(1)

    def route(self, request: Request) -> tuple[AuditDecision, Response]:
        candidates = self._candidate_capabilities(request)
        if not candidates:
            decision = self._failed_decision(
                request_id=self._request_id(), error="no eligible models"
            )
            self.telemetry.record(decision)
            raise FallbackExhaustedError(decision)

        request_id = self._request_id()
        candidate_models = tuple(candidate.model for candidate in candidates)
        failed: list[Model] = []
        attempts = 0
        last_error: str | None = None

        for capability in candidates:
            provider = self.providers[capability.model.provider]
            attempt = 0
            while True:
                attempts += 1
                try:
                    response = provider.complete(capability.model, request)
                except ProviderError as error:
                    last_error = str(error)
                    fallback_decision = self.fallback.decide(error, attempt)
                    if fallback_decision.retry_same:
                        attempt += 1
                        if fallback_decision.backoff_ms:
                            sleep(fallback_decision.backoff_ms * self.sleep_seconds_per_ms)
                        continue
                    failed.append(capability.model)
                    if fallback_decision.fall_through:
                        break
                    decision = AuditDecision(
                        request_id=request_id,
                        selected=capability.model,
                        candidates=candidate_models,
                        reason="blocked-error",
                        fallback_from=tuple(failed),
                        attempts=attempts,
                        success=False,
                        error=last_error,
                    )
                    self.telemetry.record(decision)
                    raise FallbackExhaustedError(decision) from error
                decision = AuditDecision(
                    request_id=request_id,
                    selected=response.model,
                    candidates=candidate_models,
                    reason="policy-selected" if not failed else "fallback-selected",
                    fallback_from=tuple(failed),
                    attempts=attempts,
                    success=True,
                    latency_ms=response.latency_ms,
                    cost=response.cost,
                )
                self.telemetry.record(decision)
                return decision, response.with_metadata(
                    request_id=request_id, route_reason=decision.reason
                )

        decision = AuditDecision(
            request_id=request_id,
            selected=failed[-1] if failed else candidate_models[0],
            candidates=candidate_models,
            reason="fallback-exhausted",
            fallback_from=tuple(failed),
            attempts=attempts,
            success=False,
            error=last_error or "fallback exhausted",
        )
        self.telemetry.record(decision)
        raise FallbackExhaustedError(decision)

    def _candidate_capabilities(self, request: Request) -> tuple[ModelCapabilities, ...]:
        all_models = tuple(
            capability for provider in self.providers.values() for capability in provider.models()
        )
        eligible = tuple(
            candidate for candidate in all_models if candidate.max_tokens >= request.max_tokens
        )
        return self.policy.apply(eligible, request)

    def _request_id(self) -> str:
        return f"req-{next(self._ids):06d}"

    def _failed_decision(self, request_id: str, error: str) -> AuditDecision:
        return AuditDecision(
            request_id=request_id,
            selected=Model(provider="none", name="none"),
            candidates=(),
            reason="no-route",
            attempts=0,
            success=False,
            error=error,
            cost=Cost(),
        )
