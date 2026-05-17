import asyncio
import google.generativeai as genai

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("Gemini api_key is required")
        genai.configure(api_key=api_key)
        self._model_name = model

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> str:
        def _call():
            model = genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=system,
            )
            resp = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            return resp.text or ""

        return await asyncio.to_thread(_call)
