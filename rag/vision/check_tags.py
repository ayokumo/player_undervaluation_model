"""Compare the vision model's tags with the rule based tags from the event data.

Writes results/vision/tag_agreement.md. Run: python -m rag.vision.check_tags
"""
import json

import pandas as pd

from rag.vision.common import ROOT

PAIRS = [("passing_territory", "tag_passing_territory"), ("pass_direction", "tag_pass_direction"),
         ("pass_length", "tag_pass_length"), ("carrying", "tag_carrying"), ("shooting", "tag_shooting")]


def main() -> None:
    desc = pd.DataFrame([json.loads(l) for l in (ROOT / "results/vision/descriptions.jsonl").read_text().splitlines() if l.strip()])
    summ = pd.read_csv(ROOT / "results/vision/action_summary.csv")
    df = desc.merge(summ, on=["tm_player_id", "season", "competition"])
    lines = ["# Vision tag check", "", f"Images: {len(df)}. Model: {desc.model.iloc[0]}. Date: {desc.date.iloc[0]}.", "",
             "Each tag from the vision model is compared with the rule based tag computed from the StatsBomb event data (thresholds fixed before any comparison, in `rag/vision/summarise.py`).", "",
             "| Tag | Agreement | Always predicting the most common data tag |", "|---|---|---|"]
    for v, d in PAIRS:
        agree = (df[v] == df[d]).mean()
        base = df[d].value_counts(normalize=True).iloc[0]
        lines.append(f"| {v} | {agree:.0%} | {base:.0%} |")
    lines += ["", "## Confusion (rows: data tag, columns: vision tag)"]
    for v, d in PAIRS:
        lines += ["", f"### {v}", "", pd.crosstab(df[d], df[v]).to_markdown()]
    (ROOT / "results/vision/tag_agreement.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
