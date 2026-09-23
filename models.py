import os
import re

import torch
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer

load_dotenv()
huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")

MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"
USE_4BIT = False  

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)

# Pick the best available device: Apple Silicon GPU (MPS) > CUDA > CPU
if torch.backends.mps.is_available():
    _device = torch.device("mps")
elif torch.cuda.is_available():
    _device = torch.device("cuda")
else:
    _device = torch.device("cpu")

print(f"[models.py] Loading {MODEL_ID} on device: {_device}")


def _load_model():
    kwargs = {"token": huggingface_api_key}
    fp = torch.float16 if _device.type in ("mps", "cuda") else torch.float32

    # 4-bit path (CUDA only). Quantized models must not be moved with .to()
    if USE_4BIT and _device.type == "cuda":
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )
        kwargs["device_map"] = "auto"
        return AutoModelForCausalLM.from_pretrained(MODEL_ID, **kwargs)

    # Normal path. `dtype` is for newer transformers, `torch_dtype` for older ones
    try:
        model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype=fp, **kwargs)
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=fp, **kwargs)
    return model.to(_device)


try:
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=huggingface_api_key)
    _model = _load_model()
    _model.eval()
except Exception as e:
    raise RuntimeError(f"Error loading model or tokenizer: {str(e)}")

if _tokenizer.pad_token is None:
    _tokenizer.pad_token = _tokenizer.eos_token


def _truncate_rambling(text):
    """Cut off if the model starts a second 'response:' block."""
    matches = list(re.finditer(r"response\s*:", text, re.IGNORECASE))
    if len(matches) > 1:
        return text[: matches[1].start()].strip()
    return text


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

    # Fallback: model just emits a bare 0/1 on the first line without labels
    if score is None:
        lines = [l.strip() for l in full_response.splitlines() if l.strip()]
        if lines:
            first_cleaned = re.sub(r"[\*\[\]`\s\.]", "", lines[0])
            if first_cleaned in ("0", "1"):
                score = first_cleaned
                if not justification:
                    justification = "\n".join(lines[1:]).strip()

    return score, justification


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

    full_response = _THINK_BLOCK.sub("", raw).strip()
    full_response = _truncate_rambling(full_response)
    score, justification = _parse(full_response)

    return full_response, score, justification
