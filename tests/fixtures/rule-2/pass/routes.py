def spend(cost_usd: float | None, spent: dict[str, float]) -> None:
    if cost_usd:
        spent["total"] += cost_usd


def exit_code(returncode: int | None) -> int:
    return returncode if returncode is not None else -1  # ast-grep-ignore: rule-2
