def spend(cost_usd: float | None, spent: dict[str, float]) -> None:
    if cost_usd is not None:
        spent["total"] += cost_usd
