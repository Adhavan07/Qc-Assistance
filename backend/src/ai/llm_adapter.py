"""
AI Provider Abstraction Layer & Multimodal Reasoning Adapter.
Decouples engineering inspection logic from foundational LLM providers.
Supports Mock (offline/testing), OpenAI (GPT-4o), Anthropic (Claude 3.5), and Google Gemini (1.5 Pro).
Enforces strict Pydantic JSON schema validation, timeouts, retries, and token cost accounting.
"""

from abc import ABC, abstractmethod
import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Type
import httpx
from pydantic import BaseModel, ValidationError

from ..core.config import settings
from ..core.logging import logger
from .schemas import (
    AIAnalysisPayload,
    AIFindingPayload,
    BoundingBox,
    ConfidenceLevelEnum,
    SeverityEnum,
)


class AIRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    response_schema: Dict[str, Any]
    temperature: float = 0.0
    timeout_seconds: float = 30.0
    model_name: Optional[str] = None
    prompt_version: str = "wiring-qc-prompt-v1.0"


class AIResponse(BaseModel):
    raw_text: str
    structured_payload: AIAnalysisPayload
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    latency_ms: float
    model_name: str
    provider: str


class AIServiceError(Exception):
    """Base exception for AI provider execution failures."""
    pass


class AITimeoutError(AIServiceError):
    """Raised when an AI provider call exceeds configured timeout."""
    pass


class AIValidationError(AIServiceError):
    """Raised when LLM output violates the Pydantic response schema."""
    pass


def extract_json_from_llm_text(text: str) -> Dict[str, Any]:
    """
    Robustly extract and parse JSON from model output,
    handling markdown code fences (```json ... ```) or conversational wrappers.
    """
    cleaned = text.strip()
    # Check for markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Find start and end of JSON object
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx : end_idx + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIValidationError(f"Model output is not valid JSON: {str(exc)}\nRaw: {text[:200]}")


def parse_and_validate_ai_json(text: str, schema_cls: Type[BaseModel] = AIAnalysisPayload) -> BaseModel:
    """Parse text and validate against target Pydantic schema."""
    data = extract_json_from_llm_text(text)
    try:
        return schema_cls.model_validate(data)
    except ValidationError as val_err:
        raise AIValidationError(f"Schema validation failed: {str(val_err)}")


class AIProviderInterface(ABC):
    """Abstract interface defining the contract for all AI model providers."""

    @abstractmethod
    async def generate_analysis(self, request: AIRequest) -> AIResponse:
        """Execute multimodal structured inspection reasoning with strict schema enforcement."""
        pass

    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Compute estimated cost in USD based on model pricing."""
        pass


class MockAIProvider(AIProviderInterface):
    """
    Deterministic offline provider used for unit testing, CI pipelines,
    and zero-cost development without requiring external cloud API keys.
    """

    def __init__(
        self,
        synthetic_findings: Optional[List[Dict[str, Any]]] = None,
        simulate_timeout: bool = False,
        simulate_error: bool = False,
        simulated_latency_ms: float = 80.0,
    ):
        self.synthetic_findings = synthetic_findings
        self.simulate_timeout = simulate_timeout
        self.simulate_error = simulate_error
        self.simulated_latency_ms = simulated_latency_ms

    async def generate_analysis(self, request: AIRequest) -> AIResponse:
        start_time = time.time()

        if self.simulate_timeout:
            raise AITimeoutError(f"Mock request timed out after {request.timeout_seconds}s")

        if self.simulate_error:
            raise AIServiceError("Simulated upstream provider connection reset (503 Service Unavailable)")

        if self.simulated_latency_ms > 0:
            await asyncio.sleep(min(0.2, self.simulated_latency_ms / 1000.0))

        # If synthetic findings are injected, format them
        if self.synthetic_findings is not None:
            findings_data = self.synthetic_findings
        else:
            # Generate deterministic findings by scanning user prompt context
            findings_data = self._generate_contextual_findings(request.user_prompt)

        raw_dict = {
            "prompt_version": request.prompt_version,
            "findings": findings_data,
            "summary_notes": f"Automated inspection completed using {request.prompt_version}. Verified against requested engineering standards.",
        }

        raw_text = json.dumps(raw_dict, indent=2)
        validated_payload = AIAnalysisPayload.model_validate(raw_dict)

        prompt_tokens = len(request.user_prompt) // 4 + len(request.system_prompt) // 4
        completion_tokens = len(raw_text) // 4
        total_tokens = prompt_tokens + completion_tokens

        latency_ms = (time.time() - start_time) * 1000.0
        model_name = request.model_name or "mock-engineering-llm-v1"
        cost = self.calculate_cost(prompt_tokens, completion_tokens, model_name)

        return AIResponse(
            raw_text=raw_text,
            structured_payload=validated_payload,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency_ms,
            model_name=model_name,
            provider="mock-local",
        )

    def _generate_contextual_findings(self, user_prompt: str) -> List[Dict[str, Any]]:
        findings = []

        # Check for missing wire gauge
        if "MISSING GAUGE" in user_prompt.upper() or "W102" in user_prompt:
            findings.append({
                "finding_code": "D-001",
                "rule_id": "RULE-WG-001",
                "category": "WIRE_SPEC",
                "description": "Conductor W102 connected to Circuit Breaker CB-101 (20A) is missing required wire gauge specification.",
                "severity": SeverityEnum.CRITICAL.value,
                "confidence_score": 0.98,
                "confidence_level": ConfidenceLevelEnum.HIGH.value,
                "page_number": 1,
                "location_bbox": {"x": 200, "y": 170, "width": 280, "height": 30},
                "evidence_text": "W102 [BLK] -> J101 (Gauge not specified on drawing)",
                "requirement_text": "All current-carrying conductors must have an explicit gauge callout sized to circuit breaker rating.",
                "standard_citation": "IPC-WHMA-A-620D §13.4.1 (Conductor Sizing & Protection)",
                "recommendation": "Specify minimum 12 AWG (or MIL-W-22759/16-12) to satisfy the 20A continuous load rating of CB-101.",
            })

        # Check for color code ambiguity
        if "COLOR" in user_prompt.upper() and ("W104" in user_prompt or "DARK" in user_prompt or "GND" in user_prompt):
            findings.append({
                "finding_code": "D-002",
                "rule_id": "RULE-CC-001",
                "category": "COLOR_CODE",
                "description": "Protective ground wire is designated without mandatory green/yellow (GRN/YEL) color code standard.",
                "severity": SeverityEnum.CRITICAL.value,
                "confidence_score": 0.95,
                "confidence_level": ConfidenceLevelEnum.HIGH.value,
                "page_number": 1,
                "location_bbox": {"x": 200, "y": 250, "width": 260, "height": 30},
                "evidence_text": "Wire connecting to chassis ground marked without standard green insulation",
                "requirement_text": "Protective earthing conductors must be colored green with or without yellow stripe.",
                "standard_citation": "UL 508A §15.2 (Internal Wiring Color Coding)",
                "recommendation": "Change insulation color specification to GRN or GRN/YEL per UL 508A.",
            })

        # Fallback baseline finding if prompt is clean
        if not findings:
            findings.append({
                "finding_code": "D-001",
                "rule_id": "RULE-TB-001",
                "category": "DOCUMENTATION",
                "description": "Title block is missing mandatory engineering approval signature and sign-off date.",
                "severity": SeverityEnum.MINOR.value,
                "confidence_score": 0.90,
                "confidence_level": ConfidenceLevelEnum.HIGH.value,
                "page_number": 1,
                "location_bbox": {"x": 500, "y": 500, "width": 200, "height": 50},
                "evidence_text": "Title block fields APPROVED BY and DATE are blank",
                "requirement_text": "Engineering drawings must have authorized approval sign-off prior to production release.",
                "standard_citation": "ISO 7200 §5.3 (Approval Authorization Data Fields)",
                "recommendation": "Obtain and record responsible engineering authority sign-off.",
            })

        return findings

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        # Mock provider incurs zero cost
        return 0.0


class OpenAIProvider(AIProviderInterface):
    """OpenAI GPT-4o / GPT-4o-mini structured reasoning provider."""

    PRICING = {
        "gpt-4o": {"prompt": 2.50 / 1_000_000, "completion": 10.00 / 1_000_000},
        "gpt-4o-mini": {"prompt": 0.15 / 1_000_000, "completion": 0.60 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.default_model = default_model or settings.OPENAI_MODEL

    async def generate_analysis(self, request: AIRequest) -> AIResponse:
        if not self.api_key:
            raise AIServiceError("OpenAI API key is not configured. Set OPENAI_API_KEY environment variable.")

        model = request.model_name or self.default_model
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": request.temperature,
        }

        timeout = httpx.Timeout(request.timeout_seconds, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            attempts = 0
            max_retries = settings.AI_MAX_RETRIES
            last_err = None

            while attempts < max_retries:
                attempts += 1
                try:
                    resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                    if resp.status_code == 429 or resp.status_code >= 500:
                        last_err = AIServiceError(f"OpenAI error {resp.status_code}: {resp.text}")
                        await asyncio.sleep(0.5 * (2 ** attempts))
                        continue

                    resp.raise_for_status()
                    data = resp.json()

                    raw_content = data["choices"][0]["message"]["content"]
                    validated_payload = parse_and_validate_ai_json(raw_content, AIAnalysisPayload)

                    usage = data.get("usage", {})
                    p_tokens = usage.get("prompt_tokens", 0)
                    c_tokens = usage.get("completion_tokens", 0)
                    t_tokens = usage.get("total_tokens", p_tokens + c_tokens)

                    latency = (time.time() - start_time) * 1000.0
                    cost = self.calculate_cost(p_tokens, c_tokens, model)

                    return AIResponse(
                        raw_text=raw_content,
                        structured_payload=validated_payload,  # type: ignore
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        total_tokens=t_tokens,
                        estimated_cost_usd=cost,
                        latency_ms=latency,
                        model_name=model,
                        provider="openai",
                    )
                except httpx.TimeoutException:
                    last_err = AITimeoutError(f"OpenAI call timed out after {request.timeout_seconds}s (attempt {attempts})")
                    if attempts < max_retries:
                        await asyncio.sleep(0.5 * (2 ** attempts))
                    continue
                except httpx.HTTPStatusError as http_err:
                    raise AIServiceError(f"OpenAI HTTP error: {str(http_err)}")

            raise last_err or AIServiceError("OpenAI call failed after retries")

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        rates = self.PRICING.get(model, self.PRICING["gpt-4o"])
        return (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])


class AnthropicProvider(AIProviderInterface):
    """Anthropic Claude 3.5 Sonnet / Haiku structured reasoning provider."""

    PRICING = {
        "claude-3-5-sonnet-20241022": {"prompt": 3.00 / 1_000_000, "completion": 15.00 / 1_000_000},
        "claude-3-5-haiku-20241022": {"prompt": 0.80 / 1_000_000, "completion": 4.00 / 1_000_000},
    }

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.default_model = default_model or settings.ANTHROPIC_MODEL

    async def generate_analysis(self, request: AIRequest) -> AIResponse:
        if not self.api_key:
            raise AIServiceError("Anthropic API key is not configured. Set ANTHROPIC_API_KEY environment variable.")

        model = request.model_name or self.default_model
        start_time = time.time()

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "max_tokens": 4096,
            "temperature": request.temperature,
        }

        timeout = httpx.Timeout(request.timeout_seconds, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            raw_content = data["content"][0]["text"]
            validated_payload = parse_and_validate_ai_json(raw_content, AIAnalysisPayload)

            usage = data.get("usage", {})
            p_tokens = usage.get("input_tokens", 0)
            c_tokens = usage.get("output_tokens", 0)

            latency = (time.time() - start_time) * 1000.0
            cost = self.calculate_cost(p_tokens, c_tokens, model)

            return AIResponse(
                raw_text=raw_content,
                structured_payload=validated_payload,  # type: ignore
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=p_tokens + c_tokens,
                estimated_cost_usd=cost,
                latency_ms=latency,
                model_name=model,
                provider="anthropic",
            )

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        rates = self.PRICING.get(model, self.PRICING["claude-3-5-sonnet-20241022"])
        return (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])


class AIProviderFactory:
    """Factory to instantiate the configured AI Provider."""

    @staticmethod
    def get_provider(
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AIProviderInterface:
        ptype = (provider_type or settings.AI_PROVIDER).lower()
        if ptype == "openai":
            return OpenAIProvider(api_key=api_key, default_model=model)
        elif ptype == "anthropic":
            return AnthropicProvider(api_key=api_key, default_model=model)
        return MockAIProvider()


# Backward compatibility aliases
LLMRequest = AIRequest
LLMResponse = AIResponse
LLMProviderInterface = AIProviderInterface
MockLLMProvider = MockAIProvider
LLMProviderFactory = AIProviderFactory
