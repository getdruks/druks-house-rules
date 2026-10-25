class Repository:
    name: str = ""

    def full_name(self) -> str:
        return self.name


class Note:
    body: str = ""
