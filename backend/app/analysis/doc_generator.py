from __future__ import annotations
from pathlib import Path
import re

from ..llm import LLMProvider
from ..repo.walker import WalkedFile, group_by_top_dir
from .prompts import (
    MODULE_PAGE_SYSTEM, MODULE_PAGE_USER,
    OVERVIEW_SYSTEM, OVERVIEW_USER,
    ARCHITECTURE_SYSTEM, ARCHITECTURE_USER,
)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-").lower()
    return s or "module"


def _format_summaries(files: list[WalkedFile], summaries: dict[str, str]) -> str:
    chunks = []
    for f in files:
        s = summaries.get(f.path, "_no summary_")
        chunks.append(f"### `{f.path}`\n\n{s}")
    return "\n\n".join(chunks)


def _first_paragraph(md: str) -> str:
    for block in md.strip().split("\n\n"):
        b = block.strip()
        if b and not b.startswith("#"):
            return b
    return md.strip()[:300]


async def generate_module_page(
    llm: LLMProvider, module: str, files: list[WalkedFile], summaries: dict[str, str]
) -> str:
    body = _format_summaries(files, summaries)
    return await llm.generate(
        MODULE_PAGE_USER.format(module=module, summaries=body),
        system=MODULE_PAGE_SYSTEM,
        max_tokens=1500,
    )


async def generate_overview(
    llm: LLMProvider, repo_name: str, module_pages: dict[str, str]
) -> str:
    blurbs = "\n\n".join(
        f"### `{m}`\n\n{_first_paragraph(page)}" for m, page in module_pages.items()
    )
    return await llm.generate(
        OVERVIEW_USER.format(repo_name=repo_name, module_blurbs=blurbs),
        system=OVERVIEW_SYSTEM,
        max_tokens=1200,
    )


async def generate_architecture(
    llm: LLMProvider, repo_name: str, module_pages: dict[str, str]
) -> str:
    blurbs = "\n\n".join(
        f"### `{m}`\n\n{_first_paragraph(page)}" for m, page in module_pages.items()
    )
    return await llm.generate(
        ARCHITECTURE_USER.format(repo_name=repo_name, module_blurbs=blurbs),
        system=ARCHITECTURE_SYSTEM,
        max_tokens=1500,
    )


def write_doc(docs_dir: Path, slug: str, content: str) -> Path:
    """Write a markdown file. Slug may contain `/` for nesting."""
    p = docs_dir / f"{slug}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def grouped_modules(files: list[WalkedFile]) -> dict[str, list[WalkedFile]]:
    """Wrapper kept here so callers don't need to import the walker."""
    return group_by_top_dir(files)
