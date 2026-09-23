import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_LEADING_DIGIT_RE = re.compile(r"\b([01])\b")


def _parse(full_response):
    """Extract a strict 0/1 response + justification, or None if malformed."""
    score, justification = None, ""

    m = re.search(r"response\s*:\s*(.+)", full_response, re.IGNORECASE)
    if m:
        raw = m.group(1).splitlines()[0]
        cleaned = re.sub(r"[\*\[\]`\s\.]", "", raw)
        if cleaned in ("0", "1"):
            score = cleaned

    if score is None:
        m2 = _LEADING_DIGIT_RE.search(full_response)
        if m2:
            score = m2.group(1)

    m = re.search(r"justification\s*:\s*(.*)", full_response, re.IGNORECASE | re.DOTALL)
    if m:
        justification = m.group(1).strip()

    return score, justification


def query_model(prompt, model_id="llama3.1:8b", max_new_tokens=220, temperature=0.0):
    prompt_with_prefill = prompt.rstrip() + "\nresponse: "

    data = {
        "model": model_id,
        "prompt": prompt_with_prefill,
        "stream": False,
        "options": {"num_predict": max_new_tokens, "temperature": temperature},
    }

    response = requests.post(OLLAMA_URL, json=data)
    if response.status_code != 200:
        return f"Error: {response.status_code}", None, None
    raw = response.json().get("response", "").strip()
    full_response = _THINK_BLOCK.sub("", raw).strip()
   
    score, justification = _parse("response: " + full_response)

    return full_response, score, justification