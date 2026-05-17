from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Storage
    data_dir: Path = Path("./data")

    # Azure OpenAI defaults (can also be set per-project)
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str = "gpt-4.1-mini"
    azure_openai_api_version: str = "2024-08-01-preview"

    # Gemini defaults
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # Analysis limits
    max_file_bytes: int = 200_000
    max_files_per_run: int = 500

    @property
    def repos_dir(self) -> Path:
        p = self.data_dir / "repos"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def projects_dir(self) -> Path:
        p = self.data_dir / "projects"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "codewiki.db"


settings = Settings()
