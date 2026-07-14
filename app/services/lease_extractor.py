import logging
from app.services.ai_client import AIClient, AIRequest, AIClientError

logger = logging.getLogger(__name__)

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "property_address": {"type": "string"},
        "tenant_name": {"type": "string"},
        "landlord_name": {"type": "string"},
        "lease_start_date": {"type": "string"},
        "lease_end_date": {"type": "string"},
        "monthly_rent": {"type": "string"},
        "security_deposit": {"type": "string"},
        "utilities": {
            "type": "object",
            "properties": {
                "tenant_pays": {"type": "array", "items": {"type": "string"}},
                "landlord_pays": {"type": "array", "items": {"type": "string"}},
            },
        },
        "move_out_cleaning_required": {"type": "boolean"},
        "professional_cleaning_required": {"type": "boolean"},
        "painting_required": {"type": "boolean"},
        "tenant_responsible_for_damage": {"type": "boolean"},
        "tenant_responsible_for_fixtures": {"type": "boolean"},
        "late_fees": {"type": "string"},
        "other_obligations": {"type": "array", "items": {"type": "string"}},
        "clauses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "text": {"type": "string"},
                },
            },
        },
    },
}

_SYSTEM_PROMPT_EXTRA = """
You are an expert legal document parser.
Your job is ONLY to extract information from the lease.

Do not infer.
Do not guess.
Do not summarize.

Rules:
1. If a clause is not explicitly stated, leave the field null or false.
2. Never invent clauses.
3. Every clause must contain the original wording from the lease.
4. Never state that a lease contains a clause unless it appears verbatim.
5. Never assume standard landlord practices.
6. Never assume local laws unless explicitly provided.
7. If information is missing, state "Not found in provided documents."
8. Never fabricate clause IDs (use prefix like "clause_" or similar clear identifier).
9. Confidence should reflect only the provided documents.
"""


async def extract_lease_fields(
    file_bytes: bytes,
    mime_type: str,
    ai_client: AIClient,
    lease_id: str | None = None,
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
        document_id=str(lease_id) if lease_id else None,
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
