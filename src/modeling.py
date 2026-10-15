"""Features, time based split, models and metrics for the pre transfer success model.

Label: regular_starter (see sql/01_build_pre_transfer.sql). Features use only data before the move.
Split by transfer date, with an embargo so no training label window reaches into the validation period.
"""
import os

import numpy as np
import pandas as pd
import psycopg
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import SEED

TRAIN_END = "2020-06-30"      # train: moves on or before this date (label windows end by 2022-06-30)
VAL_START, VAL_END = "2022-07-01", "2023-06-30"
TEST_START = "2023-07-01"      # test: 2023-07-01 to 2024-09-30
SOURCE_LEAGUES = ["BE1", "NL1", "PO1", "TR1", "SC1", "DK1", "GR1", "RU1", "UKR1"]
TOP5 = ["GB1", "ES1", "IT1", "L1", "FR1"]

NUM = ["age_at_transfer", "height_cm", "apps_365", "minutes_365", "goals_365", "assists_365", "yellows_365",
       "reds_365", "apps_90", "minutes_90", "apps_prev365", "minutes_prev365", "goals_p90", "assists_p90",
       "log_value", "value_age_days", "value_change_1y", "summer_window"]
CAT = ["position", "sub_position", "foot", "from_league", "to_league"]


def db_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql:///football")


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["age_at_transfer"] = df["age_at_transfer"].astype(float)
    for c in ["height_cm", "value_before", "value_1y_before"]:
        df[c] = df[c].astype(float)
    for c in ["apps_365", "minutes_365", "goals_365", "assists_365", "yellows_365", "reds_365", "apps_90",
              "minutes_90", "apps_prev365", "minutes_prev365", "value_age_days"]:
        df[c] = df[c].fillna(0).astype(float)
    df["summer_window"] = df["summer_window"].astype(float)
    m90 = (df["minutes_365"] / 90).clip(lower=1)
    df["goals_p90"] = df["goals_365"] / m90
    df["assists_p90"] = df["assists_365"] / m90
    df["log_value"] = np.log1p(df["value_before"])
    df["value_change_1y"] = np.where(df["value_1y_before"] > 0, df["value_before"] / df["value_1y_before"], np.nan)
    return df


def load_records() -> pd.DataFrame:
    with psycopg.connect(db_url()) as conn:
        df = pd.read_sql("SELECT * FROM tm.model_records ORDER BY transfer_date, move_id", conn)
    df["transfer_date"] = pd.to_datetime(df["transfer_date"])
    return add_features(df)


def split(df: pd.DataFrame):
    d = df["transfer_date"]
    train = df[d <= TRAIN_END]
    val = df[(d >= VAL_START) & (d <= VAL_END)]
    test = df[d >= TEST_START]
    embargo = df[(d > TRAIN_END) & (d < VAL_START)]
    return train, val, test, embargo


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=5), CAT),
    ])


def best_f1_threshold(y, p) -> float:
    best, thr = -1, 0.5
    for t in np.linspace(0.05, 0.95, 91):
        pred = p >= t
        if pred.sum() == 0:
            continue
        pr, rc = precision_score(y, pred, zero_division=0), recall_score(y, pred, zero_division=0)
        f1 = 0 if pr + rc == 0 else 2 * pr * rc / (pr + rc)
        if f1 > best:
            best, thr = f1, t
    return float(thr)


def metrics(y, p, thr) -> dict:
    pred = p >= thr
    return {"precision": precision_score(y, pred, zero_division=0), "recall": recall_score(y, pred, zero_division=0),
            "roc_auc": roc_auc_score(y, p), "threshold": thr}


def bootstrap_auc_ci(y, p, n=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    y, p = np.asarray(y), np.asarray(p)
    out = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        out.append(roc_auc_score(y[i], p[i]))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def train_mlp(Xtr, ytr, Xva, yva, hidden=(32, 16), dropout=0.3, wd=1e-3, lr=1e-3, epochs=300, patience=25, seed=SEED):
    import torch
    from torch import nn
    torch.manual_seed(seed)
    np.random.seed(seed)
    Xtr_t = torch.tensor(np.asarray(Xtr, dtype="float32"))
    ytr_t = torch.tensor(np.asarray(ytr, dtype="float32")).unsqueeze(1)
    Xva_t = torch.tensor(np.asarray(Xva, dtype="float32"))
    yva_t = torch.tensor(np.asarray(yva, dtype="float32")).unsqueeze(1)
    layers, d = [], Xtr_t.shape[1]
    for h in hidden:
        layers += [nn.Linear(d, h), nn.ReLU(), nn.Dropout(dropout)]
        d = h
    layers.append(nn.Linear(d, 1))
    net = nn.Sequential(*layers)
    opt = torch.optim.Adam(net.parameters(), lr=lr, weight_decay=wd)
    loss_fn = nn.BCEWithLogitsLoss()
    best, best_state, bad = 1e9, None, 0
    g = torch.Generator().manual_seed(seed)
    for ep in range(epochs):
        net.train()
        perm = torch.randperm(len(Xtr_t), generator=g)
        for i in range(0, len(perm), 64):
            idx = perm[i:i + 64]
            opt.zero_grad()
            loss_fn(net(Xtr_t[idx]), ytr_t[idx]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            vl = loss_fn(net(Xva_t), yva_t).item()
        if vl < best - 1e-4:
            best, bad = vl, 0
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict(best_state)
    net.eval()

    def predict(X):
        with torch.no_grad():
            return torch.sigmoid(net(torch.tensor(np.asarray(X, dtype="float32")))).squeeze(1).numpy()
    return net, predict, ep + 1


def fit_all(train: pd.DataFrame, val: pd.DataFrame):
    """Fit baselines, logistic regression, gradient boosting and a PyTorch MLP.
    Hyperparameters are chosen by validation ROC AUC only. The test set is not touched here."""
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression

    ytr, yva = train["regular_starter"].values, val["regular_starter"].values
    out = {}

    # Baseline 1: constant training prior (AUC 0.5 by construction)
    prior = ytr.mean()
    out["baseline_prior"] = {"predict": lambda d, prior=prior: np.full(len(d), prior), "params": {"prior": round(float(prior), 3)}}

    # Baseline 2: one rule, share of the last 365 days minutes played (a scout's first glance)
    out["baseline_minutes"] = {"predict": lambda d: (d["minutes_365"].values / 3400.0).clip(0, 1),
                               "params": {"rule": "minutes_365 / 3400"}}

    # Logistic regression
    best = None
    for C in [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]:
        pipe = Pipeline([("pre", preprocessor()), ("m", LogisticRegression(C=C, max_iter=2000, random_state=SEED))])
        pipe.fit(train, ytr)
        a = roc_auc_score(yva, pipe.predict_proba(val)[:, 1])
        if best is None or a > best[0]:
            best = (a, C, pipe)
    out["logistic_regression"] = {"predict": lambda d, p=best[2]: p.predict_proba(d)[:, 1], "params": {"C": best[1]}, "val_auc": best[0], "pipe": best[2]}

    # Gradient boosting
    best = None
    for lr in [0.03, 0.1]:
        for depth in [2, 3]:
            for n in [100, 250]:
                pipe = Pipeline([("pre", preprocessor()), ("m", GradientBoostingClassifier(
                    learning_rate=lr, max_depth=depth, n_estimators=n, subsample=0.8, random_state=SEED))])
                pipe.fit(train, ytr)
                a = roc_auc_score(yva, pipe.predict_proba(val)[:, 1])
                if best is None or a > best[0]:
                    best = (a, dict(learning_rate=lr, max_depth=depth, n_estimators=n), pipe)
    out["gradient_boosting"] = {"predict": lambda d, p=best[2]: p.predict_proba(d)[:, 1], "params": best[1], "val_auc": best[0], "pipe": best[2]}

    # PyTorch MLP on the same preprocessed features
    pre = preprocessor().fit(train)
    Xtr, Xva = pre.transform(train), pre.transform(val)
    Xtr = Xtr.toarray() if hasattr(Xtr, "toarray") else Xtr
    Xva = Xva.toarray() if hasattr(Xva, "toarray") else Xva
    best = None
    for hidden in [(16,), (32, 16)]:
        for dropout in [0.2, 0.4]:
            for wd in [1e-3, 1e-2]:
                net, pred, ep = train_mlp(Xtr, ytr, Xva, yva, hidden=hidden, dropout=dropout, wd=wd)
                a = roc_auc_score(yva, pred(Xva))
                if best is None or a > best[0]:
                    best = (a, dict(hidden=list(hidden), dropout=dropout, weight_decay=wd, epochs_run=ep), pred)

    def mlp_predict(d, pre=pre, pred=best[2]):
        X = pre.transform(d)
        X = X.toarray() if hasattr(X, "toarray") else X
        return pred(X)
    out["pytorch_mlp"] = {"predict": mlp_predict, "params": best[1], "val_auc": best[0]}
    return out
