from typing import Any, Callable, Iterator, Protocol

from druks_field_notes import exceptions


def gist(note: Any) -> str:
    if not note.gist:
        raise exceptions.NoteWithoutGist(note.id)
    return note.gist
from . import accounts, notes, runs, settings
