from druks.agents import Agent
from druks.apps import App

from .contracts import Pick


class HouseRules(App):
    name = "house_rules"
    icon = "gavel"
    description = (
        "Runs druks-house-rules on each pull request head and posts the findings "
        "as the druks-house-rules check run."
    )

    driver = Agent(
        description="Reads a change and picks the one phrase from the pool that fits it, or none.",
        prompt="house_rules/driver.md",
        contract=Pick,
        include_plugins=False,
        include_mcp=False,
    )
