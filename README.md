# Code Wiki — POC

An AI-native documentation engine for codebases. Point it at a Git repo, it
walks the code, has an LLM summarize each file, then generates a navigable
wiki (overview, architecture, per-module pages) as Markdown. Re-run later and
it diffs against the last analyzed commit and **updates** affected pages
instead of regenerating from scratch.

Two pluggable LLM providers ship out of the box:

- **Azure OpenAI** — GPT-4.1 mini
- **Google Gemini** — 2.5 Flash

## Layout

```
backend/          FastAPI + SQLite + analysis pipeline
  app/
    llm/          LLMProvider ABC + Azure OpenAI + Gemini adapters
    repo/         Git clone/pull + file walker
    analysis/     Per-file summaries, doc generation, incremental updater
    api/          REST routes
frontend/         Vite + React + react-markdown
```

## How it works

**Initial analysis:**
1. `git clone --depth 1` the repo into `data/repos/<project_id>`
2. Walk the tree, filter to source files (configurable extensions, skip
   `node_modules`/`.venv`/etc), skip files > 200 KB
3. Per-file LLM summary (purpose, exports, deps, side effects)
4. Group files by top-level directory → one module page per group
5. Aggregate module summaries → `overview.md` + `architecture.md`

**Incremental update:**
1. `git pull`, walk again, hash each file
2. Diff hashes against `FileRecord` rows in SQLite → added / modified / deleted
3. Re-summarize only changed files
4. For each module page that owns a changed file: feed the LLM the existing
   page + change list, ask it to emit an updated version preserving structure
5. Regenerate `overview.md` + `architecture.md` from the (mostly cached)
   module pages

State stored in SQLite: `projects`, `files` (path → sha256 + summary),
`doc_pages`. Markdown files live on disk under `data/projects/<id>/docs/`.

## Running it

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in credentials for at least one provider
uvicorn app.main:app --reload --port 8000
```

API docs at <http://localhost:8000/docs>.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The dev server proxies `/api/*` to the backend.

## Creating a project

1. Click **+ New project**
2. Enter a name, the repo URL (`https://github.com/owner/repo.git`), branch,
   and pick a provider
3. (Optional) "Show advanced" lets you supply per-project credentials as a
   JSON blob — useful if you don't want to set them globally in `.env`
4. Submit → analysis kicks off in the background; the detail page polls
   every 2.5s and renders the doc tree when it's ready

For private repos: include credentials in the URL itself, e.g.
`https://oauth2:GLPAT_xxx@gitlab.com/org/repo.git` or
`https://USER:TOKEN@github.com/owner/repo.git`. The POC has no secret store.

## POC limitations (on purpose)

- No auth, no multi-tenant isolation
- No webhooks — updates are manual (click "Update docs")
- Background work uses FastAPI `BackgroundTasks`; for real workloads swap in
  Celery/RQ/arq
- Sync git via `gitpython`; large repos will be slow
- Source-text truncated to 12 KB per file before sending to the LLM
- Module grouping is "top-level directory", which is crude but readable; a
  real version would use language-aware module detection
- The doc-patch prompt trusts the LLM to preserve unchanged sections; a
  safer version would do section-level diffs

## Pluggable LLMs

Adding a third provider is two files:

1. Implement `LLMProvider.generate()` in `backend/app/llm/your_provider.py`
2. Wire it into `backend/app/llm/factory.py`

The prompts in `backend/app/analysis/prompts.py` are model-agnostic.
