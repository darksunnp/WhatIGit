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
    temp = []
    lines = chunk.splitlines()
    for flines in lines[1:]:
        if flines.strip() == "":
            continue
        temp.append(_parse_numstat_line(flines))

    header = lines[0]
    sha,name,email,date,subject = header.split(US) 
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
    added, deleted , path = line.split("\t",2)
    if added == "-":
        return FileChange(
            path=path,
            added=0,
            deleted=0,
            binary=True,
            )
    added = int(added)
    deleted = int(deleted)
    return FileChange(
        path=path,
        added=added,
        deleted=deleted,
        binary=False,
    )




def _resolve_rename(path: str) -> str:
    print("hello world")


