# Fallback

`FallbackChain` classifies provider errors and decides whether to retry the same model or fall through to the next candidate.

Default behavior:

- 401 and 403: stop. This is an auth/configuration problem.
- 400-499 except 429: stop. The request probably needs correction.
- 429: retry up to `max_retries`, then fall through.
- 500-599: fall through immediately.
- Network errors: retry when allowed and permit fallthrough.
- Unknown errors: fall through.

When all candidates fail, `Router.route()` raises `FallbackExhaustedError`. The exception carries the final decision record so callers can log or inspect the failed route.
