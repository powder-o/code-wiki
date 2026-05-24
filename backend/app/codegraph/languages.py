from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from tree_sitter_language_pack import get_parser


EXTENSION_LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "tsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".java": "java",
}


DISPLAY_LANGUAGE: dict[str, str] = {
    "tsx": "typescript",
}


def language_for_path(path: str) -> str | None:
    language = EXTENSION_LANGUAGES.get(Path(path).suffix.lower())
    if language is None:
        return None
    return DISPLAY_LANGUAGE.get(language, language)


def parser_language_for_path(path: str) -> str | None:
    return EXTENSION_LANGUAGES.get(Path(path).suffix.lower())


@lru_cache(maxsize=None)
def parser_for_language(language: str):
    return get_parser(language)
