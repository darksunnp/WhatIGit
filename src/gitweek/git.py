from datetime import datetime

from gitweek.models import Commit,FileChange

RS = "\x1e"
US = "\x1f"

def parse_log(raw: str, repo:str) -> list[Commit]:
    return raw.split(" ")

def _parse_commit(chunk:str, repo:str) -> Commit:
    """First line is the header, the rest are numstat lines."""
    return chunk.split("<US>")


