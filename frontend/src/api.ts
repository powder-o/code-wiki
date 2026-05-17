export type LLMProviderName = "azure_openai" | "gemini";
export type SourceType = "git" | "local";

export interface Project {
  id: number;
  name: string;
  source_type: SourceType;
  repo_url: string;
  branch: string;
  llm_provider: string;
  status: string;
  status_detail: string | null;
  last_commit_sha: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocPage {
  slug: string;
  title: string;
  kind: string;
}

export interface DocPageContent extends DocPage {
  content: string;
}

export interface ProjectCreate {
  name: string;
  source_type: SourceType;
  repo_url: string;
  branch: string;
  llm_provider: LLMProviderName;
  llm_config?: Record<string, unknown>;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listProjects: () => fetch("/api/projects").then(json<Project[]>),
  getProject: (id: number) => fetch(`/api/projects/${id}`).then(json<Project>),
  createProject: (body: ProjectCreate) =>
    fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(json<Project>),
  deleteProject: (id: number) =>
    fetch(`/api/projects/${id}`, { method: "DELETE" }).then(json),
  analyze: (id: number) =>
    fetch(`/api/projects/${id}/analyze`, { method: "POST" }).then(json),
  update: (id: number) =>
    fetch(`/api/projects/${id}/update`, { method: "POST" }).then(json),
  listDocs: (id: number) =>
    fetch(`/api/projects/${id}/docs`).then(json<DocPage[]>),
  getDoc: (id: number, slug: string) =>
    fetch(`/api/projects/${id}/docs/${slug}`).then(json<DocPageContent>),
};
