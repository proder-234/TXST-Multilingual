import re
import pandas as pd

def load(path, language):
    df = pd.read_csv(path)

    df["response"] = df["output"].str.extract(
        r"response:\s*([01])", expand=False
    )

    df["justification"] = df["output"].str.extract(
        r"justification:\s*(.*)", expand=False, flags=re.DOTALL
    )

    return df.dropna(subset=["response"]).assign(
        language=language,
        item_id=df["input_id"],
        input=df["output"].str.extract(r"input:\s*(.*?)(?=\nresponse:)", flags=re.DOTALL)[0]
    )[["language", "item_id", "input", "response", "justification"]]


files = [
    ("result/eval_en.csv", "English"),
    ("result/eval_hi.csv", "Hindi"),
    ("result/eval_ne.csv", "Nepali"),
]

df = pd.concat([load(path, lang) for path, lang in files])

english = df[df.language == "English"].set_index("item_id")

for language in ["Hindi", "Nepali"]:
    lang = df[df.language == language].set_index("item_id")

    result = lang.join(
        english,
        lsuffix="_lang",
        rsuffix="_en",
        how="inner"
    )

    result = result[
        result.response_lang != result.response_en
    ][[
        "input_en",
        "response_en",
        "justification_en",
        "response_lang",
        "justification_lang"
    ]]

    result = result.reset_index()

    result.to_csv(
        f"result/mismatch_{language.lower()[:2]}.csv",
        index=False
    )

    print(f"{language}: {len(result)} mismatches")