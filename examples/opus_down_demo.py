from __future__ import annotations

from route_mini.fallback import ProviderError
from route_mini.policy import PreferListPolicy
from route_mini.providers import ModelCapabilities, ScriptedProvider, scripted_success
from route_mini.router import Router
from route_mini.types import Model, Request


def main() -> None:
    opus = ModelCapabilities(
        model=Model(provider="major-provider", name="opus"),
        max_tokens=4096,
        cost_per_input_token=0.000015,
        cost_per_output_token=0.000075,
        latency_p50_ms=900,
    )
    sonnet = ModelCapabilities(
        model=Model(provider="major-provider-backup", name="sonnet"),
        max_tokens=4096,
        cost_per_input_token=0.000003,
        cost_per_output_token=0.000015,
        latency_p50_ms=500,
    )

    primary = ScriptedProvider(
        "major-provider", (opus,), [ProviderError(status_code=502, message="bad gateway")]
    )
    fallback = ScriptedProvider(
        "major-provider-backup",
        (sonnet,),
        [scripted_success("fallback response", output_tokens=32, latency_ms=510)],
    )
    router = Router(
        (primary, fallback),
        PreferListPolicy(("major-provider:opus", "major-provider-backup:sonnet")),
    )
    decision, response = router.route(
        Request(prompt="Summarize the incident", max_tokens=64, input_tokens=12)
    )

    print(f"selected={response.model.key}")
    print(f"reason={decision.reason}")
    print(f"fallback_from={[model.key for model in decision.fallback_from]}")
    print(f"attempts={decision.attempts}")
    print(f"text={response.text}")


if __name__ == "__main__":
    main()
