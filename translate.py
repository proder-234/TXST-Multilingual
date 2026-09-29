import argparse
import re

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL = "facebook/nllb-200-1.3B"

# --------------------------------------------------------------------------
# Language registry -- ADD NEW LANGUAGES HERE.
#
#   key  = short language code used everywhere else in the project
#          (--langs on the CLI, prompts/*.py, results/eval_<lang>_<model>.csv, ...)
#   col  = column name written into results/ethics_translated.csv
#   nllb = NLLB-200 language code, see:
#          https://github.com/facebookresearch/flores/blob/main/flores200/README.md
#
# See README.md -> "Adding a new language" for the full walkthrough
# (this also needs a matching entry in prompts/lang_prompt.py's LANG_NAME /
# LOCALIZED, and prompts/base_prompt.py's LANG_COL, if you want prompts and
# inference to work for it too).
# --------------------------------------------------------------------------
LANGUAGES = {
    "hi": {"col": "hi_text", "nllb": "hin_Deva"},
    "ne": {"col": "ne_text", "nllb": "npi_Deva"},
    "de": {"col": "de_text", "nllb": "deu_Latn"},
    "zh": {"col": "zh_text", "nllb": "zho_Hans"},
    "es": {"col": "es_text", "nllb": "spa_Latn"},
    "fr": {"col": "fr_text", "nllb": "fra_Latn"},
}

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
print("Loading model...")
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)

if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
print(f"Using device: {device}")

model = model.to(device)
model.eval()
print("Model ready!")


# Remove Reddit tags
def strip_forum_tags(text):
    return re.sub(
        r"^(AITA|WIBTA|Aitah?)\b[:\-\|]?\s*",
        "",
        str(text),
        flags=re.IGNORECASE
    ).strip()


# Split long scenarios
def split_text(text, max_tokens=400):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sentence in sentences:
        test = (current + " " + sentence).strip()
        if len(tokenizer.encode(test)) <= max_tokens:
            current = test
        else:
            if current:
                chunks.append(current)
            # Handle very long single sentences
            words = sentence.split()
            current = ""
            for word in words:
                test = (current + " " + word).strip()
                if len(tokenizer.encode(test)) <= max_tokens:
                    current = test
                else:
                    if current:
                        chunks.append(current)
                    current = word
    if current:
        chunks.append(current)
    return chunks


# Translate a batch
def translate_batch(batch, src_lang, tgt_lang):
    tokenizer.src_lang = src_lang
    inputs = tokenizer(
        batch,
        return_tensors="pt",
        padding=True,
        truncation=False
    ).to(device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_lang),
            max_length=250,
            num_beams=1
        )
    return tokenizer.batch_decode(
        output,
        skip_special_tokens=True
    )


# Translate all scenarios to MULTIPLE target languages in one pass, so
# each row is only split into chunks once, no matter how many target
# languages it's translated into.
def translate_multi(texts, src_lang, tgt_langs, batch_size=8):
    """
    tgt_langs: dict of {output_key: nllb_lang_code}, e.g.
        {"hi_text": "hin_Deva", "ne_text": "npi_Deva"}

    Returns: dict of {output_key: [translated_text, ...]} aligned to `texts`.
    """
    results = {key: [] for key in tgt_langs}

    for index, text in enumerate(texts):
        print(f"Translating {index + 1}/{len(texts)}...", flush=True)
        text = str(text).strip()
        chunks = split_text(text, max_tokens=400)  # done once per row

        for key, tgt_lang in tgt_langs.items():
            translated_chunks = []
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                translated_chunks.extend(
                    translate_batch(batch, src_lang, tgt_lang)
                )
            results[key].append(" ".join(translated_chunks))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Translate English scenarios into one or more target languages."
    )
    parser.add_argument("--input_csv", default="results/ethics_pilot.csv")
    parser.add_argument("--output_csv", default="results/ethics_translated.csv")
    parser.add_argument(
        "--langs",
        nargs="+",
        choices=list(LANGUAGES.keys()),
        default=list(LANGUAGES.keys()),
        help="Target language code(s) to translate into (space-separated).",
    )
    parser.add_argument("--src_lang", default="eng_Latn")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Load --output_csv if it exists and add/replace only the columns "
             "for --langs, keeping all other existing translations.",
    )
    args = parser.parse_args()

    if args.append:
        print(f"Append mode: reading existing {args.output_csv}...")
        df = pd.read_csv(args.output_csv)
    else:
        print("Reading input CSV...")
        df = pd.read_csv(args.input_csv)
        if "input" in df.columns:
            df = df.rename(columns={"input": "en_text"})
        df["en_text"] = df["en_text"].apply(strip_forum_tags)
    print(f"Loaded {len(df)} rows.")

    tgt_langs = {LANGUAGES[code]["col"]: LANGUAGES[code]["nllb"] for code in args.langs}

    print(f"Translating English -> {', '.join(args.langs)}...")
    translations = translate_multi(
        df["en_text"].tolist(),
        src_lang=args.src_lang,
        tgt_langs=tgt_langs,
        batch_size=args.batch_size,
    )
    for code in args.langs:
        col = LANGUAGES[code]["col"]
        df[col] = translations[col]

    df.to_csv(args.output_csv, index=False)
    print("Done!")
    print(f"Saved to {args.output_csv}")

if __name__ == "__main__":
    main()
