from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db import (
    CodeCall,
    CodeEdge,
    CodeSymbol,
    DocPage,
    FileRecord,
    Project,
    init_db,
    session_scope,
)
from app.main import app
from app.repo.walker import walk_repo
from app.analysis.analyzer import run_graph_analysis
from app.codegraph.service import build_code_graph, persist_code_graph


def write_file(root, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def test_code_graph_resolves_cross_file_calls_across_supported_languages(tmp_path):
    write_file(
        tmp_path,
        "pkg/lib.py",
        """
        def load_user(user_id):
            return user_id
        """,
    )
    write_file(
        tmp_path,
        "pkg/app.py",
        """
        from pkg.lib import load_user

        def main():
            return load_user(42)
        """,
    )
    write_file(
        tmp_path,
        "ui/Card.tsx",
        """
        export function UserCard() {
          return <section>User</section>;
        }
        """,
    )
    write_file(
        tmp_path,
        "ui/App.tsx",
        """
        import { UserCard } from "./Card";

        export function App() {
          return <UserCard />;
        }
        """,
    )
    write_file(
        tmp_path,
        "java/com/example/Users.java",
        """
        package com.example;

        class Users {
          static String findUser() {
            return "Ada";
          }
        }
        """,
    )
    write_file(
        tmp_path,
        "java/com/example/App.java",
        """
        package com.example;

        class App {
          void run() {
            Users.findUser();
          }
        }
        """,
    )

    graph = build_code_graph(walk_repo(tmp_path))

    edges = {(edge.source_path, edge.target_path): set(edge.symbols) for edge in graph.edges}
    assert "load_user" in edges[("pkg/lib.py", "pkg/app.py")]
    assert "UserCard" in edges[("ui/Card.tsx", "ui/App.tsx")]
    assert "findUser" in edges[("java/com/example/Users.java", "java/com/example/App.java")]

    symbol = next(s for s in graph.symbols if s.file_path == "pkg/lib.py" and s.name == "load_user")
    assert symbol.language == "python"
    assert symbol.start_line == 1


def test_code_graph_drops_ambiguous_symbols_and_unconnected_html_css_nodes(tmp_path):
    write_file(tmp_path, "a.py", "def render():\n    return 'a'")
    write_file(tmp_path, "b.py", "def render():\n    return 'b'")
    write_file(tmp_path, "consumer.py", "def main():\n    return render()")
    write_file(tmp_path, "index.html", "<main class='app'></main>")
    write_file(tmp_path, "styles.css", ".app { color: red; }")

    graph = build_code_graph(walk_repo(tmp_path))

    assert all("render" not in edge.symbols for edge in graph.edges)
    node_ids = {node.id for node in graph.nodes}
    assert "index.html" not in node_ids
    assert "styles.css" not in node_ids


def test_graph_endpoint_returns_persisted_file_nodes_and_edges(tmp_path):
    init_db()
    write_file(tmp_path, "defs.py", "def answer():\n    return 42")
    write_file(tmp_path, "caller.py", "from defs import answer\n\nvalue = answer()")
    graph = build_code_graph(walk_repo(tmp_path))

    with session_scope() as s:
        project = Project(
            name="graph endpoint test",
            source_type="local",
            repo_url=str(tmp_path),
            branch="main",
            llm_provider="gemini",
            status="ready",
        )
        s.add(project)
        s.flush()
        project_id = project.id
        persist_code_graph(s, project_id, graph)

    try:
        response = TestClient(app).get(f"/api/projects/{project_id}/graph")
        assert response.status_code == 200
        payload = response.json()
        assert payload["nodes"] == [
            {
                "id": "defs.py",
                "label": "defs.py",
                "language": "python",
                "symbol_count": 1,
            },
            {
                "id": "caller.py",
                "label": "caller.py",
                "language": "python",
                "symbol_count": 0,
            },
        ]
        assert payload["links"] == [
            {
                "source": "defs.py",
                "target": "caller.py",
                "weight": 1,
                "symbols": ["answer"],
            }
        ]
    finally:
        with session_scope() as s:
            for model in (CodeEdge, CodeCall, CodeSymbol, Project):
                rows = s.query(model).filter(model.project_id == project_id).all() if model is not Project else [s.get(Project, project_id)]
                for row in rows:
                    if row is not None:
                        s.delete(row)


def test_graph_analysis_builds_graph_without_creating_documentation_baseline(tmp_path):
    init_db()
    write_file(tmp_path, "defs.py", "def answer():\n    return 42")
    write_file(tmp_path, "caller.py", "from defs import answer\n\nvalue = answer()")

    with session_scope() as s:
        project = Project(
            name="graph first workflow",
            source_type="local",
            repo_url=str(tmp_path),
            branch="main",
            llm_provider="gemini",
            status="created",
        )
        s.add(project)
        s.flush()
        project_id = project.id

    try:
        run_graph_analysis(project_id)

        with session_scope() as s:
            project = s.get(Project, project_id)
            assert project.status == "graph_ready"
            assert "2 files" in project.status_detail
            assert s.query(CodeEdge).filter(CodeEdge.project_id == project_id).count() == 1
            assert s.query(DocPage).filter(DocPage.project_id == project_id).count() == 0
            assert s.query(FileRecord).filter(FileRecord.project_id == project_id).count() == 0
    finally:
        with session_scope() as s:
            project = s.get(Project, project_id)
            if project is not None:
                s.delete(project)
