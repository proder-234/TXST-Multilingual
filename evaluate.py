import re
import pandas as pd
from sklearn.metrics import accuracy_score

from prompt import CONDITIONS


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
        item_id=df["input_id"],
    )[["language", "condition", "item_id", "prediction"]]


# English has no P1/P2/P3 -- it's the single reference run every condition
# gets scored against.
files = [("result/eval_en.csv", "English", "reference")]
for lang, name in (("hi", "Hindi"), ("ne", "Nepali")):
    for cond in CONDITIONS:
        files.append((f"result/eval_{lang}_{cond}.csv", name, cond))

dfs = []
for path, lang, cond in files:
    try:
        dfs.append(load(path, lang, cond))
    except FileNotFoundError:
        print(f"[skip] {path} not found")

df = pd.concat(dfs, ignore_index=True)

reference = dict(
    zip(
        df[df.language == "English"].item_id,
        df[df.language == "English"].prediction,
    )
)

df = df[df.language != "English"].copy()
df["label"] = df.item_id.map(reference)

print("Accuracy vs. English reference, by language x condition:\n")
result = (
    df.dropna(subset=["label"])
    .groupby(["language", "condition"])
    .apply(lambda x: accuracy_score(x.label, x.prediction))
    .rename("accuracy")
)
print(result)

# Pairwise agreement between conditions within each language -- e.g. does
# P1 (English instruction) agree with P2 (fully localized) on the same
# item more often than either agrees with P3 (explicit reasoning)?
pivot = df.pivot_table(index=["language", "item_id"], columns="condition", values="prediction")
for lang in pivot.index.get_level_values("language").unique():
    sub = pivot.loc[lang].dropna()
    print(f"\n{lang} pairwise condition agreement (n={len(sub)}):")
    for a, b in [("p1", "p2"), ("p2", "p3"), ("p1", "p3")]:
        if a in sub.columns and b in sub.columns:
            agree = (sub[a] == sub[b]).mean()
            print(f"  {a} vs {b}: {agree:.3f}")