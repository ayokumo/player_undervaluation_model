"""Render one image per eligible player: passes, carries and shots (mplsoccer, StatsBomb pitch).

Panels: passes (green complete, red incomplete), carries (blue), shots (circle size is xG, star is a goal).
The attacking direction is left to right. Output: figures/vision/<tm_player_id>_<season>.png
Run: python -m rag.vision.render
"""
import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch

from rag.vision.common import INTERIM, ROOT

OUT = ROOT / "figures" / "vision"


def render(a: pd.DataFrame, title: str, path) -> None:
    pitch = Pitch(pitch_type="statsbomb", line_color="#555555", pitch_color="white", linewidth=0.8)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.6))
    p, c, s = a[a.type == "Pass"], a[a.type == "Carry"], a[a.type == "Shot"]
    for ax, name in zip(axes, ["Passes", "Carries", "Shots"]):
        pitch.draw(ax=ax)
        ax.set_title(name, fontsize=9)
    ok, bad = p[p.outcome == "Complete"], p[p.outcome != "Complete"]
    pitch.arrows(ok.x, ok.y, ok.end_x, ok.end_y, ax=axes[0], color="#2a9d3a", width=1, headwidth=4, headlength=4, alpha=0.6)
    pitch.arrows(bad.x, bad.y, bad.end_x, bad.end_y, ax=axes[0], color="#d62828", width=1, headwidth=4, headlength=4, alpha=0.6)
    if len(c):
        pitch.arrows(c.x, c.y, c.end_x, c.end_y, ax=axes[1], color="#1d4e89", width=1, headwidth=4, headlength=4, alpha=0.55)
    for _, r in s.iterrows():
        pitch.scatter(r.x, r.y, ax=axes[2], s=max(r.xg * 900, 30), color="#f4a300" if not r.is_goal else "#d62828",
                      marker="*" if r.is_goal else "o", edgecolors="black", linewidth=0.6, alpha=0.85, zorder=3)
    axes[0].text(1, -3, f"{len(ok)} complete, {len(bad)} incomplete", fontsize=7)
    axes[1].text(1, -3, f"{len(c)} carries", fontsize=7)
    axes[2].text(1, -3, f"{len(s)} shots, {int(s.is_goal.sum())} goals", fontsize=7)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=70)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    acts = pd.read_csv(INTERIM / "sb_actions.csv")
    links = {(l["sb_player_id"], l["competition"], l["season"]): l for l in csv.DictReader(open(ROOT / "results" / "vision" / "player_links.csv"))}
    summ = pd.read_csv(ROOT / "results" / "vision" / "action_summary.csv")
    n = 0
    for _, r in summ[summ.eligible_for_image].iterrows():
        l = links[(str(r.sb_player_id), r.competition, r.season)]
        ids = {int(m) for m in l["match_ids"].split()}
        a = acts[(acts.sb_player_id == int(r.sb_player_id)) & acts.match_id.isin(ids)]
        fname = str(r.season).replace("/", "-")
        render(a, f"{r.tm_name} | {r.competition} | {r.n_matches} matches | attacking left to right", OUT / f"{r.tm_player_id}_{fname}.png")
        n += 1
    print(f"rendered {n} images into {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
