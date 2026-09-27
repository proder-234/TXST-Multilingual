# Multilingual Commonsense Ethics Evaluation

Evaluates LLMs on the [ETHICS commonsense](https://huggingface.co/datasets/hendrycks/ethics) benchmark,
translated out of English into other languages, to see whether models judge the
same scenario differently depending on the language it's presented in.

## Directory structure

```
.
├── load_dataset.py         # pulls a 300-scenario pilot sample
├── load_dataset_full.py    # pulls every scenario (no sampling)
├── translate.py            # English -> N target languages (NLLB-200)
├── inference.py            # runs a chosen model over a chosen prompt style/language
├── metrics.py               # accuracy of a language vs. English, per model
├── mismatch.py               # scenarios where a language disagrees with English
├── prompts/
│   ├── base_prompt.py       # simple prompt, prompt template stays in English
│   └── lang_prompt.py       # fully localized prompt (instructions in Hindi/Nepali/...)
├── models/
│   ├── llama3.py            # Llama 3.1 8B via local Ollama
│   ├── qwen.py               # Qwen3 8B via mlx_lm (Apple Silicon)
│   ├── mistral.py            # Mistral-7B-Instruct via transformers
│   └── models.py             # dispatcher: name -> query_model() function
├── results/                  # all CSV outputs land here
└── requirements.txt
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- `models/mistral.py` needs a `HUGGINGFACE_API_KEY` in a `.env` file at the project root.
- `models/llama3.py` expects an [Ollama](https://ollama.com) server running locally
  (`ollama serve`) with the model pulled (`ollama pull llama3.1:8b`).
- `models/qwen.py` uses `mlx_lm`, which requires Apple Silicon (M-series Mac).

You don't need all three set up -- only whichever model(s) you plan to run.

## Usage

**1. Load scenarios**

```bash
python load_dataset.py          # 300-scenario pilot -> results/ethics_pilot.csv
# or
python load_dataset_full.py     # full dataset -> results/ethics_pilot.csv
```

**2. Translate into target languages**

```bash
python translate.py                         # translates into every language in LANGUAGES
python translate.py --langs hi              # Hindi only
python translate.py --langs hi ne           # Hindi + Nepali
```
Output: `results/ethics_translated.csv` (with `en_text`, `hi_text`, `ne_text`, ... columns).

**3. Run inference**

```bash
python inference.py --lang hi --model mistral --prompt lang
```
Any flag you leave out (`--lang`, `--model`, `--prompt`) is asked for interactively.
Output: `results/eval_<lang>_<model>.csv` (e.g. `results/eval_hi_mistral.csv`).

Run this once per language you want to compare (including `en`, so you have an
English baseline to compare against) with the same `--model`.

**4. Compare accuracy against English**

```bash
python metrics.py --lang hi --model mistral
```
Reads `results/eval_en_mistral.csv` and `results/eval_hi_mistral.csv`, prints accuracy.

**5. Find mismatches**

```bash
python mismatch.py --lang hi --model mistral
```
Saves `results/mismatch_hi_mistral.csv` with every scenario where Hindi and English
predictions disagreed, and prints the count + item IDs.

## Adding a new language

Three places need an entry (all keyed by the same short code, e.g. `"bn"` for Bengali):

1. **`translate.py`** -- add to `LANGUAGES`:
   ```python
   LANGUAGES = {
       "hi": {"col": "hi_text", "nllb": "hin_Deva"},
       "ne": {"col": "ne_text", "nllb": "npi_Deva"},
       "bn": {"col": "bn_text", "nllb": "ben_Beng"},  # new
   }
   ```
   Find the NLLB-200 code for your language in the
   [FLORES-200 language list](https://github.com/facebookresearch/flores/blob/main/flores200/README.md).

2. **`prompts/base_prompt.py`** -- add to `LANG_COL`:
   ```python
   LANG_COL = {"en": "en_text", "hi": "hi_text", "ne": "ne_text", "bn": "bn_text"}
   ```

3. **`prompts/lang_prompt.py`** -- add to `LANG_COL`, `LANG_NAME`, and (optionally,
   for a fully localized prompt instead of the English-template fallback) `LOCALIZED`:
   ```python
   LANG_COL["bn"] = "bn_text"
   LANG_NAME["bn"] = "Bengali"
   LOCALIZED["bn"] = {
       "header": "...",            # instructions, in Bengali
       "reasoning_note": "...",    # language requirement, in Bengali
       "reasoning_footer": "...",  # output format rules + example, in Bengali
   }
   ```
   If you skip the `LOCALIZED` entry, `generate_prompt` automatically falls back to
   `BASE_PROMPT` with `target_language` set to whatever you put in `LANG_NAME`.

Once all three are updated, `bn` becomes a valid `--langs`/`--lang` choice everywhere
(`translate.py`, `inference.py`, `metrics.py`, `mismatch.py`) with no other code changes.

## Adding a new model

1. Create `models/<name>.py` with a `query_model(prompt, ...)` function that returns
   `(full_response, score, justification)` -- copy the shape of `models/mistral.py`,
   `models/llama3.py`, or `models/qwen.py`, whichever is closest to how your model is served.
2. Add `"<name>"` to `AVAILABLE_MODELS` in `models/models.py`.

`inference.py`, `metrics.py`, and `mismatch.py` all refer to models only by name
string, so nothing else needs to change.
