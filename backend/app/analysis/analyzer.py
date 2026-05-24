from __future__ import annotations
import json
import logging
from pathlib import Path

from ..config import settings
from ..db import session_scope, Project, FileRecord, DocPage, RunEvent
from ..llm import get_provider
from ..repo.cloner import prepare_source, working_path
from ..repo.walker import walk_repo, WalkedFile
from ..codegraph.service import build_code_graph, persist_code_graph
from .summarizer import summarize_many
from .doc_generator import (
    generate_module_page, generate_overview, generate_architecture,
    write_doc, slugify, grouped_modules,
)

log = logging.getLogger("codewiki.analyzer")


def docs_dir(project_id: int) -> Path:
    d = settings.projects_dir / str(project_id) / "docs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _module_slug(module: str) -> str:
    return f"modules/{slugify(module)}"


def _set_status(project_id: int, status: str, detail: str | None = None) -> None:
    with session_scope() as s:
        p = s.get(Project, project_id)
        if p:
            p.status = status
            p.status_detail = detail


def run_graph_analysis(project_id: int) -> None:
    """Prepare source and persist only the deterministic code graph."""
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise ValueError(f"Project {project_id} not found")
        s.expunge(p)
        project = p

    _set_status(
        project_id, "graphing",
        "Cloning repo…" if project.source_type == "git" else "Reading local path…",
    )
    head_sha = prepare_source(project)

    _set_status(project_id, "graphing", "Walking files…")
    files = walk_repo(working_path(project))

    _set_status(project_id, "graphing", "Building code graph…")
    code_graph = build_code_graph(files)

    with session_scope() as s:
        persist_code_graph(s, project_id, code_graph)
        p = s.get(Project, project_id)
        if p:
            p.last_commit_sha = head_sha
            p.status = "graph_ready"
            p.status_detail = (
                f"{len(files)} files; "
                f"{len(code_graph.nodes)} graph nodes, {len(code_graph.edges)} edges"
            )


async def run_initial_analysis(project_id: int) -> None:
    """End-to-end: prepare source -> walk -> summarize -> generate docs -> persist."""
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise ValueError(f"Project {project_id} not found")
        provider_name, llm_config = p.llm_provider, p.llm_config
        repo_name = p.name
        s.expunge(p)
        project = p

    _set_status(
        project_id, "analyzing",
        "Cloning repo…" if project.source_type == "git" else "Reading local path…",
    )
    head_sha = prepare_source(project)

    _set_status(project_id, "analyzing", "Walking files…")
    files = walk_repo(working_path(project))
    log.info("project %s: %d files to analyze", project_id, len(files))

    _set_status(project_id, "analyzing", "Building code graph…")
    code_graph = build_code_graph(files)

    llm = get_provider(provider_name, llm_config)

    _set_status(project_id, "analyzing", f"Summarizing {len(files)} files…")
    summaries = await summarize_many(llm, files)

    _set_status(project_id, "analyzing", "Generating module pages…")
    grouped = grouped_modules(files)
    module_pages: dict[str, str] = {}
    for module, mod_files in grouped.items():
        module_pages[module] = await generate_module_page(llm, module, mod_files, summaries)

    _set_status(project_id, "analyzing", "Generating overview & architecture…")
    overview = await generate_overview(llm, repo_name, module_pages)
    architecture = await generate_architecture(llm, repo_name, module_pages)

    out = docs_dir(project_id)
    write_doc(out, "overview", overview)
    write_doc(out, "architecture", architecture)
    for module, page in module_pages.items():
        write_doc(out, _module_slug(module), page)

    # Persist everything
    with session_scope() as s:
        p = s.get(Project, project_id)
        # wipe and re-write file + doc records for a clean state on first run
        for old in list(p.files):
            s.delete(old)
        for old in list(p.docs):
            s.delete(old)
        s.flush()

        for f in files:
            s.add(FileRecord(
                project_id=project_id, path=f.path, sha256=f.sha256,
                summary=summaries.get(f.path),
            ))
        persist_code_graph(s, project_id, code_graph)

        s.add(DocPage(
            project_id=project_id, slug="overview", title="Overview",
            kind="overview", source_paths=json.dumps([f.path for f in files]),
        ))
        s.add(DocPage(
            project_id=project_id, slug="architecture", title="Architecture",
            kind="architecture", source_paths=json.dumps([f.path for f in files]),
        ))
        for module, mod_files in grouped.items():
            s.add(DocPage(
                project_id=project_id, slug=_module_slug(module),
                title=f"Module: {module}", kind="module",
                source_paths=json.dumps([f.path for f in mod_files]),
            ))

        p.last_commit_sha = head_sha
        p.status = "ready"
        p.status_detail = f"{len(files)} files, {len(grouped)} modules"
        s.add(RunEvent(project_id=project_id, kind="initial"))


async def _summarize_files_by_path(llm, project: Project, paths: list[str]) -> tuple[list[WalkedFile], dict[str, str]]:
    """Helper: given repo-relative paths, walk + summarize just those."""
    if not paths:
        return [], {}
    root = working_path(project)
    walked: list[WalkedFile] = []
    from ..repo.walker import _hash_file  # type: ignore
    for rel in paths:
        ap = root / rel
        if not ap.exists() or not ap.is_file():
            continue
        try:
            size = ap.stat().st_size
            if size > settings.max_file_bytes:
                continue
        except OSError:
            continue
        walked.append(WalkedFile(
            path=rel, abs_path=ap, size=size, sha256=_hash_file(ap), is_code=True,
        ))
    summaries = await summarize_many(llm, walked)
    return walked, summaries
