from __future__ import annotations
from dataclasses import dataclass
import hashlib
from pathlib import Path

from ..config import settings

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".venv", "venv",
    "__pycache__", ".pytest_cache", "target", ".idea", ".vscode",
    "out", ".turbo", ".cache", "coverage",
}

# Code-ish extensions worth summarizing. Everything else gets listed but not
# fed to the LLM, keeping the POC's token bill modest.
CODE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".php", ".c", ".h", ".cpp", ".hpp", ".cs", ".swift", ".scala",
    ".sh", ".bash", ".sql", ".vue", ".svelte",
    # Config / docs that often matter for context
    ".json", ".yaml", ".yml", ".toml", ".md", ".dockerfile",
}

NAMED_FILES = {
    "Dockerfile", "Makefile", "Procfile", "requirements.txt", "package.json",
    "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
}


@dataclass
class WalkedFile:
    path: str           # repo-relative, posix
    abs_path: Path
    size: int
    sha256: str
    is_code: bool


def _should_include(rel_path: Path) -> bool:
    if rel_path.name in NAMED_FILES:
        return True
    return rel_path.suffix.lower() in CODE_EXTS


def _hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_repo(repo_root: Path) -> list[WalkedFile]:
    files: list[WalkedFile] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        # skip anything inside a SKIP_DIRS directory
        if any(part in SKIP_DIRS for part in p.relative_to(repo_root).parts):
            continue
        rel = p.relative_to(repo_root)
        if not _should_include(rel):
            continue
        size = p.stat().st_size
        if size > settings.max_file_bytes:
            continue
        files.append(WalkedFile(
            path=rel.as_posix(),
            abs_path=p,
            size=size,
            sha256=_hash_file(p),
            is_code=True,
        ))
        if len(files) >= settings.max_files_per_run:
            break
    return files


def read_text(p: Path, max_chars: int = 12000) -> str:
    """Read a file as text, truncating safely. Returns empty string on binary."""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n... [truncated]"
    return text


def group_by_top_dir(files: list[WalkedFile]) -> dict[str, list[WalkedFile]]:
    """Group files by their top-level directory (or '_root' for repo-root files)."""
    out: dict[str, list[WalkedFile]] = {}
    for f in files:
        parts = f.path.split("/")
        key = parts[0] if len(parts) > 1 else "_root"
        out.setdefault(key, []).append(f)
    return out
