from __future__ import annotations
import json
import logging

from ..db import session_scope, Project, FileRecord, DocPage, RunEvent
from ..llm import get_provider
from ..repo.cloner import prepare_source, working_path
from ..repo.walker import walk_repo
from ..codegraph.service import build_code_graph, persist_code_graph
from .analyzer import (
    docs_dir, _module_slug, _set_status, _summarize_files_by_path,
)
from .doc_generator import (
    generate_module_page, generate_overview, generate_architecture, write_doc,
)
from .prompts import DOC_PATCH_SYSTEM, DOC_PATCH_USER

log = logging.getLogger("codewiki.updater")


def _diff_against_db(project: Project) -> tuple[list[str], list[str], list[str], dict[str, str]]:
    """Walk the repo and compare against stored FileRecord hashes.
    Returns (added, modified, deleted, current_hash_by_path)."""
    walked = walk_repo(working_path(project))
    current = {f.path: f.sha256 for f in walked}

    with session_scope() as s:
        records = (
            s.query(FileRecord).filter(FileRecord.project_id == project.id).all()
        )
        prev = {r.path: r.sha256 for r in records}

    added = [p for p in current if p not in prev]
    deleted = [p for p in prev if p not in current]
    modified = [p for p in current if p in prev and current[p] != prev[p]]
    return added, modified, deleted, current


def _module_of(path: str) -> str:
    parts = path.split("/")
    return parts[0] if len(parts) > 1 else "_root"


async def run_update(project_id: int) -> dict:
    """Refresh the source, find changed files, and patch only affected doc pages."""
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
        "Pulling latest…" if project.source_type == "git" else "Re-reading local path…",
    )
    new_sha = prepare_source(project)

    _set_status(project_id, "analyzing", "Diffing against last analysis…")
    added, modified, deleted, current_hashes = _diff_against_db(project)
    current_files = walk_repo(working_path(project))

    if not (added or modified or deleted):
        code_graph = build_code_graph(current_files)
        with session_scope() as s:
            persist_code_graph(s, project_id, code_graph)
        _set_status(project_id, "ready", "No changes detected")
        return {"added": [], "modified": [], "deleted": [], "patched_pages": []}

    _set_status(project_id, "analyzing", "Rebuilding code graph…")
    code_graph = build_code_graph(current_files)

    llm = get_provider(provider_name, llm_config)

    _set_status(project_id, "analyzing", f"Summarizing {len(added) + len(modified)} changed files…")
    walked_changed, new_summaries = await _summarize_files_by_path(
        llm, project, added + modified,
    )

    # Build change descriptions per module
    affected_modules: set[str] = set()
    for path in added + modified + deleted:
        affected_modules.add(_module_of(path))

    # Patch each affected module page
    out = docs_dir(project_id)
    patched: list[str] = []

    for module in affected_modules:
        slug = _module_slug(module)
        page_path = out / f"{slug}.md"
        change_lines = []
        for path in added:
            if _module_of(path) == module:
                change_lines.append(
                    f"### Added: `{path}`\n\n{new_summaries.get(path, '_no summary_')}"
                )
        for path in modified:
            if _module_of(path) == module:
                change_lines.append(
                    f"### Modified: `{path}`\n\n{new_summaries.get(path, '_no summary_')}"
                )
        for path in deleted:
            if _module_of(path) == module:
                change_lines.append(f"### Removed: `{path}`")

        changes_text = "\n\n".join(change_lines) or "_no per-file changes_"

        if page_path.exists():
            existing = page_path.read_text(encoding="utf-8")
            updated = await llm.generate(
                DOC_PATCH_USER.format(existing=existing, changes=changes_text),
                system=DOC_PATCH_SYSTEM,
                max_tokens=1800,
            )
        else:
            # Module didn't exist before — generate fresh from scratch using
            # the current files in that module.
            files = [f for f in walk_repo(working_path(project)) if _module_of(f.path) == module]
            missing = [f for f in files if f.path not in new_summaries]
            if missing:
                _, more = await _summarize_files_by_path(llm, project, [f.path for f in missing])
                new_summaries.update(more)
            updated = await generate_module_page(llm, module, files, new_summaries)

        write_doc(out, slug, updated)
        patched.append(slug)

    # Overview + architecture get patched too — they reference the modules
    _set_status(project_id, "analyzing", "Updating overview & architecture…")
    module_pages = {}
    for module in affected_modules:
        slug = _module_slug(module)
        fp = out / f"{slug}.md"
        if fp.exists():
            module_pages[module] = fp.read_text(encoding="utf-8")

    # Pull in untouched module pages too so the overview stays accurate
    with session_scope() as s:
        all_module_pages = (
            s.query(DocPage).filter(
                DocPage.project_id == project_id, DocPage.kind == "module"
            ).all()
        )
        for mp in all_module_pages:
            module = mp.title.replace("Module: ", "")
            if module in module_pages:
                continue
            fp = out / f"{mp.slug}.md"
            if fp.exists():
                module_pages[module] = fp.read_text(encoding="utf-8")

    overview = await generate_overview(llm, repo_name, module_pages)
    architecture = await generate_architecture(llm, repo_name, module_pages)
    write_doc(out, "overview", overview)
    write_doc(out, "architecture", architecture)
    patched.extend(["overview", "architecture"])

    # Persist file-hash state
    with session_scope() as s:
        records = (
            s.query(FileRecord).filter(FileRecord.project_id == project_id).all()
        )
        by_path = {r.path: r for r in records}

        for path in deleted:
            if path in by_path:
                s.delete(by_path[path])

        for path in added + modified:
            if path in by_path:
                by_path[path].sha256 = current_hashes[path]
                by_path[path].summary = new_summaries.get(path)
            else:
                s.add(FileRecord(
                    project_id=project_id, path=path,
                    sha256=current_hashes[path],
                    summary=new_summaries.get(path),
                ))

        persist_code_graph(s, project_id, code_graph)

        # Ensure DocPage records exist for any newly-created module pages
        existing_slugs = {
            d.slug for d in s.query(DocPage).filter(DocPage.project_id == project_id).all()
        }
        for module in affected_modules:
            slug = _module_slug(module)
            if slug not in existing_slugs:
                s.add(DocPage(
                    project_id=project_id, slug=slug,
                    title=f"Module: {module}", kind="module",
                    source_paths=json.dumps([]),
                ))

        p = s.get(Project, project_id)
        p.last_commit_sha = new_sha
        p.status = "ready"
        p.status_detail = (
            f"+{len(added)} ~{len(modified)} -{len(deleted)} files; "
            f"{len(patched)} pages updated"
        )
        s.add(RunEvent(project_id=project_id, kind="update"))

    return {
        "added": added, "modified": modified, "deleted": deleted,
        "patched_pages": patched,
    }
