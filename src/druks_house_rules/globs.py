import re


def compile_glob(glob: str, separator: str = "/") -> re.Pattern[str]:
    """Translate a glob to a regular expression that matches a whole path.

    ``*`` matches within one segment. ``**`` matches across segments. The
    separator is ``/`` for file paths and ``.`` for module names.
    """
    escaped_separator = re.escape(separator)
    pattern = ""
    index = 0
    while index < len(glob):
        if glob.startswith("**" + separator, index):
            pattern += f"(?:[^{escaped_separator}]+{escaped_separator})*"
            index += 3
        elif glob.startswith("**", index):
            pattern += ".*"
            index += 2
        elif glob[index] == "*":
            pattern += f"[^{escaped_separator}]*"
            index += 1
        else:
            pattern += re.escape(glob[index])
            index += 1
    return re.compile(f"^{pattern}$")
