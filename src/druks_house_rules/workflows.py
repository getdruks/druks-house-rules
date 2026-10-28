from druks.core.services import Github
from druks.sandbox import Sandbox
from druks.workflows import Workflow
from druks.workspaces import RepoWorkspace

from .models import Check


class HouseRules(Workflow):
    subject = Check
    sandbox = Sandbox(setup="sandboxes/check.sh")
    workspace_class = RepoWorkspace

    async def get_workspace_kwargs(self, host) -> dict:
        check = await self.subject
        return {**await super().get_workspace_kwargs(host), "branch": check.head_sha}

    async def run(self) -> None:
        check = await self.subject
        result = await self.exec(
            [
                "druks-house-rules",
                "check",
                "--json",
                "--base",
                f"origin/{check.base_branch}",
                "--pr-title",
                check.title,
                "--pr-body",
                check.body,
            ]
        )
        report = check.report(result)
        await (await Github.get_client()).post_check_run(
            check.repo,
            head_sha=check.head_sha,
            name="druks-house-rules",
            status="completed",
            **report,
        )
        await check.conclude(report["conclusion"])

    @classmethod
    async def dispatch(
        cls,
        *,
        repo: str,
        pr_number: int,
        head_sha: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> None:
        check = await Check.get_or_none(
            repo=repo, pr_number=pr_number, head_sha=head_sha, title=title, body=body
        )
        if not check:
            check = await Check.create(
                repo=repo,
                pr_number=pr_number,
                head_sha=head_sha,
                base_branch=base_branch,
                title=title,
                body=body,
            )
        if not check.conclusion:
            await cls.start(subject=check)
