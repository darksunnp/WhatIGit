from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int
    deleted: int
    binary: bool


@dataclass(frozen=True)
class Commit:
    repo: str
    sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    subject: str
    files: tuple[FileChange, ...]
