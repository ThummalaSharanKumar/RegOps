"""
LLM client abstraction for RegOps.

Two backends supported — pick whichever API key you have:

1. Anthropic (Claude) — no permanent free tier, but highest quality extraction.
   Set env var: ANTHROPIC_API_KEY
   Get a key at: https://console.anthropic.com

2. Google Gemini — genuinely free tier, no card required. Recommended if you
   want zero cost for the 3-day prototype.
   Set env var: GEMINI_API_KEY
   Get a key at: https://aistudio.google.com/apikey

Only ONE of these needs to be set. The code auto-detects which key is present.
If neither is set, call_llm() raises a clear error telling you what to do.
"""

import os
import json

# Try to load .env if it exists
def load_env_file():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

# Run once on import
load_env_file()


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Sends a prompt to whichever LLM backend has a key configured.
    Returns the raw text response."""

    # Reload env dynamically to pick up any updates to .env while server is running
    load_env_file()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if anthropic_key:
        print("🔑 Anthropic API key successfully detected.")
        return _call_anthropic(system_prompt, user_prompt, max_tokens)
    elif gemini_key:
        print("🔑 Gemini API key successfully detected.")
        return _call_gemini(system_prompt, user_prompt, max_tokens)
    else:
        raise RuntimeError(
            "No LLM API key found.\n"
            "Set ONE of these environment variables:\n"
            "  export ANTHROPIC_API_KEY=your_key_here   (paid, no free tier)\n"
            "  export GEMINI_API_KEY=your_key_here      (free tier, get one at "
            "https://aistudio.google.com/apikey)\n"
        )


def _call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    import anthropic

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=anthropic_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def _call_gemini(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    import urllib.request
    import urllib.error
    import time
    import random

    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={gemini_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]} ,
        "generationConfig": {"maxOutputTokens": max_tokens},
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    max_retries = 6
    base_wait = 2

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                # Exponential backoff with random jitter
                wait = min(60, (base_wait ** attempt) + random.uniform(0.1, 1.0))
                print(f"⚠️ Gemini request failed with HTTP {e.code}. Retrying in {wait:.2f}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
        except Exception as err:
            # Catch raw connection issues and try to retry
            if attempt < max_retries - 1:
                wait = min(60, (base_wait ** attempt) + random.uniform(0.1, 1.0))
                print(f"⚠️ Gemini connection error: {err}. Retrying in {wait:.2f}s...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("Gemini request failed after multiple retries due to rate limits or unavailability.")


def extract_json(raw_text: str):
    """LLMs sometimes wrap JSON in markdown fences — strip that before parsing."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())
