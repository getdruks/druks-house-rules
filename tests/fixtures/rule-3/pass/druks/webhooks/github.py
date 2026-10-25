def pull_request_number(payload: dict) -> int:
    number = payload.get("pull_request", {}).get("number")
    if not isinstance(number, int):
        raise ValueError("GitHub sent a pull request without an integer number")
    return number
