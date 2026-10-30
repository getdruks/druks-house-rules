from druks.agents import Agent
from druks.workspaces import RepoWorkspace

from .app import HouseRules

implementer = Agent.get("software_factory.implement")


@implementer.after_agent
async def phrase(*, prompt: str, workspace: RepoWorkspace) -> str | None:
    pick = await HouseRules.pick(diff=await workspace.get_diff(), task=prompt)
    return pick.phrase
