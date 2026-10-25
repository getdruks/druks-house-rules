def read_manifest(text: str) -> dict:
    import json

    return json.loads(text)
