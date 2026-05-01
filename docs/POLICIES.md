# Policies

Policies take eligible model capabilities and return a reordered or filtered tuple.

Available policies:

- `CheapestPolicy`: lowest estimated request cost first.
- `FastestPolicy`: lowest configured p50 latency first.
- `PreferListPolicy`: preferred provider names or `provider:model` keys first.
- `BudgetCapPolicy`: removes models over the estimated request budget.
- `LatencyCapPolicy`: removes models over the configured p50 latency target.

Policies compose left to right:

```python
policy = BudgetCapPolicy(0.05).then(LatencyCapPolicy(800)).then(CheapestPolicy())
```

The router also filters out models whose `max_tokens` cannot satisfy the request.
