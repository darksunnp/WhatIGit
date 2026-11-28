"""Shared test fixtures: temporary git repos with fixed dates."""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

DEFAULT_DATE = "2026-11-18T10:00:00+00:00"


@pytest.fixture(autouse=True)
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests away from your real git settings and any repo above tmp_path."""
    empty_config = tmp_path / "gitconfig"
    empty_config.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))


class RepoBuilder:
    """A real git repo in a temp folder, with helpers to make dated commits."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Ada Lovelace")
        self.git("config", "user.email", "ada@example.com")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str, date: str | None = None) -> str:
        """Run git inside the repo. `date` fixes both author and committer date."""
        env = dict(os.environ)
        if date is not None:
            env["GIT_AUTHOR_DATE"] = date
            env["GIT_COMMITTER_DATE"] = date
        result = subprocess.run(
            ["git", *args],
            cwd=self.path,
            env=env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return result.stdout

    def commit(
        self,
        message: str | bytes,
        files: dict[str, str | bytes] | None = None,
        *,
        date: str = DEFAULT_DATE,
        committer_date: str | None = None,
    ) -> str:
        """Write files, stage everything, commit, and return the new sha.

        `date` is the author date. `committer_date` defaults to the same value.
        """
        for name, content in (files or {}).items():
            target = self.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8", newline="")

        message_file = self.path.parent / f"{self.path.name}-message.txt"
        if isinstance(message, bytes):
            message_file.write_bytes(message)
        else:
            message_file.write_text(message, encoding="utf-8")

        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = committer_date or date
        for args in (["add", "-A"], ["commit", "-q", "--allow-empty", "-F", str(message_file)]):
            subprocess.run(["git", *args], cwd=self.path, env=env, capture_output=True, check=True)
        return self.git("rev-parse", "HEAD").strip()


@pytest.fixture
def make_repo(tmp_path: Path) -> Callable[[str], RepoBuilder]:
    """Call make_repo("name") to create a fresh repo under tmp_path."""

    def _make(name: str = "demo") -> RepoBuilder:
        path = tmp_path / name
        path.mkdir(parents=True)
        return RepoBuilder(path)

    return _make


@pytest.fixture
def repo(make_repo: Callable[[str], RepoBuilder]) -> RepoBuilder:
    """A fresh repo named "demo" with no commits yet."""
    return make_repo("demo")
