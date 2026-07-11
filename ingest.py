"""
Phase 1 — Ingestion Agent

Parses a SEBI circular PDF and chunks it into clause-level pieces so each
chunk can be sent to the Extraction Agent independently, preserving clause
numbering for traceability.

Usage:
    python ingest.py data/master_circular.pdf
"""

import sys
import re
import json
import pdfplumber

# Matches clause headers like "1.", "1.1", "2.3.4", "Clause 5" at line start.
CLAUSE_PATTERN = re.compile(r"^\s*(\d+(\.\d+)*)\.?\s+", re.MULTILINE)


def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def chunk_by_clause(full_text: str, min_chunk_len: int = 40):
    """Splits text on clause-number boundaries. Falls back to paragraph
    splitting if no clause numbering is detected (some circulars are less
    structured)."""

    matches = list(CLAUSE_PATTERN.finditer(full_text))
    chunks = []

    if len(matches) < 3:
        # Fallback: split on blank lines / paragraphs
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        for i, p in enumerate(paragraphs):
            if len(p) >= min_chunk_len:
                chunks.append({"clause_reference": f"para_{i+1}", "text": p})
        return chunks

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        clause_ref = match.group(1)
        chunk_text = full_text[start:end].strip()
        if len(chunk_text) >= min_chunk_len:
            chunks.append({"clause_reference": clause_ref, "text": chunk_text})

    return chunks


def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <path_to_circular.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"Parsing {pdf_path} ...")
    full_text = extract_text(pdf_path)
    print(f"Extracted {len(full_text)} characters.")

    chunks = chunk_by_clause(full_text)
    print(f"Split into {len(chunks)} clause-level chunks.")

    out_path = pdf_path.rsplit(".", 1)[0] + "_chunks.json"
    with open(out_path, "w") as f:
        json.dump(chunks, f, indent=2)
    print(f"Saved chunks to {out_path}")


if __name__ == "__main__":
    main()
