from druks.workflows import Workflow, step


class Summarize(Workflow):
    async def run_multistep(self) -> None:
        await self.save_gist("gist")

    @step
    async def save_gist(self, gist: str) -> None:
        note = await self.subject
        await note.save_gist(gist)
