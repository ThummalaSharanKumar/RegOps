"""
Phase 3 — Diff / Change-Detection Agent

Compares a NEW circular's extracted obligations against a BASELINE set
(e.g. the master circular) and classifies each new obligation as:
  - "new"        : no similar obligation exists in the baseline
  - "amended"     : a similar obligation exists but wording differs meaningfully
  - "unchanged"   : matches an existing obligation closely

Uses the LLM for the classification since this needs semantic comparison,
not just string matching (circulars rarely repeat obligations verbatim).

Usage:
    python diff.py data/baseline_obligations.json data/new_obligations.json
"""

import sys
import json
from llm_client import call_llm, extract_json

SYSTEM_PROMPT = """You compare a NEW regulatory obligation against a list of \
EXISTING baseline obligations for the same intermediary category.

Classify the NEW obligation as exactly one of:
- "new": no existing obligation covers this requirement
- "amended": an existing obligation covers similar ground but this version \
changes the requirement (different frequency, different scope, different \
deadline, added/removed duty)
- "unchanged": an existing obligation already says essentially the same thing

Return ONLY a JSON object (no markdown fences, no commentary):
{
  "classification": "new" | "amended" | "unchanged",
  "matched_baseline_obligation": "the closest matching baseline obligation \
text, or null if none",
  "reasoning": "one sentence explaining the classification"
}
"""

BATCH_SYSTEM_PROMPT = """You compare a list of NEW regulatory obligations against a list of EXISTING baseline obligations for the same intermediary category.

For EACH new obligation, classify it as exactly one of:
- "new": no existing obligation covers this requirement
- "amended": an existing obligation covers similar ground but this version changes the requirement (different frequency, different scope, different deadline, added/removed duty)
- "unchanged": an existing obligation already says essentially the same thing

Return ONLY a JSON array of objects (no markdown fences, no commentary). Each element must correspond to a new obligation and contain its exact text, classification, matched baseline obligation, and reasoning:
[
  {
    "obligation_text": "the exact text of the new obligation being classified",
    "classification": "new" | "amended" | "unchanged",
    "matched_baseline_obligation": "the closest matching baseline obligation text, or null if none",
    "reasoning": "one sentence explaining the classification"
  }
]
"""


def classify_obligation(new_obligation: dict, baseline: list) -> dict:
    baseline_texts = "\n".join(
        f"- {ob['obligation_text']}" for ob in baseline
    ) or "(no baseline obligations provided)"

    user_prompt = (
        f"NEW obligation:\n{new_obligation['obligation_text']}\n\n"
        f"EXISTING baseline obligations:\n{baseline_texts}"
    )
    raw = call_llm(SYSTEM_PROMPT, user_prompt, max_tokens=500)
    try:
        result = extract_json(raw)
    except (json.JSONDecodeError, IndexError, KeyError):
        result = {
            "classification": "new",
            "matched_baseline_obligation": None,
            "reasoning": "Could not parse classifier output; defaulted to 'new'.",
        }
    return result


def classify_obligations_batch(new_obligations: list, baseline: list) -> list:
    if not new_obligations:
        return []

    baseline_texts = "\n".join(
        f"- {ob['obligation_text']}" for ob in baseline
    ) or "(no baseline obligations provided)"

    new_texts = "\n".join(
        f"{i+1}. {ob['obligation_text']}" for i, ob in enumerate(new_obligations)
    )

    user_prompt = (
        f"NEW obligations to classify:\n{new_texts}\n\n"
        f"EXISTING baseline obligations:\n{baseline_texts}"
    )

    # Use max_tokens=4000 to hold batch classification response
    raw = call_llm(BATCH_SYSTEM_PROMPT, user_prompt, max_tokens=4000)
    try:
        classifications = extract_json(raw)
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"  [warn] Could not parse batch classifier output, falling back to individual classification. Error: {e}")
        classifications = []
        for ob in new_obligations:
            classifications.append(classify_obligation(ob, baseline))
        results = []
        for ob, clf in zip(new_obligations, classifications):
            results.append({**ob, **clf})
        return results

    if not isinstance(classifications, list) or len(classifications) != len(new_obligations):
        print(f"  [warn] Batch size mismatch or invalid format (expected {len(new_obligations)} items, got {len(classifications) if isinstance(classifications, list) else type(classifications)}), falling back to individual classification.")
        results = []
        for ob in new_obligations:
            clf = classify_obligation(ob, baseline)
            results.append({**ob, **clf})
        return results

    results = []
    for ob, clf in zip(new_obligations, classifications):
        # We merge based on matching index
        results.append({**ob, **clf})
    return results


def main():
    if len(sys.argv) < 3:
        print("Usage: python diff.py <baseline_obligations.json> "
              "<new_obligations.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        baseline = json.load(f)
    with open(sys.argv[2]) as f:
        new_obligations = json.load(f)

    # Classify in batches of 10 to keep prompts manageable and avoid timeouts
    batch_size = 10
    results = []
    
    for i in range(0, len(new_obligations), batch_size):
        batch = new_obligations[i:i+batch_size]
        print(f"[{i+1}-{min(i+batch_size, len(new_obligations))}/{len(new_obligations)}] Classifying new obligations...")
        batch_results = classify_obligations_batch(batch, baseline)
        results.extend(batch_results)

    out_path = sys.argv[2].replace("_obligations.json", "_diff.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    counts = {}
    for r in results:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    print(f"\nDone. {counts}")
    print(f"Saved to {out_path}")



if __name__ == "__main__":
    main()
