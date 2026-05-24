import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Project } from "../api";
import type { CodeGraph as CodeGraphData } from "../api";
import CodeGraph from "../components/CodeGraph";

export default function ProjectGraph() {
  const { id } = useParams();
  const projectId = Number(id);
  const [project, setProject] = useState<Project | null>(null);
  const [graph, setGraph] = useState<CodeGraphData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    try {
      const [projectResult, graphResult] = await Promise.all([
        api.getProject(projectId),
        api.getGraph(projectId),
      ]);
      setProject(projectResult);
      setGraph(graphResult);
    } catch (e) {
      setErr(String(e));
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!project || !["graphing", "analyzing"].includes(project.status)) return;
    const timer = window.setInterval(refresh, 2500);
    return () => window.clearInterval(timer);
  }, [project?.status, project, refresh]);

  if (err) return <div className="error">Failed: {err}</div>;
  if (!project || !graph) return <div className="muted">Loading graph…</div>;

  return (
    <div className="graph-page">
      <div className="graph-page-header">
        <div>
          <h2>Code graph</h2>
          <p className="muted small">
            {project.name} · {graph.nodes.length} nodes · {graph.links.length} links
            {project.status_detail ? ` · ${project.status_detail}` : ""}
          </p>
        </div>
      </div>
      {graph.nodes.length === 0 ? (
        <div className="empty">
          <p>
            {project.status === "graphing"
              ? "Building the graph. This should only take a moment."
              : "No graph data has been generated for this project yet."}
          </p>
        </div>
      ) : (
        <CodeGraph data={graph} mode="full" />
      )}
    </div>
  );
}
