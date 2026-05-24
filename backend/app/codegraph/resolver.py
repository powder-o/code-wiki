from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .extractor import FileExtraction
from .models import CodeEdgeData, CodeGraph, CodeNode


def resolve_graph(extractions: list[FileExtraction]) -> CodeGraph:
    symbols = [s for e in extractions for s in e.symbols]
    calls = [c for e in extractions for c in e.calls]

    definitions_by_name: dict[str, list] = defaultdict(list)
    for symbol in symbols:
        definitions_by_name[symbol.name].append(symbol)

    edge_symbols: dict[tuple[str, str], set[str]] = defaultdict(set)
    for call in calls:
        candidates = definitions_by_name.get(call.name, [])
        candidate_files = {candidate.file_path for candidate in candidates}
        if len(candidate_files) != 1:
            continue
        definition = candidates[0]
        if definition.file_path == call.file_path:
            continue
        edge_symbols[(definition.file_path, call.file_path)].add(call.name)

    edges = [
        CodeEdgeData(source, target, tuple(sorted(names)), len(names))
        for (source, target), names in sorted(edge_symbols.items())
    ]

    connected_paths = {edge.source_path for edge in edges} | {edge.target_path for edge in edges}
    symbol_counts: dict[str, int] = defaultdict(int)
    languages: dict[str, str] = {}
    for extraction in extractions:
        languages[extraction.file_path] = extraction.language
    for symbol in symbols:
        symbol_counts[symbol.file_path] += 1

    nodes = [
        CodeNode(
            id=path,
            label=Path(path).name,
            language=languages.get(path, "unknown"),
            symbol_count=symbol_counts.get(path, 0),
        )
        for path in sorted(connected_paths, key=lambda p: (-symbol_counts.get(p, 0), p))
    ]

    return CodeGraph(nodes=nodes, symbols=symbols, calls=calls, edges=edges)
