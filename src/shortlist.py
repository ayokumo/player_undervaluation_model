"""Top 100 shortlist per source league.

Rule (fixed before looking at any output):
  1. Eligible: currently at a club in the league, at least 450 league and cup minutes in the 365 days
     before the snapshot (2026-07-06), a market value on record, and age 30 or under (the 95th percentile
     age of the real movers in the training data; the first version had no age rule and listed mostly
     33 to 38 year olds, see docs/decision_log.md).
  2. p = predicted probability of becoming a regular starter within two seasons after a move, averaged over
     the five top league destinations (the model needs a destination, the scout does not know it yet).
     The model is the one with the best validation ROC AUC (see notebooks/02_models.ipynb).
  3. score = percentile rank of p within the league minus percentile rank of market value within the league.
  4. Output the 100 players with the highest score. Ties go to the higher p.

Run:  python -m src.shortlist           (all nine leagues)
      python -m src.shortlist --league BE1
"""
import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg

from src.config import ROOT
from src.modeling import SOURCE_LEAGUES, TOP5, add_features, db_url, fit_all, load_records, split

MIN_MINUTES = 450
MAX_AGE = 30.0
TOP_N = 100
OUT_DIR = ROOT / "results" / "shortlists"


def main() -> None:
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", choices=SOURCE_LEAGUES)
    args = ap.parse_args()

    train, val, _test, _ = split(load_records())
    models = fit_all(train, val)
    name = max((k for k in models if "val_auc" in models[k]), key=lambda k: models[k]["val_auc"])
    print(f"model: {name}, validation ROC AUC {models[name]['val_auc']:.3f}")

    with psycopg.connect(db_url()) as conn:
        cur = conn.execute("SELECT * FROM tm.shortlist_features")
        cols = [c.name for c in cur.description]
        feats = pd.DataFrame(cur.fetchall(), columns=cols)
    feats["transfer_date"] = pd.to_datetime(feats["transfer_date"])
    feats = add_features(feats)
    feats = feats[(feats["minutes_365"] >= MIN_MINUTES) & feats["value_before"].notna() & (feats["age_at_transfer"] <= MAX_AGE)].copy()

    ps = []
    for dest in TOP5:
        d = feats.copy()
        d["to_league"] = dest
        ps.append(models[name]["predict"](d))
    feats["p_success"] = np.mean(ps, axis=0)

    leagues = [args.league] if args.league else SOURCE_LEAGUES
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for lg in leagues:
        g = feats[feats["from_league"] == lg].copy()
        g["p_pct"] = g["p_success"].rank(pct=True)
        g["value_pct"] = g["value_before"].rank(pct=True)
        g["score"] = g["p_pct"] - g["value_pct"]
        g = g.sort_values(["score", "p_success"], ascending=False).head(TOP_N).reset_index(drop=True)
        g.insert(0, "rank", g.index + 1)
        out = g[["rank", "player_name", "club_name", "position", "age_at_transfer", "minutes_365", "value_before",
                 "p_success", "score"]].rename(columns={"age_at_transfer": "age", "value_before": "market_value_eur"})
        out["age"] = out["age"].round(1)
        out["p_success"] = out["p_success"].round(3)
        out["score"] = out["score"].round(3)
        out["market_value_eur"] = out["market_value_eur"].astype(int)
        path = OUT_DIR / f"shortlist_{lg}.csv"
        out.to_csv(path, index=False)
        print(f"{lg}: {len(feats[feats['from_league'] == lg])} eligible players, wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
