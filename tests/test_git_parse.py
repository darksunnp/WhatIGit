"""Tests for parse_log: turning raw `git log` text into Commit objects."""

from datetime import datetime, timedelta, timezone

import pytest

from gitweek.git import parse_log
from gitweek.models import FileChange

RS = "\x1e"  # record separator: starts each commit
US = "\x1f"  # unit separator: sits between header fields
REPO = "/home/ada/code/demo"


def header(
    sha: str = "a1b2c3",
    name: str = "Ada Lovelace",
    email: str = "ada@example.com",
    date: str = "2026-11-24T21:05:13+05:45",
    subject: str = "feat: add parser",
) -> str:
    return RS + US.join([sha, name, email, date, subject])


def commit_text(numstat: list[str] | None = None, **fields: str) -> str:
    """Build one commit exactly the way git prints it.

    A commit with files is: header, numstat lines, blank line.
    A commit with no files is just the header and a newline.
    """
    text = header(**fields) + "\n"
    if numstat:
        text += "\n".join(numstat) + "\n\n"
    return text


def test_empty_output_gives_no_commits() -> None:
    assert parse_log("", REPO) == []


def test_header_fields() -> None:
    [commit] = parse_log(commit_text(numstat=["1\t0\tREADME.md"]), REPO)
    assert commit.repo == REPO
    assert commit.sha == "a1b2c3"
    assert commit.author_name == "Ada Lovelace"
    assert commit.author_email == "ada@example.com"
    assert commit.subject == "feat: add parser"


def test_author_date_keeps_its_timezone() -> None:
    [commit] = parse_log(commit_text(), REPO)
    offset = timezone(timedelta(hours=5, minutes=45))
    assert commit.authored_at == datetime(2026, 11, 24, 21, 5, 13, tzinfo=offset)
    assert commit.authored_at.utcoffset() == timedelta(hours=5, minutes=45)


def test_numstat_lines_become_file_changes() -> None:
    raw = commit_text(numstat=["12\t3\tsrc/app.py", "0\t7\tdocs/old.md"])
    [commit] = parse_log(raw, REPO)
    # Comparing against a tuple also checks that files is a tuple, not a list.
    assert commit.files == (
        FileChange(path="src/app.py", added=12, deleted=3, binary=False),
        FileChange(path="docs/old.md", added=0, deleted=7, binary=False),
    )


def test_multiple_commits_keep_git_order() -> None:
    raw = (
        commit_text(sha="new", numstat=["1\t0\ta.py"])
        + commit_text(sha="mid")
        + commit_text(sha="old", numstat=["2\t2\tb.py"])
    )
    commits = parse_log(raw, REPO)
    assert [c.sha for c in commits] == ["new", "mid", "old"]


def test_commit_with_no_files() -> None:
    # `git commit --allow-empty` produces a header with no numstat lines.
    raw = commit_text(sha="empty") + commit_text(sha="next", numstat=["1\t0\ta.py"])
    empty, after = parse_log(raw, REPO)
    assert empty.files == ()
    assert len(after.files) == 1


def test_binary_file_counts_as_zero_lines() -> None:
    [commit] = parse_log(commit_text(numstat=["-\t-\tlogo.png"]), REPO)
    assert commit.files == (FileChange(path="logo.png", added=0, deleted=0, binary=True),)


@pytest.mark.parametrize(
    ("raw_path", "expected"),
    [
        ("old.py => new.py", "new.py"),
        ("sub/m.py => m.py", "m.py"),
        ("src/{old.py => new.py}", "src/new.py"),
        ("src/{old => new}.py", "src/new.py"),
        ("{src => lib}/util.py", "lib/util.py"),
        ("src/{ => sub}/a.py", "src/sub/a.py"),
        ("src/{sub => }/b.py", "src/b.py"),
    ],
)
def test_renames_resolve_to_new_path(raw_path: str, expected: str) -> None:
    [commit] = parse_log(commit_text(numstat=[f"0\t0\t{raw_path}"]), REPO)
    assert commit.files[0].path == expected


def test_path_with_spaces_and_unicode() -> None:
    [commit] = parse_log(commit_text(numstat=["3\t1\tmy notes/café ✨.md"]), REPO)
    assert commit.files[0].path == "my notes/café ✨.md"


def test_subject_with_tabs_and_arrows() -> None:
    # Header fields are split on \x1f only, so tabs and " => " in a subject are safe.
    subject = "fix:\tparse a => b ✨"
    [commit] = parse_log(commit_text(subject=subject), REPO)
    assert commit.subject == subject


def test_empty_subject() -> None:
    [commit] = parse_log(commit_text(subject=""), REPO)
    assert commit.subject == ""


def test_subject_from_non_utf8_message() -> None:
    # Bad bytes are decoded with errors="replace", so they arrive as U+FFFD.
    subject = "caf� au lait"
    [commit] = parse_log(commit_text(subject=subject), REPO)
    assert commit.subject == subject


def test_windows_line_endings() -> None:
    raw = commit_text(numstat=["4\t2\tsrc/app.py"]).replace("\n", "\r\n")
    [commit] = parse_log(raw, REPO)
    assert commit.subject == "feat: add parser"
    assert commit.files == (FileChange(path="src/app.py", added=4, deleted=2, binary=False),)
