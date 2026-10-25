import json


def read_manifest(text: str) -> dict:
    return json.loads(text)
