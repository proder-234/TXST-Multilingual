import argparse
import re

import pandas as pd


def get_prediction(text):
    m = re.search(r"response:\s*([01])", str(text), re.I)
    return int(m.group(1)) if m else None


def load(path, language):
    df = pd.read_csv(path)
    df["prediction"] = df["output"].apply(get_prediction)
    df = df.dropna(subset=["prediction"])
    df["prediction"] = df["prediction"].astype(int)
    return df.assign(language=language, item_id=df["input_id"])[
        ["language", "item_id", "prediction", "output"]
    ]


def find_mismatches(lang, model_name, results_dir="results"):
    """Scenarios where `lang`'s prediction disagrees with English's, for the same model."""
    en_path = f"{results_dir}/eval_en_{model_name}.csv"
    lang_path = f"{results_dir}/eval_{lang}_{model_name}.csv"

    english = load(en_path, "English").set_index("item_id")
    other = load(lang_path, lang).set_index("item_id")

    joined = other.join(english, lsuffix="_lang", rsuffix="_en")
    return joined[joined.prediction_lang != joined.prediction_en]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find scenarios where a language's prediction disagrees with English, for a given model."
    )
    parser.add_argument("--lang", required=True, help="Language code to compare against English, e.g. hi or ne")
    parser.add_argument("--model", required=True, help="Model name used when running inference.py, e.g. mistral")
    parser.add_argument("--results_dir", default="results")
    args = parser.parse_args()

    result = find_mismatches(args.lang, args.model, args.results_dir)
    output_path = f"{args.results_dir}/mismatch_{args.lang}_{args.model}.csv"
    result.to_csv(output_path)

    print(f"{args.lang} vs English ({args.model}) mismatches: {len(result)}")
    print(result.index.tolist())
    print(f"Saved to {output_path}")
