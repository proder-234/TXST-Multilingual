import argparse
import csv
import traceback

from prompt import LANG_COL, generate_prompt
from models import query_model

MAX_NEW_TOKENS = {"en": 220, "hi": 400, "ne": 400}


def run(input_csv, output_csv, lang):
    text_col = LANG_COL[lang]
    max_new_tokens = MAX_NEW_TOKENS.get(lang, 220)

    with open(input_csv, newline="", encoding="utf-8") as f_in:
        rows = list(csv.DictReader(f_in))

    unparsed = 0
    errors = 0

    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=["input_id", "output"])
        writer.writeheader()

        for i, row in enumerate(rows, 1):
            scenario = row[text_col]
            prompt = generate_prompt(scenario, lang)

            print(f"[{i}/{len(rows)}] generating...", end=" ", flush=True)

            try:
                full_response, score, justification = query_model(
                    prompt, max_new_tokens=max_new_tokens
                )
            except Exception as e:
                errors += 1
                print(f"[!] query_model raised an exception: {e!r}")
                traceback.print_exc()
                # placeholder row so the CSV stays aligned, then keep going
                writer.writerow({
                    "input_id": row["input_id"],
                    "output": f"input: {scenario}\nresponse: ERROR\njustification: {e!r}",
                })
                f_out.flush()
                continue

            # query_model catches generate() errors and returns them as text
            if full_response.startswith("Error:"):
                errors += 1
                print(f"[!] {full_response}")
                writer.writerow({
                    "input_id": row["input_id"],
                    "output": f"input: {scenario}\nresponse: ERROR\njustification: {full_response}",
                })
                f_out.flush()
                continue

            writer.writerow({
                "input_id": row["input_id"],
                "output": f"input: {scenario}\nresponse: {score}\njustification: {justification}",
            })
            f_out.flush()

            if score is not None:
                print(f"response={score}")
            else:
                unparsed += 1
                print("[!] could not parse -- raw response was:")
                print(f"    {full_response!r}")

    print(f"Total: {len(rows)} | Errors: {errors} | Unparsed: {unparsed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", default="result/ethics_translated.csv")
    parser.add_argument("--output_csv", default=None)
    parser.add_argument("--lang", default="hi", choices=list(LANG_COL.keys()))
    args = parser.parse_args()

    if args.output_csv is None:
        args.output_csv = f"result/eval_{args.lang}.csv"

    run(args.input_csv, args.output_csv, args.lang)
    print("Done.")

    #caffeinate -i python3 inference.py --lang en