# RegOps Prototype — 

This is the working slice for the demo: **ingest a SEBI circular → extract
structured obligations → diff against a baseline**. No database, no
frontend framework — just Python + Streamlit, built to be recordable for
the demo video fast.

## Setup (5 minutes)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a free LLM API key** (pick one):
   - **Free option (recommended):** Google Gemini — go to
     https://aistudio.google.com/apikey, sign in with any Google account,
     click "Create API key". No card required.
     ```bash
     export GEMINI_API_KEY=your_key_here
     ```
   - **Paid option (higher quality):** Anthropic Claude — go to
     https://console.anthropic.com, create a key.
     ```bash
     export ANTHROPIC_API_KEY=your_key_here
     ```
   Only set ONE of these — the code auto-detects which is present.

3. **Get a sample circular PDF:**
   Download SEBI's Master Circular for Stockbrokers from SEBI's website
   (search "SEBI Master Circular Stockbrokers" — it's on sebi.gov.in under
   Legal > Circulars) and save it to `data/master_circular.pdf`.
   For the "new circular" side of the diff, grab any subsequent amendment
   circular for stockbrokers and save it to `data/new_circular.pdf`.

## Running it — command line (fastest way to test each phase)

```bash
# Phase 1: parse and chunk the PDF
python ingest.py data/master_circular.pdf
# -> creates data/master_circular_chunks.json

# Phase 2: extract structured obligations
python extract.py data/master_circular_chunks.json
# -> creates data/master_circular_obligations.json

# Repeat both for the newer circular
python ingest.py data/new_circular.pdf
python extract.py data/new_circular_chunks.json

# Phase 3: diff the new circular's obligations against the baseline
python diff.py data/master_circular_obligations.json data/new_circular_obligations.json
# -> creates data/new_circular_diff.json, prints a summary count
```

## Running it — the demo UI (use this for the video recording)

```bash
streamlit run app.py
```

Opens a browser tab with three tabs: Ingest & Extract, Baseline Register,
Diff. Walk through them in order for the recording — this is the "live"
version of the CLI steps above, and it's what makes the demo look like a
real product instead of terminal output.
