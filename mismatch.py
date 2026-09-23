import re
import pandas as pd

def load(path, language):
    df = pd.read_csv(path)
    df["prediction"] = df["output"].str.extract(
        r"response:\s*([01])", expand=False
    )
    df = df.dropna(subset=["prediction"])
    df["prediction"] = df["prediction"].astype(int)
    return df.assign(language=language, item_id=df["input_id"])[
        ["language", "item_id", "prediction", "output"]
    ]

files = [
    ("result/eval_en.csv", "English"),
    ("result/eval_hi.csv", "Hindi"),
    ("result/eval_ne.csv", "Nepali"),
]

df = pd.concat([load(path, lang) for path, lang in files])

english = df[df.language == "English"].set_index("item_id")

def mismatches(language):
    lang = df[df.language == language].set_index("item_id")
    joined = lang.join(english, lsuffix="_lang", rsuffix="_en")
    return joined[joined.prediction_lang != joined.prediction_en]

for language in ["Hindi", "Nepali"]:
    result = mismatches(language)
    print(f"\n{language} mismatches: {len(result)}")
    print(result.index.tolist())
    result.to_csv(f"result/mismatch_{language.lower()[:2]}.csv")
