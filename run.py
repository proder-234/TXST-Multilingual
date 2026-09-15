import argparse
import csv

from prompt import (
    CONDITIONS,
    LANG_COL,
    LANG_NAME,
    generate_condition_prompt,
    generate_prompt,
)
from models import query_model


def run(input_csv, output_csv, lang, condition):
    text_col = LANG_COL[lang]
    target_language = LANG_NAME[lang]

    with open(input_csv, newline="", encoding="utf-8") as f_in:
        rows = list(csv.DictReader(f_in))

    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=["input_id", "output"])
        writer.writeheader()

        for i, row in enumerate(rows, 1):
            scenario = row[text_col]

            if condition is None:
                # English reference run (or Russian, if you ever add
                # P1/P2/P3 templates for it) -- uses the original
                # single-condition BASE_PROMPT.
                prompt = generate_prompt(scenario, target_language)
            else:
                prompt = generate_condition_prompt(scenario, lang, condition)

            print(f"[{i}/{len(rows)}] generating...", end=" ", flush=True)
            full_response, score, justification = query_model(prompt)

            writer.writerow({
                "input_id": row["input_id"],
                "output": f"input: {scenario}\nresponse: {score}\njustification: {justification}",
            })
            f_out.flush()

            print(f"response={score}" if score is not None else "[!] could not parse a clean 0/1 response")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", default="result/ethics_translated.csv")
    parser.add_argument("--output_csv", default=None)
    parser.add_argument("--lang", default="hi", choices=list(LANG_COL.keys()))
    parser.add_argument(
        "--condition",
        default=None,
        choices=list(CONDITIONS),
        help=(
            "P1/P2/P3 prompt condition. Required when --lang is hi or ne. "
            "Not supported for --lang en (always uses the single reference "
            "prompt) or --lang ru (no P1/P2/P3 templates defined for "
            "Russian yet)."
        ),
    )
    args = parser.parse_args()

    if args.lang in ("hi", "ne") and args.condition is None:
        parser.error("--condition is required when --lang is hi or ne")
    if args.lang in ("en", "ru") and args.condition is not None:
        parser.error(f"--condition is not supported for --lang {args.lang}")

    if args.output_csv is None:
        suffix = f"_{args.condition}" if args.condition else ""
        args.output_csv = f"result/eval_{args.lang}{suffix}.csv"

    run(args.input_csv, args.output_csv, args.lang, args.condition)
    print("Done.")