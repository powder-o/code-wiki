import json
from ..config import settings
from .base import LLMProvider
from .azure_openai import AzureOpenAIProvider
from .gemini import GeminiProvider


def get_provider(provider: str, llm_config: str | None = None) -> LLMProvider:
    """Build an LLMProvider. `llm_config` is an optional JSON string with
    per-project overrides (e.g. custom deployment or model)."""
    overrides = json.loads(llm_config) if llm_config else {}

    if provider == "azure_openai":
        return AzureOpenAIProvider(
            endpoint=overrides.get("endpoint") or settings.azure_openai_endpoint,
            api_key=overrides.get("api_key") or settings.azure_openai_api_key,
            deployment=overrides.get("deployment") or settings.azure_openai_deployment,
            api_version=overrides.get("api_version") or settings.azure_openai_api_version,
        )

    if provider == "gemini":
        return GeminiProvider(
            api_key=overrides.get("api_key") or settings.gemini_api_key,
            model=overrides.get("model") or settings.gemini_model,
        )

    raise ValueError(f"Unknown llm provider: {provider}")
