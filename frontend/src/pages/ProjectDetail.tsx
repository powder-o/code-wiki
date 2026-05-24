import { useEffect, useState, useCallback } from "react";
import { Link, useParams, useNavigate, Routes, Route, useLocation } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { api, CodeGraph as CodeGraphData, DocPage, DocPageContent, Project } from "../api";
import CodeGraph from "../components/CodeGraph";
import ProjectGraph from "./ProjectGraph";

function statusDotClass(status: string): string {
  if (status === "ready" || status === "graph_ready") return "dot-ready";
  if (status === "analyzing" || status === "graphing") return "dot-analyzing";
  if (status === "error") return "dot-error";
  return "dot-created";
}

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
    if (!project || !["analyzing", "graphing"].includes(project.status)) return;
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [project?.status, refresh]);

  if (err) return <div className="error">Failed: {err}</div>;
  if (!project) return <div className="muted">Loading…</div>;

  const working = ["analyzing", "graphing"].includes(project.status);
  const hasDocs = docs.length > 0;
  const canGenerateDocs = !hasDocs && project.status === "graph_ready";
  const currentSlug = location.pathname.split(`/projects/${projectId}/`)[1] || "";

  async function onPrimaryAction() {
    try {
      if (canGenerateDocs) {
        await api.analyze(projectId);
      } else {
        await api.update(projectId);
      }
      refresh();
    } catch (e) {
      alert(`Action failed: ${e}`);
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
          <div className="muted small" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <span className="tag">{project.source_type === "local" ? "local" : "git"}</span>
            <span>{project.repo_url}</span>
            {project.source_type === "git" ? <span>· branch {project.branch}</span> : null}
            <span>· {project.llm_provider}</span>
          </div>
          <div className="muted small" style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
            <span className={`dot ${statusDotClass(project.status)}`} />
            <span>{project.status}</span>
            {project.status_detail ? <span>— {project.status_detail}</span> : null}
            {project.last_commit_sha
              ? <span>· @ {project.last_commit_sha.slice(0, 7)}</span>
              : null}
          </div>
        </div>
        <div className="project-actions">
          <button
            disabled={working || project.status === "created" || project.status === "error"}
            onClick={onPrimaryAction}
            className="btn"
          >
            {working ? "Working…" : canGenerateDocs ? "Generate documentation" : "Update docs"}
          </button>
          <button onClick={onDelete} className="btn btn-danger">Delete</button>
        </div>
      </div>

      {working && docs.length === 0 ? (
        <div className="empty">
          <p>
            {project.status === "graphing"
              ? "Building the code graph. Documentation can be generated after this finishes."
              : "Generating documentation. This can take a few minutes for large codebases."}
          </p>
          <p className="muted small">{project.status_detail}</p>
        </div>
      ) : (
        <div className="doc-layout">
          <aside className="doc-sidebar">
            <Sidebar docs={docs} projectId={projectId} currentSlug={currentSlug} />
          </aside>
          <section className="doc-content">
            <Routes>
              <Route index element={<DefaultDocLoader projectId={projectId} docs={docs} />} />
              <Route path="graph" element={<ProjectGraph />} />
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
        <li className={currentSlug === "graph" ? "active" : ""}>
          <Link to={`/projects/${projectId}/graph`}>Graph</Link>
        </li>
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

function DefaultDocLoader({ projectId, docs }: { projectId: number; docs: DocPage[] }) {
  // Redirect to overview if it exists, else first doc
  const [target, setTarget] = useState<string | null>(null);
  useEffect(() => {
    if (docs.length === 0) return;
    const first = docs.find((d) => d.kind === "overview") || docs[0];
    if (first) setTarget(first.slug);
  }, [docs]);

  useEffect(() => {
    if (docs.length > 0) return;
    api.listDocs(projectId).then((nextDocs) => {
      const first = nextDocs.find((d) => d.kind === "overview") || nextDocs[0];
      if (first) setTarget(first.slug);
    });
  }, [projectId, docs.length]);

  if (!target) {
    return (
      <>
        <OverviewGraphPanel projectId={projectId} />
        <div className="empty">
          <p>Documentation has not been generated yet.</p>
          <p className="muted small">Review the graph first, then use Generate documentation when you are ready.</p>
        </div>
      </>
    );
  }
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
    <>
      {doc.kind === "overview" ? <OverviewGraphPanel projectId={projectId} /> : null}
      <article className="markdown">
        <h2>{doc.title}</h2>
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {doc.content}
        </ReactMarkdown>
      </article>
    </>
  );
}

function OverviewGraphPanel({ projectId }: { projectId: number }) {
  const [graph, setGraph] = useState<CodeGraphData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setGraph(null);
    setErr(null);
    api.getGraph(projectId)
      .then((nextGraph) => {
        if (active) setGraph(nextGraph);
      })
      .catch((e) => {
        if (active) setErr(String(e));
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  return (
    <section className="overview-graph-panel">
      <div className="overview-graph-header">
        <div>
          <h2>Code graph</h2>
          <p className="muted small">File and symbol relationships in this project.</p>
        </div>
        <Link to={`/projects/${projectId}/graph`} className="link-btn">Open full graph</Link>
      </div>
      {err ? (
        <div className="error">Graph unavailable: {err}</div>
      ) : !graph ? (
        <div className="muted">Loading graph…</div>
      ) : graph.nodes.length === 0 ? (
        <div className="muted">No graph data has been generated yet.</div>
      ) : (
        <CodeGraph data={graph} mode="compact" />
      )}
    </section>
  );
}
