def announce(events: list[str], name: str) -> None:
    if not name:
        return
    events.append(name)
