import argparse
import csv
import os

from prompts.base_prompt import generate_prompt as base_generate_prompt
from prompts.lang_prompt import (
    LANG_COL,
    LANG_NAME,
    generate_prompt as lang_generate_prompt,
)
from models.models import AVAILABLE_MODELS, get_query_model

PROMPT_TYPES = ["base", "lang"]


def build_prompt(prompt_type, scenario, lang_code):
    """prompt_type 'base' -> prompts/base_prompt.py, 'lang' -> prompts/lang_prompt.py."""
    if prompt_type == "lang":
        return lang_generate_prompt(scenario, lang_code)
    target_language = LANG_NAME.get(lang_code, lang_code)
    return base_generate_prompt(scenario, target_language)


def ask(question, choices):
    choices_str = "/".join(choices)
    while True:
        answer = input(f"{question} [{choices_str}]: ").strip().lower()
        if answer in choices:
            return answer
        print(f"Please choose one of: {choices_str}")


def run(input_csv, output_csv, lang, model_name, prompt_type):
    text_col = LANG_COL[lang]
    query_model = get_query_model(model_name)

    with open(input_csv, newline="", encoding="utf-8") as f_in:
        rows = list(csv.DictReader(f_in))

    out_dir = os.path.dirname(output_csv)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=["input_id", "output"])
        writer.writeheader()

        for i, row in enumerate(rows, 1):
            scenario = row[text_col]
            prompt = build_prompt(prompt_type, scenario, lang)

            print(f"[{i}/{len(rows)}] generating...", end=" ", flush=True)
            full_response, score, justification = query_model(prompt)

            writer.writerow({
                "input_id": row["input_id"],
                "output": f"input: {scenario}\nresponse: {score}\njustification: {justification}",
            })
            f_out.flush()

            print(f"response={score}" if score is not None else "[!] could not parse a clean 0/1 response")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run inference over translated scenarios with a chosen model and prompt style."
    )
    parser.add_argument("--input_csv", default="results/ethics_translated.csv")
    parser.add_argument("--output_csv", default=None, help="Defaults to results/eval_<lang>_<model>.csv")
    parser.add_argument("--lang", choices=list(LANG_COL.keys()), default=None)
    parser.add_argument("--model", choices=AVAILABLE_MODELS, default=None)
    parser.add_argument(
        "--prompt",
        choices=PROMPT_TYPES,
        default=None,
        help="'base' = prompts/base_prompt.py, 'lang' = prompts/lang_prompt.py (fully localized instructions)",
    )
    args = parser.parse_args()

    lang = args.lang or ask("Which language do you want to run inference on?", list(LANG_COL.keys()))
    model_name = args.model or ask("Which model do you want to use?", AVAILABLE_MODELS)
    prompt_type = args.prompt or ask("Which prompt style do you want to use?", PROMPT_TYPES)

    output_csv = args.output_csv or f"results/eval_{lang}_{model_name}.csv"

    run(args.input_csv, output_csv, lang, model_name, prompt_type)
    print("Done.")
