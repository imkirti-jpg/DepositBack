import logging
from app.services.ai_client import AIClient, AIRequest

logger = logging.getLogger(__name__)


# schema & prompt 

_PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_description": {"type": "string"},
                    "claimed_amount":   {"type": "number"},
                    "currency":         {"type": "string"},
                },
            },
        }
    },
}

_PARSE_SYSTEM_EXTRA = """
You are parsing a landlord's deduction notice into a structured list of
individual claim line items.

Rules:
- Split compound deductions into separate items
  (e.g. "Cleaning ₹2000 + repainting ₹5000" → two items).
- Set claimed_amount to null if no amount is stated for that item.
- item_description should be concise but complete, e.g.
  "Repainting of all walls" not just "paint".
- Do not assess or label anything in this pass — only parse.
"""


# schema & prompt 

_ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "analyzed_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_description": {"type": "string"},
                    "claimed_amount":   {"type": "number"},
                    "label": {
                        "type": "string",
                        "enum": ["supported", "weak", "unsupported", "unclear"],
                    },
                    "reasoning": {"type": "string"},
                    "evidence_refs": {
                        "type": "object",
                        "properties": {
                            "lease_clauses": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "evidence_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }
    },
}

_ANALYZE_SYSTEM_EXTRA = """
You are a tenancy-dispute analyst assessing whether each deduction in a
landlord's notice is justified under the lease and the tenant's evidence.

Label definitions — use exactly one per claim:
  supported    — the lease clearly permits this deduction AND the landlord's
                 claim is consistent with the evidence.
  weak         — the deduction may be partially valid but lacks lease backing,
                 is likely normal wear and tear, or the amount is disproportionate.
  unsupported  — no lease clause permits this deduction, or evidence directly
                 contradicts the landlord's claim.
  unclear      — insufficient information to assess; state exactly what is missing.

Use unclear ONLY when a conclusion truly cannot be reached.

If the lease suggests a deduction MAY be valid but the landlord has weak or incomplete support, use weak.

Do not overuse unclear.
For each claim:
1. Check whether the lease's extracted_fields contain a clause that permits
   or prohibits this type of deduction.
2. Check whether any uploaded evidence (move-in or move-out photos/notes)
   supports or contradicts the deduction.
3. Apply Indian tenancy norms where relevant:
   - Normal wear and tear is the landlord's responsibility, not the tenant's.
   - Repainting after 2+ years of tenancy is typically normal wear and tear.
   - Deductions for pre-existing damage are not valid.
4. Cite specific lease clauses and evidence IDs in evidence_refs.
   If nothing relevant exists, leave the arrays empty and explain what is missing
   in the reasoning field.
5. Never state or imply the tenant will win or recover a specific amount.
"""


# Engine 

async def analyze_notice(
    *,
    notice_text: str | None,
    notice_file_bytes: bytes | None,
    notice_mime_type: str | None,
    lease_fields: dict | None,
    evidence_rows: list[dict],
    ai_client: AIClient,
) -> list[dict]:
    """
    Run the two-pass analysis pipeline.

    Returns a list of analyzed claim dicts, each with:
      item_description, claimed_amount, label, reasoning, evidence_refs

    Raises AIClientError on failure — the caller sets notice status = failed.
    """

    #1 parse the notice 
    parse_parts = _build_notice_parts(notice_text, notice_file_bytes, notice_mime_type)
    parse_parts.insert(0, "Parse this deduction notice into individual claim line items.")

    parse_response = await ai_client.call(
        AIRequest(
            parts=parse_parts,
            response_schema=_PARSE_SCHEMA,
            system_prompt_extra=_PARSE_SYSTEM_EXTRA,
            temperature=0.1,
        )
    )
    raw_claims = parse_response.parsed.get("claims", [])
    logger.info("dispute_engine pass 1: parsed %d claims", len(raw_claims))

    if not raw_claims:
        # return empty, caller will mark completed
        return []

    # 2 analyze each claim against lease + evidence 
    context_block = _build_context_block(raw_claims, lease_fields, evidence_rows)

    analyze_response = await ai_client.call(
        AIRequest(
            parts=[context_block],
            response_schema=_ANALYZE_SCHEMA,
            system_prompt_extra=_ANALYZE_SYSTEM_EXTRA,
            temperature=0.2,
        )
    )
    analyzed = analyze_response.parsed.get("analyzed_claims", [])
    logger.info(
        "dispute_engine pass 2: analyzed %d claims (retried=%s)",
        len(analyzed),
        analyze_response.retried,
    )
    return analyzed


def _build_notice_parts(
    notice_text: str | None,
    notice_file_bytes: bytes | None,
    notice_mime_type: str | None,
) -> list:
    parts = []
    if notice_text:
        parts.append(f"DEDUCTION NOTICE TEXT:\n{notice_text}")
    if notice_file_bytes and notice_mime_type:
        parts.append({"data": notice_file_bytes, "mime_type": notice_mime_type})
    return parts


def _build_context_block(
    raw_claims: list[dict],
    lease_fields: dict | None,
    evidence_rows: list[dict],
) -> str:
    """
    Build the single text block passed to pass 2.
    Structured so the model can clearly see: what was claimed, what the
    lease says, and what evidence exists.
    """
    lines = ["Analyze the following deduction claims.\n"]

    lines.append("CLAIMS TO ANALYZE:")
    for i, claim in enumerate(raw_claims, 1):
        amount = claim.get("claimed_amount")
        currency = claim.get("currency", "INR")
        amount_str = f"{currency} {amount}" if amount else "amount not stated"
        lines.append(f"  {i}. {claim.get('item_description')} — {amount_str}")

    lines.append("\nLEASE INFORMATION:")
    if lease_fields:
        for key, field in lease_fields.items():
            if key in ("low_confidence_fields", "extraction_notes"):
                continue
            val = field.get("value") if isinstance(field, dict) else field
            conf = field.get("confidence", "") if isinstance(field, dict) else ""
            conf_note = f" [confidence: {conf}]" if conf else ""
            lines.append(f"  {key}: {val}{conf_note}")
    else:
        lines.append("  No lease has been uploaded or extracted for this property.")

    lines.append("\nUPLOADED EVIDENCE:")
    if evidence_rows:
        for ev in evidence_rows:
            room = ev.get("room_label") or "unspecified room"
            phase = ev.get("phase", "")
            notes = ev.get("notes") or "no notes"
            lines.append(f"  [{ev['id']}] {phase} — {room}: {notes}")
    else:
        lines.append("  No evidence has been uploaded for this property.")

    return "\n".join(lines)



"""
dispute_engine.py — the two-pass AI pipeline that is the core of DepositBack.

Pass 1: Parse the deduction notice into discrete claim line items.
Pass 2: Match every claim against the lease fields and uploaded evidence,
        producing a label + reasoning + evidence_refs for each.

Both passes go through ai_client so the guardrail always applies.

This prompt WILL need tuning against real deduction notices before the
verdicts feel trustworthy. Budget time in week 4-5 of the build for this.
The schema is stable — only the prompt text changes during tuning.
"""
