import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Project } from "../api";

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
        <p>Connect a Git repo to generate its wiki.</p>
        <Link to="/new" className="btn btn-primary">+ New project</Link>
      </div>
    );
  }

  return (
    <div>
      <h1>Projects</h1>
      <ul className="project-list">
        {projects.map((p) => (
          <li key={p.id}>
            <Link to={`/projects/${p.id}`} className="project-card">
              <div className="project-card-head">
                <strong>{p.name}</strong>
                <span className={`status status-${p.status}`}>{p.status}</span>
              </div>
              <div className="muted small">
                <span className="tag">{p.source_type === "local" ? "local" : "git"}</span>
                {" "}{p.repo_url}
              </div>
              <div className="muted small">
                {p.llm_provider}
                {p.source_type === "git" ? ` · branch ${p.branch}` : ""}
                {p.status_detail ? ` · ${p.status_detail}` : ""}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
