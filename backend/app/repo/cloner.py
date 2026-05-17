from pathlib import Path
import shutil
from git import Repo

from ..config import settings
from ..db import Project


def _git_clone_dir(project_id: int) -> Path:
    return settings.repos_dir / str(project_id)


def working_path(project: Project) -> Path:
    """Where the source files for this project actually live on disk."""
    if project.source_type == "local":
        return Path(project.repo_url)
    return _git_clone_dir(project.id)


def prepare_source(project: Project) -> str | None:
    """Make sure the source is on disk and ready to walk.

    - For git projects: clone or fetch+pull. Returns the current HEAD sha.
    - For local projects: validate the path exists. Returns None.
    """
    if project.source_type == "local":
        p = Path(project.repo_url)
        if not p.is_absolute():
            raise ValueError(f"Local path must be absolute: {project.repo_url}")
        if not p.exists() or not p.is_dir():
            raise ValueError(f"Local path is not a directory: {p}")
        return None

    return _clone_or_pull(project.id, project.repo_url, project.branch)


def _clone_or_pull(project_id: int, repo_url: str, branch: str = "main") -> str:
    path = _git_clone_dir(project_id)
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
