class Summarize:
    subject = "Note"

    def get_agent_run_kwargs(self) -> dict:
        return {"note_body": self.note.body}

    async def run_multistep(self) -> None:
        await self.note.save_gist(self.get_agent_run_kwargs())
