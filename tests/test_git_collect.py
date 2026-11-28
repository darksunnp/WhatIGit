"""Tests for collect: running real git on temp repos and filtering by author date."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from gitweek.errors import GitweekError
from gitweek.git import collect
from gitweek.models import FileChange

# The window is Mon 16 Nov 00:00 up to (not including) Mon 23 Nov 00:00, UTC.
START = datetime(2026, 11, 16, tzinfo=UTC)
END = datetime(2026, 11, 23, tzinfo=UTC)

BEFORE = "2026-11-10T10:00:00+00:00"
INSIDE = "2026-11-18T10:00:00+00:00"
INSIDE_LATER = "2026-11-19T10:00:00+00:00"
AFTER = "2026-11-25T10:00:00+00:00"


def subjects(repo_path: Path) -> list[str]:
    return [c.subject for c in collect(str(repo_path), START, END)]


# Part B: run_git basics


def test_fresh_repo_returns_no_commits(repo) -> None:
    assert collect(str(repo.path), START, END) == []


def test_not_a_repo_raises_friendly_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(GitweekError):
        collect(str(plain), START, END)


def test_git_not_installed_raises_friendly_error(tmp_path: Path, monkeypatch) -> None:
    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", missing_git)
    with pytest.raises(GitweekError, match="not installed"):
        collect(str(tmp_path), START, END)


# Part C: collect and the time window


def test_reads_commits_in_the_window(repo) -> None:
    repo.commit("old work", {"a.py": "1\n"}, date=BEFORE)
    repo.commit("feat: add b", {"b.py": "1\n2\n"}, date=INSIDE)

    commits = collect(str(repo.path), START, END)

    assert [c.subject for c in commits] == ["feat: add b"]
    assert commits[0].repo == str(repo.path)
    assert commits[0].author_email == "ada@example.com"
    assert commits[0].files == (FileChange(path="b.py", added=2, deleted=0, binary=False),)


def test_newest_commit_comes_first(repo) -> None:
    repo.commit("first", {"a.py": "1\n"}, date=INSIDE)
    repo.commit("second", {"a.py": "2\n"}, date=INSIDE_LATER)
    assert subjects(repo.path) == ["second", "first"]


def test_window_start_is_included_and_end_is_not(repo) -> None:
    repo.commit("exactly at start", {"a.py": "1\n"}, date=START.isoformat())
    repo.commit("exactly at end", {"a.py": "2\n"}, date=END.isoformat())
    assert subjects(repo.path) == ["exactly at start"]


def test_rebased_old_work_does_not_count(repo) -> None:
    # Authored before the window, committed inside it (like a rebase this week).
    repo.commit("old idea", {"a.py": "1\n"}, date=BEFORE, committer_date=INSIDE)
    assert subjects(repo.path) == []


def test_work_committed_after_the_window_still_counts(repo) -> None:
    # Authored inside the window, committed later (like an amend next week).
    # This is why collect must not pass --until to git.
    repo.commit("feat: thing", {"a.py": "1\n"}, date=INSIDE, committer_date=AFTER)
    assert subjects(repo.path) == ["feat: thing"]


# Part D: real-world repo shapes


def test_commits_on_other_branches_count(repo) -> None:
    repo.commit("on main", {"a.py": "1\n"}, date=INSIDE)
    repo.git("switch", "-q", "-c", "feature")
    repo.commit("on feature", {"b.py": "1\n"}, date=INSIDE_LATER)
    repo.git("switch", "-q", "main")
    assert subjects(repo.path) == ["on feature", "on main"]


def test_stash_is_not_counted(repo) -> None:
    repo.commit("real work", {"a.py": "1\n"}, date=INSIDE)
    (repo.path / "a.py").write_text("half done\n")
    repo.git("stash", "-q", date=INSIDE_LATER)
    assert subjects(repo.path) == ["real work"]


def test_detached_head_still_works(repo) -> None:
    first = repo.commit("one", {"a.py": "1\n"}, date=INSIDE)
    repo.commit("two", {"a.py": "2\n"}, date=INSIDE_LATER)
    repo.git("checkout", "-q", "--detach", first)
    assert subjects(repo.path) == ["two", "one"]


def test_binary_file_and_rename_from_real_git(repo) -> None:
    repo.commit("add files", {"logo.png": b"\x89PNG\x00\x01", "src/old.py": "a\nb\n"}, date=INSIDE)
    repo.git("mv", "src/old.py", "src/new.py")
    repo.commit("refactor: rename", date=INSIDE_LATER)

    renamed, added = collect(str(repo.path), START, END)

    assert renamed.files == (FileChange(path="src/new.py", added=0, deleted=0, binary=False),)
    assert FileChange(path="logo.png", added=0, deleted=0, binary=True) in added.files


def test_unicode_and_spaces_in_paths(make_repo) -> None:
    # Needs `-c core.quotePath=false`, or git prints "notes/caf\303\251.md" in quotes.
    repo = make_repo("my repo")
    repo.commit("docs", {"notes/café ✨.md": "hi\n"}, date=INSIDE)
    [commit] = collect(str(repo.path), START, END)
    assert commit.files[0].path == "notes/café ✨.md"


def test_non_utf8_message_does_not_crash(repo) -> None:
    # Latin-1 bytes are not valid UTF-8. Some git versions convert them to "é",
    # others pass the raw byte through and errors="replace" turns it into U+FFFD.
    repo.commit(b"caf\xe9 au lait", {"a.py": "1\n"}, date=INSIDE)
    [commit] = collect(str(repo.path), START, END)
    assert commit.subject in ("café au lait", "caf� au lait")
