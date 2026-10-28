from druks.signals import subscribe

from .workflows import HouseRules


@subscribe("pr.opened")
@subscribe("pr.synchronized")
@subscribe("pr.edited")
@subscribe("pr.ready_for_review")
async def pull_request_head_gets_checked(*, repo: str, pr_number: int, payload: dict) -> None:
    await HouseRules.dispatch(
        repo=repo,
        pr_number=pr_number,
        head_sha=payload["head_sha"],
        base_branch=payload["base_branch"],
        title=payload["title"],
        body=payload["body"],
    )
