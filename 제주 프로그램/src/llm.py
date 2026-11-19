"""LLM 제공자 추상화. 기본은 외부 호출 없는 mock, 센터 PC용 로컬(ollama) 선택 가능."""
import json
import os
import urllib.request
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    def complete(self, system: str, prompt: str) -> str: ...


class MockProvider(LLMProvider):
    name = "mock"

    def complete(self, system: str, prompt: str) -> str:
        # 프롬프트 끝의 [분석 결과] 블록을 쉬운 말로 되풀이하는 결정적 응답
        facts = prompt.split("[분석 결과]")[-1].strip()
        return "요약(mock 모델, 실제 AI 아님):\n" + facts


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, url: str, model: str):
        self.url, self.model = url.rstrip("/"), model

    def complete(self, system: str, prompt: str) -> str:
        body = json.dumps({"model": self.model, "system": system, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(self.url + "/api/generate", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["response"]


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI  # 선택 의존성: pip install openai (외부 API)

        self.client, self.model = OpenAI(api_key=api_key), model

    def complete(self, system: str, prompt: str) -> str:
        r = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return r.choices[0].message.content or ""


def get_provider(name: str | None = None) -> LLMProvider:
    name = (name or os.getenv("LLM_PROVIDER", "mock")).lower()
    if name == "ollama":
        return OllamaProvider(os.getenv("OLLAMA_URL", "http://localhost:11434"), os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    if name == "openai":
        return OpenAIProvider(os.environ["OPENAI_API_KEY"], os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    return MockProvider()
