import numpy as np
import pandas as pd
import joblib
import os

BASE = os.path.dirname(__file__)
MOD  = os.path.join(BASE, "models")

# ── Load all artifacts once at startup ──
model        = joblib.load(os.path.join(MOD, "model_calibrated_final.pkl"))
imputer      = joblib.load(os.path.join(MOD, "imputer.pkl"))
scaler       = joblib.load(os.path.join(MOD, "scaler.pkl"))
feature_cols = joblib.load(os.path.join(MOD, "feature_cols.pkl"))
team_stats   = joblib.load(os.path.join(MOD, "team_stats_lookup.pkl"))
h2h_df       = pd.read_csv(os.path.join(MOD, "h2h_history.csv"), parse_dates=["Date"])

# ── Fix sklearn version mismatch (1.6.x → 1.7+) ──────────────
# SimpleImputer renamed _fill_dtype to _fit_dtype in sklearn 1.7.
# Patch it here right after loading so transform() works on any version.
import warnings
for _obj in (imputer, scaler):
    if not hasattr(_obj, "_fill_dtype") and hasattr(_obj, "_fit_dtype"):
        _obj._fill_dtype = _obj._fit_dtype

LABELS = {0: "Home Win", 1: "Draw", 2: "Away Win"}


def _get_rolls(team: str) -> dict:
    """Latest rolling stats for a team, keyed as roll_*"""
    if team not in team_stats:
        return {}
    return {k: v for k, v in team_stats[team].items() if k.startswith("roll_")}


def _get_h2h(home: str, away: str, n: int = 5) -> list:
    mask = (
        ((h2h_df.HomeTeam == home) & (h2h_df.AwayTeam == away)) |
        ((h2h_df.HomeTeam == away) & (h2h_df.AwayTeam == home))
    )
    past = h2h_df[mask].sort_values("Date").tail(n)
    records = []
    for _, r in past.iterrows():
        if r.HomeTeam == home:
            outcome = "Win" if r.Result == 0 else ("Draw" if r.Result == 1 else "Loss")
            score   = f"{int(r.FTHG)}–{int(r.FTAG)}"
        else:
            outcome = "Win" if r.Result == 2 else ("Draw" if r.Result == 1 else "Loss")
            score   = f"{int(r.FTAG)}–{int(r.FTHG)}"
        records.append({
            "date":    r.Date.strftime("%d %b %Y"),
            "home":    r.HomeTeam,
            "away":    r.AwayTeam,
            "score":   score,
            "outcome": outcome,
            "league":  r.get("League", "—"),
        })
    return records


def _form_string(team: str) -> list:
    """Last 5 results for a team as W/D/L list"""
    mask_h = h2h_df.HomeTeam == team
    mask_a = h2h_df.AwayTeam == team
    home_r = h2h_df[mask_h].tail(5)[["Date", "Result"]].copy()
    away_r = h2h_df[mask_a].tail(5)[["Date", "Result"]].copy()
    home_r["pts"] = home_r.Result.map({0: 3, 1: 1, 2: 0})
    away_r["pts"] = away_r.Result.map({2: 3, 1: 1, 0: 0})
    combined = pd.concat([
        home_r[["Date", "pts"]],
        away_r[["Date", "pts"]]
    ]).sort_values("Date").tail(5)
    return ["W" if p == 3 else ("D" if p == 1 else "L") for p in combined.pts]


def predict(home_team: str, away_team: str) -> dict:
    h = _get_rolls(home_team)
    a = _get_rolls(away_team)

    # Build feature row
    row = {}
    for col in feature_cols:
        if col.startswith("H_roll_"):
            key = col.replace("H_roll_", "roll_")
            row[col] = h.get(key, np.nan)
        elif col.startswith("A_roll_"):
            key = col.replace("A_roll_", "roll_")
            row[col] = a.get(key, np.nan)
        elif col.startswith("diff_"):
            stat = col.replace("diff_", "")
            hv = h.get(f"roll_{stat}", np.nan)
            av = a.get(f"roll_{stat}", np.nan)
            row[col] = hv - av if not (np.isnan(hv) or np.isnan(av)) else np.nan
        elif col == "H2H_home_winrate":
            past = _get_h2h(home_team, away_team)
            wins = sum(1 for p in past if p["outcome"] == "Win")
            row[col] = wins / len(past) if past else 0.5
        elif col == "H2H_draw_rate":
            past = _get_h2h(home_team, away_team)
            draws = sum(1 for p in past if p["outcome"] == "Draw")
            row[col] = draws / len(past) if past else 0.25
        elif col == "H2H_n_matches":
            row[col] = len(_get_h2h(home_team, away_team))
        elif col in ("Prob_H", "Prob_D", "Prob_A", "home_advantage"):
            row[col] = {"Prob_H": 0.45, "Prob_D": 0.27,
                        "Prob_A": 0.28, "home_advantage": 1}.get(col, 0.0)
        else:
            row[col] = np.nan

    X     = pd.DataFrame([row])[feature_cols]
    X_imp = pd.DataFrame(imputer.transform(X), columns=feature_cols)

    # Try raw first (tree models), fall back to scaled
    try:
        proba = model.predict_proba(X_imp)[0]
    except Exception:
        proba = model.predict_proba(scaler.transform(X_imp))[0]

    pred_idx = int(np.argmax(proba))

    # Stats for display
    STAT_KEYS = ["roll_GF", "roll_GA", "roll_Points", "roll_Win", "roll_ShotsOnTarget"]
    STAT_LABELS = {
        "roll_GF":            "Goals Scored",
        "roll_GA":            "Goals Conceded",
        "roll_Points":        "Points / Game",
        "roll_Win":           "Win Rate",
        "roll_ShotsOnTarget": "Shots on Target",
    }
    home_stats = {
        STAT_LABELS[k]: round(float(h[k]), 2)
        for k in STAT_KEYS if k in h and not np.isnan(h[k])
    }
    away_stats = {
        STAT_LABELS[k]: round(float(a[k]), 2)
        for k in STAT_KEYS if k in a and not np.isnan(a[k])
    }

    return {
        "home_team":  home_team,
        "away_team":  away_team,
        "prediction": LABELS[pred_idx],
        "prob_home":  round(float(proba[0]) * 100, 1),
        "prob_draw":  round(float(proba[1]) * 100, 1),
        "prob_away":  round(float(proba[2]) * 100, 1),
        "confidence": round(float(max(proba)) * 100, 1),
        "home_form":  _form_string(home_team),
        "away_form":  _form_string(away_team),
        "home_stats": home_stats,
        "away_stats": away_stats,
        "h2h":        _get_h2h(home_team, away_team),
    }