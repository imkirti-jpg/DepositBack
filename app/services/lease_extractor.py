import logging
from app.services.ai_client import AIClient, AIRequest, AIClientError

logger = logging.getLogger(__name__)

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "deposit_amount": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "currency": {"type": "string"},
                "confidence": {"type": "string"},
            },
        },
        "notice_period": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "days": {"type": "number"},
                "confidence": {"type": "string"},
            },
        },
        "lock_in_period": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "confidence": {"type": "string"},
            },
        },
        "refund_timeline": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "confidence": {"type": "string"},
            },
        },
        "deductible_categories": {
            "type": "object",
            "properties": {
                "value": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string"},
            },
        },
        "move_out_obligations": {
            "type": "object",
            "properties": {
                "value": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string"},
            },
        },
        "deduction_clauses": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "confidence": {"type": "string"},
            },
        },
        "low_confidence_fields": {"type": "array", "items": {"type": "string"}},
        "extraction_notes": {"type": "string"},
    },
}

_SYSTEM_PROMPT_EXTRA = """
You are extracting structured fields from an Indian residential lease agreement.
The document may be a photographed page, a scanned PDF, or typed text.

For every field:
- Set confidence to "high" if the value is explicitly stated in the document.
- Set confidence to "medium" if you inferred it from context or standard practice.
- Set confidence to "low" if the document is ambiguous on this point.
- Set confidence to "unclear" if the document does not address this at all.

Always populate low_confidence_fields with the key names of every field
whose confidence is "low" or "unclear". The frontend uses this list to
prompt the user to confirm those values — never leave it empty if any
field has low or unclear confidence.

Never guess a deposit amount or date if it is not visible in the document.
If a field is not present, set its value to null and confidence to "unclear".
"""


async def extract_lease_fields(
    file_bytes: bytes,
    mime_type: str,
    ai_client: AIClient,
) -> dict:
    """
    Run extraction on a lease file. Returns the extracted_fields dict.
    Raises AIClientError on failure — the caller sets status = failed.
    """
    request = AIRequest(
        parts=[
            "Extract the key tenancy fields from this lease document.",
            {"data": file_bytes, "mime_type": mime_type},
        ],
        response_schema=_RESPONSE_SCHEMA,
        system_prompt_extra=_SYSTEM_PROMPT_EXTRA,
        temperature=0.1,   # factual extraction — as deterministic as possible
    )
    response = await ai_client.call(request)
    if response.retried:
        logger.info("lease_extractor: extraction succeeded after retry")
    return response.parsed





"""
lease_extractor.py — the AI extraction logic for a lease document.

Called only from background tasks — never directly from a request handler.

extracted_fields schema (stored as JSONB):
{
  "deposit_amount":         {"value": "50000", "currency": "INR",  "confidence": "high"},
  "notice_period":          {"value": "30 days", "days": 30,        "confidence": "high"},
  "lock_in_period":         {"value": "6 months",                   "confidence": "medium"},
  "refund_timeline":        {"value": "within 30 days of move-out", "confidence": "high"},
  "deductible_categories":  {"value": ["unpaid rent", "damage..."], "confidence": "medium"},
  "move_out_obligations":   {"value": ["return all keys", ...],     "confidence": "high"},
  "deduction_clauses":      {"value": "<raw clause text>",          "confidence": "high"},
  "low_confidence_fields":  ["lock_in_period"],
  "extraction_notes":       "Any caveats or ambiguities noticed."
}

confidence levels: "high" | "medium" | "low" | "unclear"
low_confidence_fields lists every key whose confidence is "low" or "unclear" —
the frontend uses this list to show "please confirm" prompts to the user.
"""
