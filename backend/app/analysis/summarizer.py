import asyncio
from pathlib import Path

from ..llm import LLMProvider
from ..repo.walker import WalkedFile, read_text
from .prompts import FILE_SUMMARY_SYSTEM, FILE_SUMMARY_USER


LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "jsx", ".ts": "typescript",
    ".tsx": "tsx", ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby",
    ".php": "php", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".kt": "kotlin", ".swift": "swift", ".scala": "scala",
    ".sh": "bash", ".bash": "bash", ".sql": "sql",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".vue": "vue", ".svelte": "svelte",
}


def _lang(path: str) -> str:
    return LANG_BY_EXT.get(Path(path).suffix.lower(), "")


async def summarize_file(llm: LLMProvider, f: WalkedFile) -> str:
    content = read_text(f.abs_path)
    if not content.strip():
        return "_Empty or unreadable file._"
    prompt = FILE_SUMMARY_USER.format(path=f.path, lang=_lang(f.path), content=content)
    return await llm.generate(prompt, system=FILE_SUMMARY_SYSTEM, max_tokens=400)


async def summarize_many(
    llm: LLMProvider, files: list[WalkedFile], concurrency: int = 4
) -> dict[str, str]:
    """Summarize a batch of files concurrently. Returns {path: summary}."""
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, str] = {}

    async def _one(f: WalkedFile):
        async with sem:
            try:
                results[f.path] = await summarize_file(llm, f)
            except Exception as e:
                results[f.path] = f"_Summary failed: {e}_"

    await asyncio.gather(*(_one(f) for f in files))
    return results
