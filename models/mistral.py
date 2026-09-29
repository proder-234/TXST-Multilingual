import os

import torch
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer

from .models import clean, parse

load_dotenv()
huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")

MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"

print(f"[models/mistral.py] Loading {MODEL_ID}")


def _load_model():
    kwargs = {"token": huggingface_api_key, "device_map": "auto"}
    # `dtype` is for newer transformers, `torch_dtype` for older ones
    try:
        return AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype="auto", **kwargs)
    except TypeError:
        return AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype="auto", **kwargs)


try:
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=huggingface_api_key)
    _model = _load_model()
    _model.eval()
except Exception as e:
    raise RuntimeError(f"Error loading model or tokenizer: {str(e)}")

if _tokenizer.pad_token is None:
    _tokenizer.pad_token = _tokenizer.eos_token


def query_model(prompt, max_new_tokens=220):
    messages = [{"role": "user", "content": prompt}]
    prompt_text = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _tokenizer(
        prompt_text, return_tensors="pt", add_special_tokens=False
    ).to(_model.device)

    try:
        with torch.no_grad():
            outputs = _model.generate(
                **inputs,  # passes input_ids and attention_mask
                max_new_tokens=max_new_tokens,
                do_sample=False,  # deterministic
                pad_token_id=_tokenizer.pad_token_id,
            )
    except Exception as e:
        return f"Error: {str(e)}", None, None

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    raw = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    full_response = clean(raw, truncate=True)
    score, justification = parse(full_response, fallback="bare_line")

    return full_response, score, justification