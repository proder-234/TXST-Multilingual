import re
import pandas as pd
from sklearn.metrics import accuracy_score

def get_prediction(text):
    m = re.search(r"response:\s*([01])", str(text), re.I)
    return int(m.group(1)) if m else None


def load(path, language, condition):
    df = pd.read_csv(path)
    df["prediction"] = df["output"].apply(get_prediction)
    df = df.dropna(subset=["prediction"])

    return df.assign(
        language=language,
        condition=condition,
        item_id=df["input_id"]
    )[["language", "condition", "item_id", "prediction"]]

files = [
    ("result/eval_en.csv", "English", "reference"),
    ("result/eval_hi_p1.csv", "Hindi", "p1"),
    # ("result/eval_hi_p2.csv", "Hindi", "p2"),  # skipped for now
    ("result/eval_hi_p3.csv", "Hindi", "p3"),
]

df = pd.concat([load(path, lang, cond) for path, lang, cond in files])

english = df[df.language == "English"]
reference = dict(zip(english.item_id, english.prediction))

df = df[df.language != "English"].copy()
df["label"] = df.item_id.map(reference)

result = (
    df.dropna(subset=["label"])
      .groupby(["language", "condition"])
      .apply(lambda x: accuracy_score(x.label.astype(int), x.prediction.astype(int)))
)
print(result)

# Pairwise agreement between conditions on the same item -- separate from
# accuracy against the English reference, this tells you how much the
# model's own answer changes purely because of prompt wording.
pivot = df.pivot_table(index="item_id", columns="condition", values="prediction")
pivot = pivot.dropna()
print(f"\nHindi pairwise condition agreement (n={len(pivot)}):")
for a, b in [("p1", "p3")]:  # add ("p1", "p2"), ("p2", "p3") back once p2 is ready
    agree = (pivot[a] == pivot[b]).mean()
    print(f"  {a} vs {b}: {agree:.3f}")