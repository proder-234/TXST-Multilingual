from mlx_lm import load, generate

from .models import clean, parse

MODEL_ID = "mlx-community/Qwen3-8B-4bit"

_model, _tokenizer = load(MODEL_ID)


def query_model(prompt, max_new_tokens=220):
    messages = [{"role": "user", "content": prompt}]
    text = _tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, enable_thinking=False
    )

    raw = generate(_model, _tokenizer, prompt=text, max_tokens=max_new_tokens, verbose=False).strip()
    full_response = clean(raw)
    score, justification = parse(full_response)

    return full_response, score, justification
