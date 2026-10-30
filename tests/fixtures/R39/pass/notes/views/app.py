from notes.core import models

from . import forms, urls
from .serializers import NoteSerializer


def note(pk: int) -> NoteSerializer:
    return NoteSerializer(models.Note(pk), forms, urls)
