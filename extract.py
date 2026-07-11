"""
Phase 2 — Extraction Agent

Takes clause chunks (from ingest.py) and asks the LLM to extract structured
obligations from each one. Chunks that contain no actionable obligation
(preambles, definitions, etc.) are skipped — the LLM returns an empty list
for those.

Usage:
    python extract.py data/master_circular_chunks.json
"""

import sys
import json
from llm_client import call_llm, extract_json

SYSTEM_PROMPT = """You are a regulatory compliance analyst. You are given one \
clause from a SEBI circular applicable to stockbrokers. Extract every \
distinct compliance OBLIGATION it creates.

An obligation is a specific, actionable duty imposed on the stockbroker —
not general context, definitions, or preamble. A clause may contain zero,
one, or multiple obligations.

Return ONLY a JSON array (no markdown fences, no commentary). Each element:
{
  "obligation_text": "plain-language restatement of what must be done",
  "category": "one of: KYC, risk_management, reporting, cybersecurity, \
investor_grievance, record_keeping, disclosures, governance, \
capital_adequacy, shareholding_restrictions, fees_and_payments, other",
  "frequency": "one of: one_time, daily, monthly, quarterly, annual, \
event_based, continuous",
  "evidence_required": "what document/artifact would prove compliance"
}

Pick the closest fitting category. Only use "other" if the obligation \
genuinely does not fit any listed category — do not default to it for \
convenience.

If the clause contains no actionable obligation, return an empty array: []
"""

BATCH_SYSTEM_PROMPT = """You are a regulatory compliance analyst. You are given a list of clauses from a SEBI circular applicable to stockbrokers. Extract every distinct compliance OBLIGATION they create.

An obligation is a specific, actionable duty imposed on the stockbroker — not general context, definitions, or preamble. A clause may contain zero, one, or multiple obligations.

Return ONLY a JSON array of obligations (no markdown fences, no commentary). Each element MUST include the clause_reference indicating which clause it was extracted from:
[
  {
    "clause_reference": "the exact clause_reference of the clause this obligation is extracted from",
    "obligation_text": "plain-language restatement of what must be done",
    "category": "one of: KYC, risk_management, reporting, cybersecurity, investor_grievance, record_keeping, disclosures, governance, capital_adequacy, shareholding_restrictions, fees_and_payments, other",
    "frequency": "one of: one_time, daily, monthly, quarterly, annual, event_based, continuous",
    "evidence_required": "what document/artifact would prove compliance"
  }
]

Pick the closest fitting category. Only use "other" if the obligation genuinely does not fit any listed category — do not default to it for convenience.

If none of the clauses contain any actionable obligation, return an empty array: []
"""


def extract_from_chunk(chunk: dict) -> list:
    user_prompt = f"Clause {chunk['clause_reference']}:\n\n{chunk['text']}"
    raw = call_llm(SYSTEM_PROMPT, user_prompt)
    try:
        obligations = extract_json(raw)
    except (json.JSONDecodeError, IndexError, KeyError):
        print(f"  [warn] Could not parse LLM output for clause "
              f"{chunk['clause_reference']}, skipping.")
        return []

    for ob in obligations:
        ob["clause_reference"] = chunk["clause_reference"]
    return obligations


def extract_from_chunks_batch(chunks: list) -> list:
    if not chunks:
        return []

    formatted_chunks = []
    for chunk in chunks:
        formatted_chunks.append(f"Clause {chunk['clause_reference']}:\n\n{chunk['text']}")
    user_prompt = "\n\n---\n\n".join(formatted_chunks)

    # Use max_tokens=4000 to hold all batch extraction outputs
    raw = call_llm(BATCH_SYSTEM_PROMPT, user_prompt, max_tokens=4000)
    try:
        obligations = extract_json(raw)
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"  [warn] Could not parse batch LLM output, falling back to individual extraction. Error: {e}")
        obligations = []
        for chunk in chunks:
            obligations.extend(extract_from_chunk(chunk))
        return obligations

    if not isinstance(obligations, list):
        print("  [warn] Batch LLM output is not a list, falling back to individual extraction.")
        obligations = []
        for chunk in chunks:
            obligations.extend(extract_from_chunk(chunk))
        return obligations

    valid_obligations = []
    for ob in obligations:
        if isinstance(ob, dict):
            if "clause_reference" not in ob or not ob["clause_reference"]:
                ob["clause_reference"] = chunks[0]["clause_reference"]
            valid_obligations.append(ob)

    return valid_obligations


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract.py <path_to_chunks.json>")
        sys.exit(1)

    chunks_path = sys.argv[1]
    with open(chunks_path) as f:
        chunks = json.load(f)

    all_obligations = []
    batch_size = 10
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        print(f"[{i+1}-{min(i+batch_size, len(chunks))}/{len(chunks)}] Extracting from batch...")
        obligations = extract_from_chunks_batch(batch)
        all_obligations.extend(obligations)
        print(f"  -> {len(obligations)} obligation(s) found in batch")

    out_path = chunks_path.replace("_chunks.json", "_obligations.json")
    with open(out_path, "w") as f:
        json.dump(all_obligations, f, indent=2)

    print(f"\nDone. {len(all_obligations)} total obligations extracted.")
    print(f"Saved to {out_path}")



if __name__ == "__main__":
    main()