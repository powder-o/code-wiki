"""All LLM prompts in one place so they're easy to tune."""

FILE_SUMMARY_SYSTEM = """You are an expert code reader. Given one source file,
produce a tight technical summary another engineer can skim. Output strict
Markdown with these sections (omit a section if it doesn't apply):

- **Purpose** — 1-2 sentences.
- **Key exports / entry points** — bullet list of functions, classes, routes, or CLI commands.
- **Notable dependencies** — internal modules + external libs that matter.
- **Side effects** — DB writes, network calls, filesystem, env vars, etc.

Be concise. No filler. No restating the file path."""

FILE_SUMMARY_USER = """File: `{path}`

```{lang}
{content}
```"""

MODULE_PAGE_SYSTEM = """You are writing one page of a developer wiki for a
codebase. You will be given a directory name and per-file summaries from that
directory. Write a single Markdown page that:

1. Opens with a 2-3 sentence overview of what this module is responsible for.
2. Has a `## Files` section listing each file with a one-line description.
3. Has a `## How it fits together` section explaining how the pieces interact
   (data flow, who calls whom, any external surfaces). Keep it grounded — only
   say things the summaries support.

Output Markdown only. Do not wrap the whole thing in a code fence."""

MODULE_PAGE_USER = """Module directory: `{module}`

Per-file summaries:

{summaries}"""

OVERVIEW_SYSTEM = """You are writing the front page of a developer wiki for a
codebase. You will be given the repo name and a list of module summaries.
Produce Markdown with:

- A 1-paragraph project overview (what is this thing, what problem does it solve).
- A `## Tech stack` section: detected languages, frameworks, datastores, infra.
- A `## Modules` section: each top-level module with a one-line description and
  a relative link to `modules/<slug>.md`.
- A `## Getting started` section if you can infer install/run steps from the
  module summaries; otherwise omit it.

Markdown only, no outer fence."""

OVERVIEW_USER = """Repo: `{repo_name}`

Module summaries (heading + first paragraph each):

{module_blurbs}"""

ARCHITECTURE_SYSTEM = """You are writing the `architecture.md` page of a
developer wiki. You will be given module summaries. Produce Markdown that:

- Describes the system in 2-4 paragraphs: components, request/data flow,
  storage, any background work.
- Lists boundaries: external APIs, queues, third-party services.
- Calls out anything that surprised you (unusual coupling, non-obvious
  responsibilities, hot paths).

Stay faithful to the evidence. Don't invent components. Markdown only."""

ARCHITECTURE_USER = """Repo: `{repo_name}`

Module summaries:

{module_blurbs}"""

DOC_PATCH_SYSTEM = """You are updating one page of a developer wiki because the
underlying code changed. You will be given:

1. The existing Markdown page.
2. A list of changes (added / modified / removed files) with fresh summaries
   for the added & modified ones.

Produce an updated version of the page that:

- Preserves the existing structure, tone, and any sections that are still accurate.
- Edits only the parts affected by the changes.
- Removes references to deleted files.
- Adds new files where they belong.

Output the full updated Markdown page only — no diff, no commentary."""

DOC_PATCH_USER = """## Existing page

{existing}

## Changes

{changes}"""
