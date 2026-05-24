from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..repo.walker import WalkedFile, read_text
from .languages import language_for_path, parser_for_language, parser_language_for_path
from .models import CallSite, SymbolDef


@dataclass
class FileExtraction:
    file_path: str
    language: str
    symbols: list[SymbolDef]
    calls: list[CallSite]


def extract_file(file: WalkedFile) -> FileExtraction | None:
    parser_language = parser_language_for_path(file.path)
    display_language = language_for_path(file.path)
    if not parser_language or not display_language:
        return None
    if display_language in {"html", "css"}:
        return FileExtraction(file.path, display_language, [], [])

    source = read_text(file.abs_path)
    if not source.strip():
        return FileExtraction(file.path, display_language, [], [])

    parser = parser_for_language(parser_language)
    tree = parser.parse(source)
    root = tree.root_node()
    symbols: list[SymbolDef] = []
    calls: list[CallSite] = []

    for node in _walk(root):
        kind = node.kind()
        symbol = _symbol_from_node(file.path, display_language, source, node, kind)
        if symbol is not None:
            symbols.append(symbol)
        call = _call_from_node(file.path, display_language, source, node, kind)
        if call is not None:
            calls.append(call)

    return FileExtraction(file.path, display_language, _dedupe_symbols(symbols), _dedupe_calls(calls))


def _walk(node):
    yield node
    for i in range(node.child_count()):
        child = node.child(i)
        if child is not None:
            yield from _walk(child)


def _text(source: str, node) -> str:
    data = source.encode("utf-8")
    return data[node.start_byte():node.end_byte()].decode("utf-8", errors="ignore")


def _field_text(source: str, node, field: str) -> str | None:
    child = node.child_by_field_name(field)
    if child is None:
        return None
    return _text(source, child)


def _line(node) -> int:
    return node.start_position().row + 1


def _end_line(node) -> int:
    return node.end_position().row + 1


def _signature(source: str, node) -> str:
    first_line = _text(source, node).strip().splitlines()[0]
    return first_line[:200]


def _symbol_from_node(
    file_path: str, language: str, source: str, node, kind: str
) -> SymbolDef | None:
    name: str | None = None
    symbol_kind = "function"

    if language == "python":
        if kind == "function_definition":
            name = _field_text(source, node, "name")
        elif kind == "class_definition":
            name = _field_text(source, node, "name")
            symbol_kind = "class"

    elif language in {"javascript", "typescript"}:
        if kind == "function_declaration":
            name = _field_text(source, node, "name")
        elif kind == "method_definition":
            name = _field_text(source, node, "name")
            symbol_kind = "method"
        elif kind == "class_declaration":
            name = _field_text(source, node, "name")
            symbol_kind = "class"
        elif kind == "variable_declarator":
            value = node.child_by_field_name("value")
            if value is not None and value.kind() in {"arrow_function", "function"}:
                name = _field_text(source, node, "name")

    elif language == "java":
        if kind == "method_declaration":
            name = _field_text(source, node, "name")
            symbol_kind = "method"
        elif kind in {"class_declaration", "interface_declaration"}:
            name = _field_text(source, node, "name")
            symbol_kind = "class"

    if not name or not _is_symbol_name(name):
        return None
    return SymbolDef(
        file_path=file_path,
        name=name,
        kind=symbol_kind,
        language=language,
        start_line=_line(node),
        end_line=_end_line(node),
        signature=_signature(source, node),
    )


def _call_from_node(
    file_path: str, language: str, source: str, node, kind: str
) -> CallSite | None:
    name: str | None = None

    if language == "python" and kind == "call":
        name = _callable_name(source, node.child_by_field_name("function"))

    elif language in {"javascript", "typescript"}:
        if kind == "call_expression":
            name = _callable_name(source, node.child_by_field_name("function"))
        elif kind in {"jsx_self_closing_element", "jsx_opening_element"}:
            name = _field_text(source, node, "name")
            if name and not name[:1].isupper():
                name = None

    elif language == "java":
        if kind == "method_invocation":
            name = _field_text(source, node, "name")
        elif kind == "object_creation_expression":
            name = _field_text(source, node, "type")

    if not name or not _is_symbol_name(name) or _is_noise_name(name):
        return None
    return CallSite(
        file_path=file_path,
        name=name,
        language=language,
        start_line=_line(node),
        context=_signature(source, node),
    )


def _callable_name(source: str, node) -> str | None:
    if node is None:
        return None
    kind = node.kind()
    if kind in {"identifier", "property_identifier", "type_identifier"}:
        return _text(source, node)
    if kind in {"attribute", "member_expression"}:
        for field in ("attribute", "property"):
            value = _field_text(source, node, field)
            if value:
                return value
    return None


def _is_symbol_name(name: str) -> bool:
    return name.replace("_", "").replace("$", "").isalnum()


NOISE_NAMES = {
    "print", "len", "str", "int", "float", "list", "dict", "set", "tuple",
    "range", "map", "filter", "reduce", "open", "super", "console", "log",
    "String", "Integer", "System",
}


def _is_noise_name(name: str) -> bool:
    return name in NOISE_NAMES


def _dedupe_symbols(symbols: list[SymbolDef]) -> list[SymbolDef]:
    seen = set()
    out = []
    for s in symbols:
        key = (s.file_path, s.name, s.kind, s.start_line)
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _dedupe_calls(calls: list[CallSite]) -> list[CallSite]:
    seen = set()
    out = []
    for c in calls:
        key = (c.file_path, c.name, c.start_line)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out
