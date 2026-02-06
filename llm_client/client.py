from __future__ import annotations

import os
from typing import Optional

from groq import Groq

from config import llm_config


class LLMClient:
    """
    Groq-only LLM client for chat completions.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.model = model or llm_config.model
        self.temperature = temperature if temperature is not None else llm_config.temperature
        # Explicitly read API key from environment so it works both locally (.env)
        # and on hosts with managed secrets / env vars.
        api_key = os.getenv("GROQ_API_KEY")
        self._client = Groq(api_key=api_key) if api_key else Groq()

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
    ) -> str:
        """
        Perform a Groq chat completion request and return the response text.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""


# Shared default client
llm_client = LLMClient()
