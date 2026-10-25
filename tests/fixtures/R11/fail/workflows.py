from druks.workflows import Workflow, step


class EnqueueInStepFlow(Workflow):
    @step
    async def misuse(self) -> None:
        await record_task.enqueue(repo="from-a-step")

    async def run_multistep(self) -> None:
        await self.misuse()
