from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SymbolDef:
    file_path: str
    name: str
    kind: str
    language: str
    start_line: int
    end_line: int
    signature: str | None = None


@dataclass(frozen=True)
class CallSite:
    file_path: str
    name: str
    language: str
    start_line: int
    context: str | None = None


@dataclass(frozen=True)
class CodeNode:
    id: str
    label: str
    language: str
    symbol_count: int


@dataclass(frozen=True)
class CodeEdgeData:
    source_path: str
    target_path: str
    symbols: tuple[str, ...]
    weight: int


@dataclass
class CodeGraph:
    nodes: list[CodeNode] = field(default_factory=list)
    symbols: list[SymbolDef] = field(default_factory=list)
    calls: list[CallSite] = field(default_factory=list)
    edges: list[CodeEdgeData] = field(default_factory=list)
