# Usage

`route-mini` separates routing from provider clients. Core objects accept provider implementations, model capabilities, a routing policy, and fallback rules.

```python
from route_mini import Router, Request, PreferListPolicy

router = Router(providers=(primary, secondary), policy=PreferListPolicy(("primary", "secondary")))
decision, response = router.route(Request(prompt="hello", max_tokens=64))
```

The returned `decision` records candidates, selected model, fallback attempts, latency, cost, and success state. The returned `response` includes the selected model and request id metadata.

## Provider Contract

Implement `Provider.models()` to return capabilities, and `Provider.complete()` to execute one model. Keep SDK setup outside the router so the policy layer remains testable and provider-agnostic.

Tests and demos use `ScriptedProvider`, which replays fixed successes or errors without network access.
