from druks.workflows import Instruction
from druks.workspaces import RepoWorkspace

from .app import HouseRules

implementer = Instruction.get("software_factory.implement")


@implementer.after_agent
async def nudge(*, prompt: str, workspace: RepoWorkspace) -> str | None:
    nudge = await HouseRules.nudge(diff=await workspace.get_diff(), task=prompt)
    if nudge.entry:
        return f"{nudge.phrase}\n\n{nudge.where}"
    return
