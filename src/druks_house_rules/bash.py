"""The process rules a Bash command is held to before it runs.

R33: no commit on ``main``; GitHub refuses the push. R35: a merge or a release
waits for the owner's word, so the hook asks instead of denying. R20: no test run
piped into ``tail``, ``head``, or ``grep``. R27: in a repository that runs it, the
body of ``gh pr create`` and ``gh pr edit`` holds before the pull request does.
"""

import pathlib
import re
import shlex

from . import checkout, config, pull_request
from .findings import Finding

SEPARATORS = frozenset({"&&", "||", ";", "&", "|"})
TEST_RUNNERS = frozenset({"pytest", "vitest", "jest"})
READERS = frozenset({"tail", "head", "grep"})
PROTECTED_BRANCH = "main"
ASKED_RULES = frozenset({"R35"})
PULL_REQUEST_VERBS = frozenset({"gh pr create", "gh pr edit"})
BODY_FLAGS = frozenset({"--body", "-b"})
BODY_FILE_FLAGS = frozenset({"--body-file", "-F"})
HEREDOC = re.compile(r"""<<-?\s*["']?(\w+)["']?[^\n]*\n(.*?)^\t*\1$""", re.DOTALL | re.MULTILINE)


def check(command: str, cwd: pathlib.Path) -> list[Finding]:
    """The findings on one command that the session runs from ``cwd``."""
    findings = []
    pipeline = _pipeline(command)
    directory = cwd
    for _, words in pipeline:
        verb = _verb(words)
        if words[:1] == ["cd"] and words[1:]:
            directory = _enter(directory, words[1])
        if verb == "git commit" and _branch(words, directory, cwd) == PROTECTED_BRANCH:
            findings.append(
                Finding(
                    "command",
                    1,
                    "R33",
                    f"commit on {PROTECTED_BRANCH}; create a branch and open a pull request",
                )
            )
        if verb in {"gh pr merge", "gh release"}:
            findings.append(
                Finding("command", 1, "R35", f"{verb}: the owner decides; ask before you run it")
            )
        if verb in PULL_REQUEST_VERBS and _runs_body_rule(directory if directory.is_dir() else cwd):
            findings.extend(pull_request.check_body(_body(verb, words, command, directory)))
    for (_, words), (operator, reader) in zip(pipeline, pipeline[1:], strict=False):
        if operator == "|" and _is_test_run(words) and reader and reader[0] in READERS:
            findings.append(
                Finding(
                    "command",
                    1,
                    "R20",
                    f"test run piped into {reader[0]}; run it as its own step and read it whole",
                )
            )
    return findings


def _branch(words: list[str], directory: pathlib.Path, cwd: pathlib.Path) -> str | None:
    """The branch a git command lands on. A path the shell has yet to expand is not
    a directory here, so the command counts as running in the session's folder."""
    arguments = iter(words[1:])
    for word in arguments:
        if word == "-C":
            directory = _enter(directory, next(arguments, ""))
        elif word == "-c":
            next(arguments, None)
        elif not word.startswith("-"):
            break
    return checkout.Checkout(directory if directory.is_dir() else cwd).branch()


def _runs_body_rule(directory: pathlib.Path) -> bool:
    repository = config.find_repository(directory)
    return bool(repository) and "R27" in repository[1].rules


def _body(verb: str, words: list[str], command: str, directory: pathlib.Path) -> str:
    """The body a pull request command gives. A heredoc comes from the raw command,
    because the lexer takes a quote in its text for the shell's. A file the command
    has yet to write, or a body on stdin, reads as empty here."""
    heredoc = HEREDOC.search(command, command.find(verb))
    if heredoc:
        return heredoc[2]
    arguments = iter(words)
    for word in arguments:
        flag, _, value = word.partition("=")
        if flag in BODY_FLAGS:
            return value or next(arguments, "")
        if flag in BODY_FILE_FLAGS:
            path = _enter(directory, value or next(arguments, ""))
            return path.read_text() if path.is_file() else ""
    return ""


def _enter(directory: pathlib.Path, path: str) -> pathlib.Path:
    return directory / pathlib.Path(path).expanduser()


def _pipeline(command: str) -> list[tuple[str, list[str]]]:
    """The command's simple commands, each with the operator that precedes it."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    pipeline = [("", [])]
    for token in tokens:
        if token in SEPARATORS:
            pipeline.append((token, []))
        else:
            pipeline[-1][1].append(token)
    return pipeline


def _verb(words: list[str]) -> str:
    """The program and its subcommand, such as ``git commit`` or ``gh pr merge``."""
    if not words:
        return ""
    program = words[0].rsplit("/", 1)[-1]
    arguments = iter(words[1:])
    subcommands = []
    for word in arguments:
        if word in {"-C", "-c"}:
            next(arguments, None)
        elif not word.startswith("-"):
            subcommands.append(word)
            if len(subcommands) == 2 or program != "gh":
                break
    verb = " ".join([program, *subcommands])
    if verb.startswith("gh release"):
        return "gh release"
    return verb


def _is_test_run(words: list[str]) -> bool:
    if any(word.rsplit("/", 1)[-1] in TEST_RUNNERS for word in words):
        return True
    return bool(words) and words[0] == "npm" and "test" in words
