import json
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..db import session_scope, Project, DocPage
from ..schemas import ProjectCreate, ProjectOut, DocPageOut, DocPageContent, UpdateResult
from ..analysis.analyzer import run_initial_analysis, docs_dir
from ..analysis.updater import run_update

log = logging.getLogger("codewiki.api")
router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects():
    with session_scope() as s:
        return [ProjectOut.model_validate(p) for p in s.query(Project).order_by(Project.id.desc()).all()]


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate):
    with session_scope() as s:
        p = Project(
            name=body.name,
            repo_url=body.repo_url,
            branch=body.branch,
            llm_provider=body.llm_provider,
            llm_config=json.dumps(body.llm_config) if body.llm_config else None,
            status="created",
        )
        s.add(p)
        s.flush()
        return ProjectOut.model_validate(p)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(404, "Project not found")
        return ProjectOut.model_validate(p)


@router.delete("/{project_id}")
def delete_project(project_id: int):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(404, "Project not found")
        s.delete(p)
    return {"ok": True}


# ---- analyze / update -------------------------------------------------------


async def _analyze_task(project_id: int):
    try:
        await run_initial_analysis(project_id)
    except Exception as e:
        log.exception("initial analysis failed for project %s", project_id)
        with session_scope() as s:
            p = s.get(Project, project_id)
            if p:
                p.status = "error"
                p.status_detail = str(e)


async def _update_task(project_id: int):
    try:
        await run_update(project_id)
    except Exception as e:
        log.exception("update failed for project %s", project_id)
        with session_scope() as s:
            p = s.get(Project, project_id)
            if p:
                p.status = "error"
                p.status_detail = str(e)


@router.post("/{project_id}/analyze")
def analyze(project_id: int, bg: BackgroundTasks):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(404, "Project not found")
        if p.status == "analyzing":
            raise HTTPException(409, "Project is already being analyzed")
        p.status = "analyzing"
        p.status_detail = "Queued…"
    bg.add_task(_analyze_task, project_id)
    return {"ok": True, "status": "analyzing"}


@router.post("/{project_id}/update", response_model=None)
def update(project_id: int, bg: BackgroundTasks):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(404, "Project not found")
        if p.status == "analyzing":
            raise HTTPException(409, "Project is already being analyzed")
        if not p.last_commit_sha:
            raise HTTPException(
                400,
                "Project has not been analyzed yet — run /analyze first",
            )
        p.status = "analyzing"
        p.status_detail = "Queued update…"
    bg.add_task(_update_task, project_id)
    return {"ok": True, "status": "analyzing"}


# ---- docs -------------------------------------------------------------------


@router.get("/{project_id}/docs", response_model=list[DocPageOut])
def list_docs(project_id: int):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(404, "Project not found")
        pages = s.query(DocPage).filter(DocPage.project_id == project_id).order_by(DocPage.slug).all()
        return [DocPageOut.model_validate(d) for d in pages]


@router.get("/{project_id}/docs/{slug:path}", response_model=DocPageContent)
def get_doc(project_id: int, slug: str):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if not p:
            raise HTTPException(404, "Project not found")
        page = (
            s.query(DocPage)
            .filter(DocPage.project_id == project_id, DocPage.slug == slug)
            .first()
        )
        if not page:
            raise HTTPException(404, "Doc page not found")
        fp = docs_dir(project_id) / f"{slug}.md"
        if not fp.exists():
            raise HTTPException(404, "Doc file missing on disk")
        return DocPageContent(
            slug=page.slug, title=page.title, kind=page.kind,
            content=fp.read_text(encoding="utf-8"),
        )
