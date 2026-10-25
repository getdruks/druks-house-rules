class Summarize:
    subject = "Note"

    def __init__(self, note) -> None:
        self.note = note

    @classmethod
    def for_note(cls, note) -> "Summarize":
        return cls(note)

    @property
    def title(self) -> str:
        return self.note.title

    async def run_multistep(self) -> None:
        await self.save_gist(await self.note.gist())

    async def save_gist(self, gist: str) -> None:
        await self.note.save_gist(gist)
