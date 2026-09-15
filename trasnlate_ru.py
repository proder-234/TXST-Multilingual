import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL = "facebook/nllb-200-1.3B"

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


def strip_forum_tags(text):
    return re.sub(
        r"^(AITA|WIBTA|Aitah?)\b[:\-\|]?\s*",
        "",
        str(text),
        flags=re.IGNORECASE
    ).strip()


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


def translate_batch(batch):
    tokenizer.src_lang = "eng_Latn"

    inputs = tokenizer(
        batch,
        return_tensors="pt",
        padding=True,
        truncation=False
    ).to(device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids("rus_Cyrl"),
            max_length=250,
            num_beams=1
        )

    return tokenizer.batch_decode(output, skip_special_tokens=True)


if __name__ == "__main__":
    df = pd.read_csv("result/ethics_pilot.csv")

    if "input" in df.columns:
        df = df.rename(columns={"input": "en_text"})

    df["en_text"] = df["en_text"].apply(strip_forum_tags)

    results = []

    for i, text in enumerate(df["en_text"], 1):
        print(f"Translating {i}/{len(df)}...")

        chunks = split_text(text)
        translated = []

        for j in range(0, len(chunks), 8):
            translated.extend(translate_batch(chunks[j:j + 8]))

        results.append(" ".join(translated))

    df["ru_text"] = results
    df.to_csv("result/translated_ru.csv", index=False)

    print("Done!")
    print("Saved to result/translated_ru.csv")