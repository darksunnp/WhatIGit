from datetime import datetime

from gitweek.models import Commit,FileChange

RS = "\x1e"
US = "\x1f"

def parse_log(raw: str, repo:str) -> list[Commit]:
    result = []
    for temp in raw.split(RS):
        if temp.strip() == "":
            continue
        result.append(_parse_commit(temp,repo))
    return result
        

def _parse_commit(chunk:str, repo:str) -> Commit:
    lines = chunk.splitlines()
    header = lines[0]
    sha,name,email,date,subject = header.split(US)
    return Commit(
        repo=repo,
        sha=sha,
        author_name=name,
        author_email=email,
        authored_at=datetime.fromisoformat(date),
        subject=subject,
        files=(),
    )




