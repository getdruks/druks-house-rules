from ..core import models


def note(pk: int) -> models.Note:
    return models.Note(pk)
