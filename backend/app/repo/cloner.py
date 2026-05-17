from pathlib import Path
import shutil
from git import Repo

from ..config import settings


def repo_path(project_id: int) -> Path:
    return settings.repos_dir / str(project_id)


def clone_or_pull(project_id: int, repo_url: str, branch: str = "main") -> str:
    """Clone the repo if absent, otherwise fetch + checkout + pull. Returns
    the current HEAD sha."""
    path = repo_path(project_id)
    if path.exists() and (path / ".git").exists():
        repo = Repo(path)
        repo.remotes.origin.fetch()
        repo.git.checkout(branch)
        repo.remotes.origin.pull()
    else:
        if path.exists():
            shutil.rmtree(path)
        repo = Repo.clone_from(repo_url, path, branch=branch, depth=1)
    return repo.head.commit.hexsha


def changed_files(project_id: int, old_sha: str, new_sha: str) -> tuple[list[str], list[str], list[str]]:
    """Return (added, modified, deleted) repo-relative paths between two shas."""
    repo = Repo(repo_path(project_id))
    diff = repo.commit(old_sha).diff(new_sha)
    added, modified, deleted = [], [], []
    for d in diff:
        if d.change_type == "A":
            added.append(d.b_path)
        elif d.change_type == "D":
            deleted.append(d.a_path)
        else:
            modified.append(d.b_path or d.a_path)
    return added, modified, deleted
