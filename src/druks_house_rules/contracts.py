from druks.agents import AgentOutput
from pydantic import Field

from .pool import ENTRIES


class Pick(AgentOutput):
    """The pick: the id of the pool entry whose situation the change shows,
    or null, and one sentence on where in the diff it shows."""

    entry: int | None = Field(ge=1, le=len(ENTRIES))
    where: str

    @property
    def phrase(self) -> str | None:
        if self.entry:
            return ENTRIES[self.entry - 1]["phrase"]
        return

    def to_artifact(self) -> dict[str, str]:
        content = f"{self.phrase}\n\n{self.where}" if self.entry else "No phrase fits this change."
        return {"kind": "markdown", "title": "Pick", "content": content}

    def to_event(self) -> dict[str, str]:
        summary = f"{self.entry}: {self.phrase}" if self.entry else "none"
        return {"topic": "rule.hit", "summary": summary}
