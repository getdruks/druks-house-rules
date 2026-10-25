from druks_field_notes.exceptions import (
    NoteNotFound,
    NoteWithoutGist,
    RepositoryNotFound,
    SummaryRejected,
)


def gist(note) -> str:
    if not note.gist:
        raise NoteWithoutGist(note.id)
    return note.gist
