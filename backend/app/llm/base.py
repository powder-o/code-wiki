from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Tiny abstraction for chat-style LLMs used by Code Wiki.

    Implementations must be safe to call from async FastAPI handlers — wrap
    blocking SDK calls in `asyncio.to_thread` if the SDK is sync.
    """

    name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> str:
        ...
