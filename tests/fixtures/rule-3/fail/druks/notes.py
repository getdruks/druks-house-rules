def gist_length(note) -> int:
    if isinstance(note.gist, str):
        return len(note.gist)
    return 0
