"""Ask a vision capable model (Claude) to describe each action map image and tag it.

The model sees only the image (the title names the player and tournament). It is told to describe what is visible
and to choose tags from fixed lists. Tags are later checked against the rule based tags from the event data
(rag/vision/summarise.py). Output: results/vision/descriptions.jsonl
Run: python -m rag.vision.describe          (needs ANTHROPIC_API_KEY)
"""
import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from rag.vision.common import ROOT

load_dotenv()
OUT = ROOT / "results" / "vision" / "descriptions.jsonl"

PROMPT = """You are looking at three football pitch maps for one player across a few international matches.
Left panel: passes (green completed, red incomplete). Middle: carries (the player running with the ball). Right: shots
(circle size is shot quality, a star is a goal). The player's team attacks left to right, so the right side is the
opponent's goal. The title gives the player and the tournament.

Describe only what you can see. Do not guess the player's role, quality, or anything not drawn. Write 2 or 3 plain
sentences about where the passes start and go, how long they are, where the carries happen, and the shots if any.
Then choose one tag for each field:
- passing_territory: mostly_own_half (most passes start in the left half), mostly_final_third (many passes start in
  the right third of the pitch), or balanced.
- pass_direction: mostly_forward (most arrows point to the right), mostly_sideways_or_back (few point right), or mixed.
- pass_length: short (mostly short arrows), long (many long arrows across much of the pitch), or medium.
- carrying: carries_into_final_third (several carries start before and end inside the right third), or
  few_carries_into_final_third.
- shooting: shots_from_close (shots mostly inside or near the box), shots_from_range (mostly far from goal),
  shots_mixed, or too_few_shots (fewer than 2 shots)."""


class Tags(BaseModel):
    description: str = Field(description="2 or 3 plain sentences about what is visible")
    passing_territory: Literal["mostly_own_half", "mostly_final_third", "balanced"]
    pass_direction: Literal["mostly_forward", "mostly_sideways_or_back", "mixed"]
    pass_length: Literal["short", "medium", "long"]
    carrying: Literal["carries_into_final_third", "few_carries_into_final_third"]
    shooting: Literal["shots_from_close", "shots_mixed", "shots_from_range", "too_few_shots"]


def describe_one(llm, path) -> dict:
    b64 = base64.b64encode(path.read_bytes()).decode()
    msg = HumanMessage(content=[{"type": "text", "text": PROMPT}, {"type": "image", "base64": b64, "mime_type": "image/png"}])
    return llm.invoke([msg]).model_dump()


def main(limit: int | None = None) -> None:
    model = os.environ.get("VISION_MODEL", os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    llm = ChatAnthropic(model=model, max_tokens=600).with_structured_output(Tags)
    summ = pd.read_csv(ROOT / "results" / "vision" / "action_summary.csv")
    todo = summ[summ.eligible_for_image]
    done = set()
    if OUT.exists():
        done = {(json.loads(l)["tm_player_id"], json.loads(l)["season"]) for l in OUT.read_text().splitlines() if l.strip()}
    jobs = [r for _, r in todo.iterrows() if (int(r.tm_player_id), r.season) not in done][:limit]

    def run(r):
        path = ROOT / "figures" / "vision" / f"{r.tm_player_id}_{str(r.season).replace('/', '-')}.png"
        try:
            t = describe_one(llm, path)
        except Exception as e:  # keep going, retry later by rerunning
            return {"error": str(e)[:200], "tm_player_id": int(r.tm_player_id), "season": r.season}
        return {"tm_player_id": int(r.tm_player_id), "season": r.season, "competition": r.competition, "model": model, "date": date.today().isoformat(), **t}

    with OUT.open("a") as f, ThreadPoolExecutor(4) as ex:
        for res in ex.map(run, jobs):
            if "error" not in res:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            else:
                print("error", res)
    print(f"described {len(jobs)} images -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
