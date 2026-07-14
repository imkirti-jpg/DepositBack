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
        "summary": {
            "type": "object",
            "properties": {
                "supported_amount": {"type": "number"},
                "unsupported_amount": {"type": "number"},
                "unclear_amount": {"type": "number"},
            },
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "amount": {"type": "number"},
                    "verdict": {
                        "type": "string",
                        "enum": ["supported", "weak", "unsupported", "unclear"],
                    },
                    "contract_status": {
                        "type": "string",
                        "enum": ["allowed", "partially_allowed", "not_allowed"],
                    },
                    "evidence_status": {
                        "type": "string",
                        "enum": ["sufficient", "partial", "missing"],
                    },
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                    "landlord_evidence": {"type": "array", "items": {"type": "string"}},
                    "needed_evidence": {"type": "array", "items": {"type": "string"}},
                    "lease_clause_ids": {"type": "array", "items": {"type": "string"}},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}

_ANALYZE_SYSTEM_EXTRA = """
You are an expert tenancy-dispute analyst evaluating landlord deduction claims.

For each claim line item, evaluate two distinct dimensions:
1. CONTRACT: Is this type of deduction allowed under the lease clauses?
   - contract_status:
     - allowed: The lease explicitly permits this deduction type (e.g. cleaning, damage repairs).
     - partially_allowed: The lease allows it under restricted conditions or only a portion of it.
     - not_allowed: The lease does not support this type of deduction, or explicitly prohibits it.

2. EVIDENCE: Is the claim supported by specific, credible evidence?
   - evidence_status:
     - sufficient: Landlord's referenced invoices/photos exist and tenant evidence doesn't contradict.
     - partial: Some evidence exists, but it's incomplete or weak.
     - missing: No invoices, photos, or proof are mentioned or provided.

Combine these into the final "verdict":
  - supported   — Lease allows the deduction AND evidence is sufficient.
  - weak        — Lease allows/may allow the deduction, but evidence is insufficient or missing.
  - unsupported — Lease does not support the deduction, or tenant evidence refutes it.
  - unclear     — Conflicting or ambiguous information makes it impossible to decide.

Rules:
1. Distinguish three categories of evidence:
   - Landlord-Referenced: List any photos, invoices, estimates, or documents mentioned/referenced by the landlord in the deduction notice in "landlord_evidence" (e.g. "cleaning invoice").
   - Tenant-Uploaded (Actually Uploaded): Match and cite ONLY specific tenant-uploaded evidence IDs from the UPLOADED EVIDENCE section in "evidence_ids" that directly relate to this claim. DO NOT generically match files (like "Move-in Photo 1") unless the note, room, or phase explicitly correlates with the deduction.
   - Needed Evidence: List any additional evidence that is still required to verify the claim in "needed_evidence".
2. Apply Indian tenancy norms:
   - Normal wear and tear is the landlord's responsibility, not the tenant's.
   - Repainting after 2+ years of tenancy is typically normal wear and tear.
   - Deductions for pre-existing damage are not valid.
3. Cite specific lease clauses in "lease_clause_ids". Never fabricate clause IDs or evidence IDs.
4. If information is missing, state "Not found in provided documents" in reasoning.
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
    notice_id: str | None = None,
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
            document_id=f"{notice_id}_parse" if notice_id else None,
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
            document_id=f"{notice_id}_analyze" if notice_id else None,
        )
    )
    claims_list = analyze_response.parsed.get("claims", [])
    logger.info(
        "dispute_engine pass 2: analyzed %d claims (retried=%s)",
        len(claims_list),
        analyze_response.retried,
    )
    
    # Map back to database schema keys:
    # item_description, claimed_amount, label, reasoning, evidence_refs
    mapped = []
    for cl in claims_list:
        mapped.append({
            "item_description": cl.get("title", ""),
            "claimed_amount": cl.get("amount"),
            "label": cl.get("verdict", "unclear"),
            "reasoning": cl.get("reasoning", ""),
            "evidence_refs": {
                "lease_clauses": cl.get("lease_clause_ids", []),
                "evidence_ids": cl.get("evidence_ids", []),
                "needed_evidence": cl.get("needed_evidence", []),
                "landlord_evidence": cl.get("landlord_evidence", []),
                "contract_status": cl.get("contract_status", "not_allowed"),
                "evidence_status": cl.get("evidence_status", "missing"),
            }
        })
    return mapped


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
