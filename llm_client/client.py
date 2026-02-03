from __future__ import annotations

import os
from typing import Literal, Optional

import requests
from openai import OpenAI
from groq import Groq

from config import llm_config


Provider = Literal["openai", "groq", "ollama"]


class LLMClient:
    """
    Simple pluggable LLM client supporting OpenAI, Groq, and Ollama.
    """

    def __init__(
        self,
        provider: Provider | None = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.provider: Provider = (provider or llm_config.provider)  # type: ignore[assignment]
        self.model = model or llm_config.model
        self.temperature = temperature if temperature is not None else llm_config.temperature

        if self.provider == "openai":
            self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.provider == "groq":
            self._client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            # Ollama uses HTTP API; client is not required
            self._client = None

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
    ) -> str:
        """
        Perform a chat completion request and return the response text.
        """
        if self.provider == "openai":
            response = self._client.chat.completions.create(  # type: ignore[union-attr]
                model=self.model,
                temperature=self.temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        if self.provider == "groq":
            response = self._client.chat.completions.create(  # type: ignore[union-attr]
                model=self.model,
                temperature=self.temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        # Ollama HTTP API
        url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/v1/chat/completions")
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# Shared default client
llm_client = LLMClient()

