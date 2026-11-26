from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int
    deleted: int
    binary: int


class Commit:
    repo: str
    sha: str
    author_name: str
    author_eail: str
    authored_at: datetime
    subject: str
    files: tuple[FileChange, ...]
