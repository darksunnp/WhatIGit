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
    print("hello world")



