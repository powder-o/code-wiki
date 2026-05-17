from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


LLMProviderName = Literal["azure_openai", "gemini"]
SourceType = Literal["git", "local"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    source_type: SourceType = "git"
    repo_url: str = Field(min_length=1)  # git URL or absolute local path
    branch: str = "main"
    llm_provider: LLMProviderName
    llm_config: dict | None = None  # optional per-project overrides


class ProjectOut(BaseModel):
    id: int
    name: str
    source_type: str
    repo_url: str
    branch: str
    llm_provider: str
    status: str
    status_detail: str | None
    last_commit_sha: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocPageOut(BaseModel):
    slug: str
    title: str
    kind: str

    class Config:
        from_attributes = True


class DocPageContent(BaseModel):
    slug: str
    title: str
    kind: str
    content: str


class UpdateResult(BaseModel):
    added: list[str]
    modified: list[str]
    deleted: list[str]
    patched_pages: list[str]
