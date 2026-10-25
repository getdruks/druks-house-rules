import dataclasses


@dataclasses.dataclass(frozen=True, order=True)
class Finding:
    """One place where a rule does not hold.

    ``path`` is relative to the checkout root. A finding about a commit uses
    ``commit:<sha>`` and a finding about the pull request body uses ``pr-body``.
    """

    path: str
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} {self.rule} {self.message}"
