from druks.agents import Agent
from druks.workspaces import RepoWorkspace

from .app import HouseRules

implementer = Agent.get("software_factory.implement")


@implementer.after_agent
async def nudge(*, prompt: str, workspace: RepoWorkspace) -> str | None:
    nudge = await HouseRules.nudge(diff=await workspace.get_diff(), task=prompt)
    return nudge.phrase
