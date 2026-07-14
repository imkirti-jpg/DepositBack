from __future__ import annotations
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger(__name__)

_GUARDRAIL_SYSTEM_PROMPT = """
You are an impartial tenancy-dispute analyst.

RULES YOU MUST ALWAYS FOLLOW:
1. Never state or imply that the tenant will win, recover money, or that a claim
   is guaranteed. Your job is to assess evidence, not predict outcomes.
2. Every claim assessment must include a confidence label — exactly one of:
   supported | weak | unsupported | unclear
3. Never invent evidence. If the lease or evidence does not address a point,
   label it "unclear" and explain what is missing.
4. Use firm, fact-based language. Avoid aggressive or exaggerated wording.
5. Respond ONLY with the JSON structure specified in the user message.
   No preamble, no markdown fences, no trailing commentary.
6. Include this exact sentence verbatim in any generated letters or messages:
   "DepositBack helps organise evidence and draft communication. It does not
   provide legal representation and does not guarantee any outcome."
""".strip()

_CERTAINTY_PHRASES = [
    "you will win", "you will recover", "guaranteed",
    "certain to", "definitely get back", "100% sure", "no doubt",
]


import os
import hashlib
import datetime

class AIClientError(Exception):
    pass


@dataclass
class AIRequest:
    parts: list[str | dict]       
    response_schema: dict[str, Any]
    system_prompt_extra: str = ""
    temperature: float = 0.2
    max_output_tokens: int = 8192
    allow_retry: bool = False
    document_id: str | None = None


@dataclass
class AIResponse:
    raw_text: str
    parsed: dict[str, Any]
    retried: bool = False


class AIClient:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    @staticmethod
    def calculate_request_hash(request: AIRequest) -> str:
        h = hashlib.sha256()
        h.update((request.system_prompt_extra or "").encode("utf-8"))
        h.update(json.dumps(request.response_schema, sort_keys=True).encode("utf-8"))
        for part in request.parts:
            if isinstance(part, str):
                h.update(part.encode("utf-8"))
            elif isinstance(part, dict):
                h.update(part.get("data", b""))
                h.update(part.get("mime_type", "").encode("utf-8"))
        return h.hexdigest()

    def _load_mock_response(self, request: AIRequest) -> dict:
        mocks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mocks")
        extra = (request.system_prompt_extra or "").lower()
        parts_combined = " ".join([p if isinstance(p, str) else "" for p in request.parts]).lower()
        
        if "expert legal document parser" in extra or "extract the key tenancy fields" in parts_combined:
            filename = "lease_extraction.json"
        elif "parsing a landlord's deduction notice" in extra or "parse this deduction notice" in parts_combined:
            filename = "notice_parse.json"
        elif "tenant rights and lease analysis assistant" in extra or "evaluate every deduction separately" in extra:
            filename = "notice_analysis.json"
        elif "whatsapp/email draft" in extra or "demand letter" in extra or "firm, professional message" in extra:
            filename = "document_generation.json"
        else:
            filename = "notice_analysis.json"
            
        mock_path = os.path.join(mocks_dir, filename)
        try:
            with open(mock_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Mock load failed for %s: %s", filename, e)
            return {}

    async def call(self, request: AIRequest) -> AIResponse:
        req_hash = self.calculate_request_hash(request)
        doc_id = request.document_id or req_hash
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. Dev mode: AI disabled
        if not settings.AI_ENABLED:
            logger.info("[%s] [Doc ID: %s] Dev mode (AI_ENABLED=False). Loading mock response...", timestamp, doc_id)
            mock_data = self._load_mock_response(request)
            return AIResponse(raw_text=json.dumps(mock_data), parsed=mock_data, retried=False)
            
        # 2. Cache check
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{req_hash}.json")
        
        if os.path.exists(cache_path):
            logger.info("[%s] [Doc ID: %s] Cache hit. Returning cached response...", timestamp, doc_id)
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return AIResponse(
                    raw_text=cached_data.get("raw_text", ""),
                    parsed=cached_data.get("parsed", {}),
                    retried=cached_data.get("retried", False)
                )
            except Exception as e:
                logger.error("Failed to read cache file: %s", e)

        # 3. Gemini API Call
        logger.info("[%s] [Doc ID: %s] Making Gemini API call (Hash: %s)", timestamp, doc_id, req_hash)
        
        system_instruction = self._build_system_prompt(request.system_prompt_extra)
        user_parts = self._build_parts(request)
        
        if request.allow_retry:
            raw_text, retried = await self._call_with_retry(
                system_instruction, user_parts, request.temperature, request.max_output_tokens
            )
        else:
            raw_text = await self._gemini_call(system_instruction, user_parts, request.temperature, request.max_output_tokens)
            violation = self._check_guardrail_violation(raw_text)
            parse_ok = self._is_valid_json(raw_text)
            if violation or not parse_ok:
                raise AIClientError(
                    f"Model validation failed. Violation: {violation is not None}, Valid JSON: {parse_ok}"
                )
            retried = False
            
        parsed = self._parse_json(raw_text)
        
        # Save to cache
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "raw_text": raw_text,
                    "parsed": parsed,
                    "retried": retried
                }, f, indent=2)
        except Exception as e:
            logger.error("Failed to write to cache: %s", e)
            
        return AIResponse(raw_text=raw_text, parsed=parsed, retried=retried)

    def _build_system_prompt(self, extra: str) -> str:
        return f"{_GUARDRAIL_SYSTEM_PROMPT}\n\n{extra.strip()}" if extra else _GUARDRAIL_SYSTEM_PROMPT

    def _build_parts(self, request: AIRequest) -> list:
        parts = []
        schema_instruction = (
            "\n\nRespond with ONLY valid JSON matching this schema exactly:\n"
            + json.dumps(request.response_schema, indent=2)
        )
        for part in request.parts:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(types.Part.from_bytes(data=part["data"], mime_type=part["mime_type"]))
        parts.append(schema_instruction)
        return parts

    async def _call_with_retry(self, system_instruction, user_parts, temperature, max_output_tokens):
        raw_text = await self._gemini_call(system_instruction, user_parts, temperature, max_output_tokens)
        violation = self._check_guardrail_violation(raw_text)
        parse_ok = self._is_valid_json(raw_text)

        if not violation and parse_ok:
            return raw_text, False

        logger.warning("ai_client: retrying — violation=%s parse_ok=%s", violation, parse_ok)
        corrective_parts = list(user_parts) + [
            self._build_correction_note(raw_text, had_violation=bool(violation), had_parse_error=not parse_ok)
        ]
        retry_text = await self._gemini_call(system_instruction, corrective_parts, 0.1, max_output_tokens)

        if not self._is_valid_json(retry_text):
            raise AIClientError("Model returned invalid JSON on both attempts.")
        if self._check_guardrail_violation(retry_text):
            raise AIClientError("Model continued to use certainty language after correction.")

        return retry_text, True

    async def _gemini_call(self, system_instruction, user_parts, temperature, max_output_tokens) -> str:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user_parts,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
            ),
        )
        return response.text or ""

    @staticmethod
    def _check_guardrail_violation(text: str) -> str | None:
        lower = text.lower()
        for phrase in _CERTAINTY_PHRASES:
            if phrase in lower:
                return phrase
        return None

    @staticmethod
    def _is_valid_json(text: str) -> bool:
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            json.loads(cleaned)
            return True
        except json.JSONDecodeError:
            return False

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            result = json.loads(cleaned)
            if not isinstance(result, dict):
                raise AIClientError(f"Expected a JSON object, got {type(result).__name__}")
            return result
        except json.JSONDecodeError as exc:
            raise AIClientError(f"Could not parse model response as JSON: {exc}") from exc

    @staticmethod
    def _build_correction_note(raw_text: str, had_violation: bool, had_parse_error: bool) -> str:
        lines = ["CORRECTION REQUIRED — your previous response had problems:"]
        if had_violation:
            lines.append("• You used language implying a certain outcome. Use confidence labels only.")
        if had_parse_error:
            lines.append("• Your response was not valid JSON. Return only the raw JSON object, no fences.")
        lines.append("\nPrevious response:\n" + raw_text)
        lines.append("\nPlease try again, fixing all issues above.")
        return "\n".join(lines)


ai_client = AIClient()