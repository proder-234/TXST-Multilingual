import argparse
import re

import pandas as pd
from sklearn.metrics import accuracy_score


def get_prediction(text):
    m = re.search(r"response:\s*([01])", str(text), re.I)
    return int(m.group(1)) if m else None


def load(path, language):
    df = pd.read_csv(path)
    df["prediction"] = df["output"].apply(get_prediction)
    df = df.dropna(subset=["prediction"])

    return df.assign(
        language=language,
        item_id=df["input_id"].astype(int)
    )[["language", "item_id", "prediction"]]


def compute_accuracy(lang, model_name, results_dir="results"):
    """Accuracy of `lang`'s predictions against English's, for the same model."""
    en_path = f"{results_dir}/eval_en_{model_name}.csv"
    lang_path = f"{results_dir}/eval_{lang}_{model_name}.csv"

    english = load(en_path, "English")
    other = load(lang_path, lang)

    reference = dict(zip(english.item_id, english.prediction))
    other = other.copy()
    other["label"] = other.item_id.map(reference)
    other = other.dropna(subset=["label"])

    return accuracy_score(other.label, other.prediction)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare a language's predictions against English, for the same model."
    )
    parser.add_argument("--lang", required=True, help="Language code to compare against English, e.g. hi or ne")
    parser.add_argument("--model", required=True, help="Model name used when running inference.py, e.g. mistral")
    parser.add_argument("--results_dir", default="results")
    args = parser.parse_args()

    acc = compute_accuracy(args.lang, args.model, args.results_dir)
    print(f"Accuracy ({args.lang} vs English, model={args.model}): {acc:.4f}")
