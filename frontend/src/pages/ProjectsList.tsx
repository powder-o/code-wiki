import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Project } from "../api";
import Sparkline from "../components/Sparkline";

const STATUS_LABELS: Record<string, string> = {
  ready: "ready",
  graph_ready: "graph ready",
  analyzing: "working",
  graphing: "building graph",
  error: "error",
  created: "new",
};

function statusDotClass(status: string): string {
  if (status === "ready" || status === "graph_ready") return "dot-ready";
  if (status === "analyzing" || status === "graphing") return "dot-analyzing";
  if (status === "error") return "dot-error";
  return "dot-created";
}

function shortenRepo(url: string): string {
  // strip protocol + .git, collapse user-prefix on local paths
  return url.replace(/^https?:\/\//, "").replace(/\.git$/, "");
}

export default function ProjectsList() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div className="error">Failed to load: {err}</div>;
  if (!projects) return <div className="muted">Loading…</div>;

  if (projects.length === 0) {
    return (
      <div className="empty">
        <h2>No projects yet</h2>
        <p>Connect a Git repo or point at a local path to generate its wiki.</p>
        <div style={{ marginTop: 16 }}>
          <Link to="/new" className="btn btn-primary">+ New project</Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1>Projects</h1>
      <ul className="project-list">
        {projects.map((p) => (
          <li key={p.id}>
            <Link to={`/projects/${p.id}`} className="project-row">
              <div className="project-row-main">
                <span
                  className={`dot ${statusDotClass(p.status)}`}
                  title={STATUS_LABELS[p.status] ?? p.status}
                />
                <span className="project-row-name">{p.name}</span>
                <span className="project-row-meta">{shortenRepo(p.repo_url)}</span>
              </div>
              <Sparkline data={p.activity_7d ?? Array(7).fill(0)} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
