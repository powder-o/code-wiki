import asyncio
from openai import AzureOpenAI

from .base import LLMProvider


class AzureOpenAIProvider(LLMProvider):
    name = "azure_openai"

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-08-01-preview",
    ):
        if not endpoint or not api_key:
            raise ValueError("Azure OpenAI endpoint and api_key are required")
        self.deployment = deployment
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        def _call():
            resp = self._client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""

        return await asyncio.to_thread(_call)
