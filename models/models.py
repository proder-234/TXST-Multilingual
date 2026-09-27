import re

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_LEADING_DIGIT_RE = re.compile(r"\b([01])\b")

AVAILABLE_MODELS = ["mistral", "qwen", "ollama"]


def _truncate_rambling(text):
    """Cut off if the model starts a second 'response:' block."""
    matches = list(re.finditer(r"response\s*:", text, re.IGNORECASE))
    if len(matches) > 1:
        return text[: matches[1].start()].strip()
    return text


def clean(raw, truncate=False):
    """Strip <think> blocks and (optionally) cut off rambling repeats."""
    text = _THINK_BLOCK.sub("", raw).strip()
    if truncate:
        text = _truncate_rambling(text)
    return text


def parse(full_response, fallback=None):
    """Extract a strict 0/1 response + justification, or None if malformed.

    fallback:
        None            - no extra fallback (strict "response:"/"justification:" only)
        "bare_line"     - if no "response:" label, treat a bare 0/1 first line as the score
        "leading_digit" - if no "response:" label, grab the first standalone 0/1 anywhere
    """
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

    if score is None and fallback == "bare_line":
        lines = [l.strip() for l in full_response.splitlines() if l.strip()]
        if lines:
            first_cleaned = re.sub(r"[\*\[\]`\s\.]", "", lines[0])
            if first_cleaned in ("0", "1"):
                score = first_cleaned
                if not justification:
                    justification = "\n".join(lines[1:]).strip()
    elif score is None and fallback == "leading_digit":
        m2 = _LEADING_DIGIT_RE.search(full_response)
        if m2:
            score = m2.group(1)

    return score, justification


def get_query_model(model_name):
    """Return the query_model(prompt, ...) function for the chosen backend.

    Imports are done lazily, inside each branch, so picking one model doesn't
    require every backend's dependencies (torch, mlx_lm, requests) to be
    installed/loaded at once.
    """
    if model_name == "mistral":
        from .mistral import query_model
    elif model_name == "qwen":
        from .qwen import query_model
    elif model_name == "ollama":
        from .llama import query_model
    else:
        raise ValueError(f"Unknown model '{model_name}'. Choose from {AVAILABLE_MODELS}")

    return query_model