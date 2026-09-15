import re
import requests

MODEL_ID = "llama3"
OLLAMA_URL = "http://localhost:11434/api/generate"

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


def _parse(full_response):
    """Extract a strict 0/1 response + justification, or None if malformed."""
    score, justification = None, ""

    m = re.search(r"response\s*:\s*(.+)", full_response, re.IGNORECASE)
    if m:
        raw = m.group(1).splitlines()[0]
        cleaned = re.sub(r"[\*\[\]`\s\.]", "", raw)
        if cleaned in ("0", "1"):
            score = cleaned

    m = re.search(r"justification\s*:\s*(.*)", full_response, re.IGNORECASE | re.DOTALL)
    if m:
        justification = m.group(1).strip()

    return score, justification


def query_model(prompt, max_new_tokens=220):
    data = {
        "model": MODEL_ID,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_new_tokens,
        },
    }

    response = requests.post(OLLAMA_URL, json=data)

    if response.status_code != 200:
        return f"Error: {response.status_code}", None, None

    result = response.json()
    raw = result.get("response", "").strip()
    full_response = _THINK_BLOCK.sub("", raw).strip()
    score, justification = _parse(full_response)

    return full_response, score, justification