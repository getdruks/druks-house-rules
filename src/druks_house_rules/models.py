import json
import subprocess

from druks.db import StoredSubject
from sqlalchemy.orm import Mapped

from . import config


class Check(StoredSubject):
    """One pull request head, title, and body held to the rules."""

    repo: Mapped[str]
    pr_number: Mapped[int]
    head_sha: Mapped[str]
    base_branch: Mapped[str]
    title: Mapped[str]
    body: Mapped[str]
    conclusion: Mapped[str | None]

    def __str__(self) -> str:
        return f"{self.repo}#{self.pr_number} at {self.head_sha[:7]}"

    def report(self, result: subprocess.CompletedProcess[str]) -> dict:
        """The check run for the CLI's result, in GitHub's shape."""
        if result.returncode == 0:
            return {"conclusion": "success", "title": "No findings", "summary": "Every rule holds."}
        if result.returncode == 3:
            return {
                "conclusion": "neutral",
                "title": "Not configured",
                "summary": f"Add `{config.FILENAME}` to hold this repository to the rules.",
            }
        if result.returncode != 1:
            return {"conclusion": "failure", "title": "Check failed", "summary": result.stderr}
        findings = json.loads(result.stdout)
        return {
            "conclusion": "failure",
            "title": f"{len(findings)} findings" if len(findings) != 1 else "1 finding",
            "summary": "```\n"
            + "\n".join(
                f"{finding['path']}:{finding['line']} {finding['rule']} {finding['message']}"
                for finding in findings
            )
            + "\n```",
            "annotations": [
                {
                    "path": finding["path"],
                    "start_line": finding["line"],
                    "end_line": finding["line"],
                    "annotation_level": "failure",
                    "title": finding["rule"],
                    "message": finding["message"],
                }
                for finding in findings
            ],
        }

    async def conclude(self, conclusion: str) -> None:
        self.conclusion = conclusion
        await self.save()
