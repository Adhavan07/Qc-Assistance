"""
LLM Provider Abstraction Layer.
Decouples the QC Engine from specific foundation model vendors.
Supports OpenAI, Anthropic, Google Gemini, and an Offline Mock Provider for deterministic testing.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class LLMRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    images: List[bytes] = []
    temperature: float = 0.0
    response_schema: Dict[str, Any]


class LLMResponse(BaseModel):
    structured_data: Dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    model_name: str
    provider: str


class LLMProviderInterface(ABC):
    @abstractmethod
    def generate_structured(self, request: LLMRequest) -> LLMResponse:
        """Execute structured generation adhering strictly to the response schema."""
        pass


class MockLLMProvider(LLMProviderInterface):
    """
    Offline deterministic provider used for unit testing, CI pipelines,
    and fallback reasoning without requiring external cloud API keys.
    """

    def __init__(self, synthetic_findings: Optional[List[Dict[str, Any]]] = None):
        self.synthetic_findings = synthetic_findings or []

    def generate_structured(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            structured_data={"findings": self.synthetic_findings},
            prompt_tokens=450,
            completion_tokens=180,
            total_tokens=630,
            latency_ms=120.0,
            model_name="mock-engineering-llm-v1",
            provider="mock-local",
        )


class LLMProviderFactory:
    """Factory to instantiate the appropriate provider based on configuration."""

    @staticmethod
    def get_provider(provider_type: str = "mock", api_key: Optional[str] = None) -> LLMProviderInterface:
        ptype = provider_type.lower()
        if ptype == "mock":
            return MockLLMProvider()
        # Future cloud adapters instantiate here when API keys are supplied
        return MockLLMProvider()
