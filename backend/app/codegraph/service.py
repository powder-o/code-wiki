from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..db import CodeCall, CodeEdge, CodeSymbol, session_scope
from ..repo.walker import WalkedFile
from .extractor import extract_file
from .models import CodeGraph
from .resolver import resolve_graph


def build_code_graph(files: list[WalkedFile]) -> CodeGraph:
    extractions = []
    for file in files:
        extraction = extract_file(file)
        if extraction is not None:
            extractions.append(extraction)
    return resolve_graph(extractions)


def persist_code_graph(session: Session, project_id: int, graph: CodeGraph) -> None:
    for model in (CodeEdge, CodeCall, CodeSymbol):
        for row in session.query(model).filter(model.project_id == project_id).all():
            session.delete(row)
    session.flush()

    for symbol in graph.symbols:
        session.add(CodeSymbol(
            project_id=project_id,
            file_path=symbol.file_path,
            name=symbol.name,
            kind=symbol.kind,
            language=symbol.language,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            signature=symbol.signature,
        ))
    for call in graph.calls:
        session.add(CodeCall(
            project_id=project_id,
            file_path=call.file_path,
            name=call.name,
            language=call.language,
            start_line=call.start_line,
            context=call.context,
        ))
    for edge in graph.edges:
        session.add(CodeEdge(
            project_id=project_id,
            source_path=edge.source_path,
            target_path=edge.target_path,
            symbols_json=json.dumps(list(edge.symbols)),
            weight=edge.weight,
        ))


def graph_payload_for_project(project_id: int) -> dict:
    with session_scope() as session:
        symbols = (
            session.query(CodeSymbol)
            .filter(CodeSymbol.project_id == project_id)
            .all()
        )
        calls = (
            session.query(CodeCall)
            .filter(CodeCall.project_id == project_id)
            .all()
        )
        edges = (
            session.query(CodeEdge)
            .filter(CodeEdge.project_id == project_id)
            .order_by(CodeEdge.source_path, CodeEdge.target_path)
            .all()
        )

        connected = {edge.source_path for edge in edges} | {edge.target_path for edge in edges}
        symbol_counts: dict[str, int] = {}
        languages: dict[str, str] = {}
        for symbol in symbols:
            symbol_counts[symbol.file_path] = symbol_counts.get(symbol.file_path, 0) + 1
            languages.setdefault(symbol.file_path, symbol.language)
        for call in calls:
            languages.setdefault(call.file_path, call.language)

        nodes = [
            {
                "id": path,
                "label": path.rsplit("/", 1)[-1],
                "language": languages.get(path, "unknown"),
                "symbol_count": symbol_counts.get(path, 0),
            }
            for path in sorted(connected, key=lambda p: (-symbol_counts.get(p, 0), p))
        ]
        links = [
            {
                "source": edge.source_path,
                "target": edge.target_path,
                "weight": edge.weight,
                "symbols": json.loads(edge.symbols_json),
            }
            for edge in edges
        ]
        return {"nodes": nodes, "links": links}
