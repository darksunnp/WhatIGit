import os
import subprocess
from datetime import datetime

from gitweek.errors import GitweekError
from gitweek.models import Commit, FileChange

RS = "\x1e"
US = "\x1f"


def parse_log(raw: str, repo: str) -> list[Commit]:
    result = []
    for temp in raw.split(RS):
        if temp.strip() == "":
            continue
        result.append(_parse_commit(temp, repo))
    return result


def _parse_commit(chunk: str, repo: str) -> Commit:
    temp = []
    lines = chunk.splitlines()
    for flines in lines[1:]:
        if flines.strip() == "":
            continue
        temp.append(_parse_numstat_line(flines))

    header = lines[0]
    sha, name, email, date, subject = header.split(US)
    return Commit(
        repo=repo,
        sha=sha,
        author_name=name,
        author_email=email,
        authored_at=datetime.fromisoformat(date),
        subject=subject,
        files=(tuple(temp)),
    )


def _parse_numstat_line(line: str) -> FileChange:
    added, deleted, path = line.split("\t", 2)
    if added == "-":
        return FileChange(
            path=_resolve_rename(path),
            added=0,
            deleted=0,
            binary=True,
        )
    added = int(added)
    deleted = int(deleted)
    return FileChange(
        path=_resolve_rename(path),
        added=added,
        deleted=deleted,
        binary=False,
    )


def _resolve_rename(path: str) -> str:
    if " => " not in path:
        return path
    if "{" not in path:
        return path.split(" => ")[1]

    before_t, _, rest_t = path.partition("{")
    before, _, rest = rest_t.partition("}")
    gluing = before_t + before.split(" => ")[1] + rest
    return gluing.replace("//", "/")


def run_git(args: list[str], cwd: str) -> str:
    cmd_list = ["git", "-C", cwd, *args]
    try:
        result = subprocess.run(
            cmd_list,
            env={**os.environ, "LC_ALL": "C"},
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as err:
        raise GitweekError("git not installed") from err
    if result.returncode != 0:
        raise GitweekError(f"git failed in {cwd}: {result.stderr.strip()}")
    return result.stdout


def collect(repo: str, start: datetime, end: datetime) -> list[Commit]:
    args = [
        "-c",
        "core.quotePath=false",
        "log",
        "--branches",
        "--remotes",
        "--no-merges",
        "-M",
        "--numstat",
        f"--since={start.isoformat()}",
        "--pretty=format:%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s",
    ]
    raw = run_git(args, repo)
    temp = parse_log(raw, repo)
    temp_list = []
    for commit in temp:
        if start <= commit.authored_at < end:
            temp_list.append(commit)
    return temp_list
