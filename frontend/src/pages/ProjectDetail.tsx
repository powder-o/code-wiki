import { useEffect, useState, useCallback } from "react";
import { Link, useParams, useNavigate, Routes, Route, useLocation } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { api, DocPage, DocPageContent, Project } from "../api";

export default function ProjectDetail() {
  const { id } = useParams();
  const projectId = Number(id);
  const nav = useNavigate();
  const location = useLocation();

  const [project, setProject] = useState<Project | null>(null);
  const [docs, setDocs] = useState<DocPage[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [p, d] = await Promise.all([
        api.getProject(projectId),
        api.listDocs(projectId).catch(() => []),
      ]);
      setProject(p);
      setDocs(d);
    } catch (e) {
      setErr(String(e));
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while analysis is running
  useEffect(() => {
    if (project?.status !== "analyzing") return;
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [project?.status, refresh]);

  if (err) return <div className="error">Failed: {err}</div>;
  if (!project) return <div className="muted">Loading…</div>;

  const analyzing = project.status === "analyzing";
  const currentSlug = location.pathname.split(`/projects/${projectId}/`)[1] || "";

  async function onUpdate() {
    try {
      await api.update(projectId);
      refresh();
    } catch (e) {
      alert(`Update failed: ${e}`);
    }
  }

  async function onDelete() {
    if (!confirm("Delete this project and all its docs?")) return;
    await api.deleteProject(projectId);
    nav("/");
  }

  return (
    <div className="project-detail">
      <div className="project-header">
        <div>
          <h1>{project.name}</h1>
          <div className="muted small">
            {project.repo_url} · branch {project.branch} · {project.llm_provider}
          </div>
          <div className="muted small">
            <span className={`status status-${project.status}`}>{project.status}</span>
            {project.status_detail ? ` — ${project.status_detail}` : ""}
            {project.last_commit_sha
              ? ` · @ ${project.last_commit_sha.slice(0, 7)}`
              : ""}
          </div>
        </div>
        <div className="project-actions">
          <button disabled={analyzing} onClick={onUpdate} className="btn">
            {analyzing ? "Working…" : "Update docs"}
          </button>
          <button onClick={onDelete} className="btn btn-danger">Delete</button>
        </div>
      </div>

      {analyzing && docs.length === 0 ? (
        <div className="empty">
          <p>Analyzing the repo. This can take a few minutes for large codebases.</p>
          <p className="muted small">{project.status_detail}</p>
        </div>
      ) : (
        <div className="doc-layout">
          <aside className="doc-sidebar">
            <Sidebar docs={docs} projectId={projectId} currentSlug={currentSlug} />
          </aside>
          <section className="doc-content">
            <Routes>
              <Route index element={<DefaultDocLoader projectId={projectId} />} />
              <Route path="*" element={<DocLoader projectId={projectId} />} />
            </Routes>
          </section>
        </div>
      )}
    </div>
  );
}

function Sidebar({
  docs, projectId, currentSlug,
}: { docs: DocPage[]; projectId: number; currentSlug: string }) {
  const overview = docs.find((d) => d.kind === "overview");
  const architecture = docs.find((d) => d.kind === "architecture");
  const modules = docs.filter((d) => d.kind === "module");

  function link(d: DocPage) {
    return (
      <li key={d.slug} className={currentSlug === d.slug ? "active" : ""}>
        <Link to={`/projects/${projectId}/${d.slug}`}>{d.title}</Link>
      </li>
    );
  }

  return (
    <nav>
      <ul>
        {overview && link(overview)}
        {architecture && link(architecture)}
      </ul>
      {modules.length > 0 && (
        <>
          <div className="sidebar-section">Modules</div>
          <ul>{modules.map(link)}</ul>
        </>
      )}
    </nav>
  );
}

function DefaultDocLoader({ projectId }: { projectId: number }) {
  // Redirect to overview if it exists, else first doc
  const [target, setTarget] = useState<string | null>(null);
  useEffect(() => {
    api.listDocs(projectId).then((docs) => {
      const first = docs.find((d) => d.kind === "overview") || docs[0];
      if (first) setTarget(first.slug);
    });
  }, [projectId]);
  if (!target) return <div className="muted">No docs yet.</div>;
  return <DocBySlug projectId={projectId} slug={target} />;
}

function DocLoader({ projectId }: { projectId: number }) {
  const loc = useLocation();
  const slug = loc.pathname.split(`/projects/${projectId}/`)[1];
  return <DocBySlug projectId={projectId} slug={slug} />;
}

function DocBySlug({ projectId, slug }: { projectId: number; slug: string }) {
  const [doc, setDoc] = useState<DocPageContent | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    setDoc(null);
    setErr(null);
    api.getDoc(projectId, slug).then(setDoc).catch((e) => setErr(String(e)));
  }, [projectId, slug]);

  if (err) return <div className="error">{err}</div>;
  if (!doc) return <div className="muted">Loading…</div>;
  return (
    <article className="markdown">
      <h2>{doc.title}</h2>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
        {doc.content}
      </ReactMarkdown>
    </article>
  );
}
