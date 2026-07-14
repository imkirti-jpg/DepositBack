"""
document_generator.py — generates recovery documents from the claims breakdown.

Two document types:
  message       — short WhatsApp/email draft, copy-paste ready, ~150-250 words
  formal_letter — full demand letter with referenced clauses, ~400-600 words

The mandatory disclaimer is injected server-side into the formal_letter output.
Never rely on the prompt alone for the disclaimer — always append it in code.
"""

import logging
from app.services.ai_client import AIClient, AIRequest

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "\n\n---\n"
    "DepositBack helps organise evidence and draft communication. "
    "It does not provide legal representation and does not guarantee any outcome. "
    "Verify your state's specific tenancy rules before escalating."
)

#  Shared response schema 

_DOC_SCHEMA = {
    "type": "object",
    "properties": {
        "draft": {"type": "string"},
        "subject_line": {
            "type": "string",
            "description": "Email subject line (for message type). Empty string for formal_letter.",
        },
        "total_disputed_amount": {
            "type": "number",
            "description": "Sum of all disputed claim amounts. 0 if no amounts were stated.",
        },
    },
}


#  Message prompt 

_MESSAGE_SYSTEM_EXTRA = """
You are drafting a firm, professional message for a tenant to send to their
landlord disputing incorrect deposit deductions.

Tone: polite but firm. Not aggressive. Not pleading. Factual.
Length: 150-250 words. It must work as a WhatsApp message or short email.

Structure:
1. Reference the deduction notice received.
2. For each unsupported or weak claim, state why it is being disputed in one sentence.
3. State the total amount being disputed.
4. Request a revised refund breakdown or the full disputed amount within 7 days.
5. Say the tenant will follow up in writing if there is no response.

Do NOT include greetings like "Dear Sir/Madam" — the user will add those.
Do NOT use aggressive or threatening language.
Do NOT reference any specific law unless a lease clause is clearly cited in the context.
"""

_MESSAGE_USER_PROMPT = """
Draft a WhatsApp/email message disputing the following deduction claims on behalf of the tenant.

{context}

Write only the message body. The user will personalise the greeting and sign-off.
"""


#  Formal letter prompt 

_FORMAL_LETTER_SYSTEM_EXTRA = """
You are drafting a formal demand letter for a tenant to send to their landlord
disputing incorrect deposit deductions under an Indian residential tenancy.

Tone: formal, firm, legally aware. Not aggressive.
Length: 400-600 words.

Structure:
1. Subject line (e.g. "Formal Dispute of Security Deposit Deductions — [Property Address]").
2. Opening: reference the lease, move-out date, and deposit amount.
3. For each unsupported or weak deduction: state the item, the amount, why it is disputed,
   and cite the specific lease clause or evidence that supports the dispute.
   Use numbered paragraphs.
4. State the total disputed amount and the total refund being requested.
5. Set a 7-day response deadline from the date of this letter.
6. State that failure to respond may result in escalation to the appropriate
   consumer forum or rent authority.
7. Close formally.

Leave [DATE], [LANDLORD NAME], [PROPERTY ADDRESS], and [TENANT NAME] as
literal placeholders — the user will fill these in before sending.

Do NOT invent legal citations. Reference lease clauses only if they appear
in the context provided.
"""

_FORMAL_LETTER_USER_PROMPT = """
Draft a formal demand letter disputing the following deposit deductions.

{context}

Include [DATE], [LANDLORD NAME], [PROPERTY ADDRESS], [TENANT NAME] as
placeholders. Write the full letter body only.
"""


#  Generator 

async def generate_document(
    *,
    doc_type: str,
    claims: list[dict],
    lease_fields: dict | None,
    deposit_amount: float | None,
    property_label: str,
    ai_client: AIClient,
    doc_id: str | None = None,
) -> dict:
    """
    Generate a recovery document from the claims breakdown.

    Returns a dict with keys: draft, subject_line, total_disputed_amount.
    The caller is responsible for appending _DISCLAIMER to formal_letter drafts.

    Raises AIClientError on failure.
    """
    context = _build_context(claims, lease_fields, deposit_amount, property_label)

    if doc_type == "message":
        system_extra = _MESSAGE_SYSTEM_EXTRA
        user_prompt = _MESSAGE_USER_PROMPT.format(context=context)
    else:
        system_extra = _FORMAL_LETTER_SYSTEM_EXTRA
        user_prompt = _FORMAL_LETTER_USER_PROMPT.format(context=context)

    response = await ai_client.call(
        AIRequest(
            parts=[user_prompt],
            response_schema=_DOC_SCHEMA,
            system_prompt_extra=system_extra,
            temperature=0.4,   # slightly higher than extraction  documents need natural language
            document_id=str(doc_id) if doc_id else None,
        )
    )

    parsed = response.parsed
    if response.retried:
        logger.info("document_generator: %s generated after retry", doc_type)

    # Inject disclaimer server-side into formal letters — never trust the prompt alone
    if doc_type == "formal_letter":
        parsed["draft"] = parsed.get("draft", "") + _DISCLAIMER

    return parsed


def _build_context(
    claims: list[dict],
    lease_fields: dict | None,
    deposit_amount: float | None,
    property_label: str,
) -> str:
    lines = [f"PROPERTY: {property_label}"]

    if deposit_amount:
        lines.append(f"DEPOSIT AMOUNT: ₹{deposit_amount:,.0f}")

    # Pull the most useful lease fields for document context
    if lease_fields:
        refund = lease_fields.get("refund_timeline", {})
        notice = lease_fields.get("notice_period", {})
        if refund.get("value"):
            lines.append(f"LEASE REFUND CLAUSE: {refund['value']}")
        if notice.get("value"):
            lines.append(f"NOTICE PERIOD: {notice['value']}")

    # Only include disputed or unclear claims in the document — supported
    # deductions are legitimately withheld and should not be disputed
    disputed = [
        c for c in claims
        if c.get("effective_label") in ("weak", "unsupported", "unclear")
    ]
    supported = [
        c for c in claims
        if c.get("effective_label") == "supported"
    ]

    lines.append(f"\nDISPUTED DEDUCTIONS ({len(disputed)} items):")
    total_disputed = 0.0
    for i, claim in enumerate(disputed, 1):
        amount = claim.get("claimed_amount")
        amount_str = f"₹{amount:,.0f}" if amount else "amount not stated"
        if amount:
            total_disputed += float(amount)
        lines.append(f"  {i}. {claim.get('item_description')} — {amount_str}")
        lines.append(f"     Label: {claim.get('effective_label')}")
        lines.append(f"     Reasoning: {claim.get('reasoning', '')}")

        refs = claim.get("evidence_refs", {})
        clauses = refs.get("lease_clauses", [])
        ev_ids = refs.get("evidence_ids", [])
        if clauses:
            lines.append(f"     Lease clauses: {'; '.join(clauses)}")
        if ev_ids:
            lines.append(f"     Evidence IDs: {', '.join(ev_ids)}")

    if supported:
        lines.append(f"\nACCEPTED DEDUCTIONS ({len(supported)} items — do NOT dispute these):")
        for claim in supported:
            amount = claim.get("claimed_amount")
            amount_str = f"₹{amount:,.0f}" if amount else "amount not stated"
            lines.append(f"  • {claim.get('item_description')} — {amount_str}")

    lines.append(f"\nTOTAL DISPUTED: ₹{total_disputed:,.0f}")
    return "\n".join(lines)