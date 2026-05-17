import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, LLMProviderName } from "../api";

export default function AddProject() {
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [provider, setProvider] = useState<LLMProviderName>("azure_openai");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [overrides, setOverrides] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErr(null);
    try {
      let llm_config: Record<string, unknown> | undefined;
      if (showAdvanced && overrides.trim()) {
        try {
          llm_config = JSON.parse(overrides);
        } catch {
          throw new Error("Advanced overrides must be valid JSON");
        }
      }
      const project = await api.createProject({
        name, repo_url: repoUrl, branch, llm_provider: provider, llm_config,
      });
      await api.analyze(project.id);
      nav(`/projects/${project.id}`);
    } catch (e) {
      setErr(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="form">
      <h1>New project</h1>

      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required
               placeholder="my-service" />
      </label>

      <label>
        Repo URL
        <input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} required
               placeholder="https://github.com/owner/repo.git" />
        <span className="hint">For private repos, include credentials in the URL (e.g. https://oauth2:TOKEN@…)</span>
      </label>

      <label>
        Branch
        <input value={branch} onChange={(e) => setBranch(e.target.value)} />
      </label>

      <label>
        LLM provider
        <select value={provider} onChange={(e) => setProvider(e.target.value as LLMProviderName)}>
          <option value="azure_openai">Azure OpenAI · gpt-4.1-mini</option>
          <option value="gemini">Google Gemini · 2.5-flash</option>
        </select>
      </label>

      <button type="button" className="link-btn"
              onClick={() => setShowAdvanced((v) => !v)}>
        {showAdvanced ? "Hide" : "Show"} advanced (per-project credential overrides)
      </button>

      {showAdvanced && (
        <label>
          Overrides (JSON)
          <textarea
            rows={6}
            value={overrides}
            onChange={(e) => setOverrides(e.target.value)}
            placeholder={
              provider === "azure_openai"
                ? '{ "endpoint": "...", "api_key": "...", "deployment": "gpt-4.1-mini" }'
                : '{ "api_key": "...", "model": "gemini-2.5-flash" }'
            }
          />
          <span className="hint">Optional — falls back to backend env vars if omitted.</span>
        </label>
      )}

      {err && <div className="error">{err}</div>}

      <div className="form-actions">
        <button disabled={submitting} className="btn btn-primary">
          {submitting ? "Creating…" : "Create & analyze"}
        </button>
      </div>
    </form>
  );
}
