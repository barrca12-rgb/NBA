"""Historical NBA opening and closing spreads and totals from ESPN's stored odds (free), per game and book.

Adapted from barrca12-rgb/CBB cbb/lines_hist.py and audit/b8_open_meta.py, NBA league path. One request per game
returns every book ESPN tracked, each with its opening and closing spread, total and moneylines. No Odds API.

    python -m nba.lines --start 2014 --end 2026      # writes data/lines/espn_<season>.csv (resumable)

Columns (sportsbook convention: home_spread -3 = home favored by 3):
  close: home_spread, total, home_ml, away_ml       open: open_home_spread, open_total, open_home_ml, open_away_ml
  rec_home_id, rec_away_id, details: the odds record's own teams and summary text, to catch reversed records
Games with no line get one row with an empty book so reruns skip them; failed fetches are retried on rerun.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from . import data

URL = ("https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/"
       "events/{0}/competitions/{0}/odds?limit=100")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "lines")
# Projection services / aggregates that ESPN lists like books (CBB list); never used as a market line.
NOT_BOOKS = {"consensus", "numberfire", "teamrankings", "accuscore", "Fantasy911.com", "betegy",
             "Sportradar Internal Odds(ISE)", "unknown"}
COLS = ["game_id", "book", "home_spread", "total", "home_ml", "away_ml",
        "open_home_spread", "open_total", "open_home_ml", "open_away_ml", "rec_home_id", "rec_away_id", "details"]


def _num(x):
    try:
        return float(str(x).replace("+", ""))
    except (TypeError, ValueError):
        return np.nan


def _am(d: dict, *keys):
    for k in keys:
        d = (d or {}).get(k) or {}
    return _num(d.get("american") if isinstance(d, dict) else None)


def _team(side: dict):
    ref = ((side or {}).get("team") or {}).get("$ref", "")
    try:
        return int(ref.split("/teams/")[1].split("?")[0])
    except (IndexError, ValueError):
        return np.nan


def game_lines(game_id: int) -> list[dict]:
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL.format(game_id), headers={"User-Agent": "nba-feasibility"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            break
        except Exception:
            if attempt == 3:
                return [{"game_id": game_id, "book": "fetch failed"}]
            time.sleep(2 ** attempt)
    rows = []
    for p in d.get("items") or []:
        book = (p.get("provider") or {}).get("name", "")
        if "live" in book.lower():
            continue
        h, a = p.get("homeTeamOdds") or {}, p.get("awayTeamOdds") or {}
        cs, ct = _am(h, "close", "pointSpread"), _am(p, "close", "total")
        r = {"game_id": game_id, "book": book,
             "home_spread": cs if cs == cs else _num(p.get("spread")),
             "total": ct if ct == ct else _num(p.get("overUnder")),
             "home_ml": _num(h.get("moneyLine")), "away_ml": _num(a.get("moneyLine")),
             "open_home_spread": _am(h, "open", "pointSpread"), "open_total": _am(p, "open", "total"),
             "open_home_ml": _am(h, "open", "moneyLine"), "open_away_ml": _am(a, "open", "moneyLine"),
             # the record's own home/away team ids and text ("LAL -1.5"): the check for home/away reversed vs the game
             "rec_home_id": _team(h), "rec_away_id": _team(a), "details": p.get("details")}
        if any(r[c] == r[c] for c in ("home_spread", "total", "open_home_spread", "open_total")):
            rows.append(r)
    return rows or [{"game_id": game_id, "book": ""}]


def season_lines(season: int, workers: int = 12) -> pd.DataFrame:
    path = os.path.join(OUT, f"espn_{season}.csv")
    done = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=COLS)
    done = done[done["book"].fillna("") != "fetch failed"]
    g, _ = data.season_games(season)
    todo = sorted(set(g["game_id"]) - set(done["game_id"]))
    if todo:
        with ThreadPoolExecutor(workers) as ex:
            new = [r for rows in ex.map(game_lines, todo) for r in rows]
        done = pd.concat([done, pd.DataFrame(new, columns=COLS)], ignore_index=True)
        os.makedirs(OUT, exist_ok=True)
        done.sort_values(["game_id", "book"]).to_csv(path, index=False)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2014)
    ap.add_argument("--end", type=int, default=2026)
    a = ap.parse_args()
    for s in range(a.start, a.end + 1):
        l = season_lines(s)
        print(s, len(l), l["game_id"].nunique(), (l["book"] == "fetch failed").sum(), flush=True)


if __name__ == "__main__":
    main()


def orient_openers(l: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """CBB "flip" rule: each book's opening spread is checked against the opening moneylines stored with it, never
    against the close. The opening favorite is the side with the shorter moneyline; an opener favoring the other
    team by more than 1 point has its sign corrected. Unchecked openers (no or equal moneylines, |spread| <= 1)
    are kept."""
    l = l.copy()
    o, hml, aml = l["open_home_spread"], l["open_home_ml"].replace(0, np.nan), l["open_away_ml"].replace(0, np.nan)
    imp = lambda x: np.where(x < 0, -x / (100 - np.minimum(x, 0)), 100 / (np.maximum(x, 0) + 100))
    fav = np.sign(imp(hml.to_numpy(float)) - imp(aml.to_numpy(float)))
    has = o.notna().to_numpy()
    checkable = has & ~np.isnan(fav) & (fav != 0) & (o.abs() > 1).to_numpy()
    wrong = checkable & (-np.sign(o.to_numpy()) != fav)
    l.loc[wrong, "open_home_spread"] = -l.loc[wrong, "open_home_spread"]
    return l, {"openers": int(has.sum()), "checked": int(checkable.sum()), "mis-oriented": int(wrong.sum())}


def reversed_records(l: pd.DataFrame, games: pd.DataFrame) -> pd.Series:
    """Per (game, book) row: True when the odds record's own home team is the game's away team (home and away
    reversed against the game). Uses only the record's team ids, never a price or result."""
    m = l[["game_id"]].merge(games[["game_id", "home_id", "away_id"]], on="game_id", how="left")
    return pd.Series((l["rec_home_id"].to_numpy() == m["away_id"].to_numpy()) &
                     (l["rec_away_id"].to_numpy() == m["home_id"].to_numpy()), index=l.index)


def consensus(l: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One opening and one closing spread and total per game: the median across real sportsbooks. Reversed records
    are dropped (not flipped), openers oriented by their own moneylines, books more than 5 points off the median
    spread dropped (CBB rule), plausibility: |spread| <= 30, totals 150-300."""
    l = l[~l["book"].fillna("").isin(NOT_BOOKS | {"", "fetch failed"})].copy()
    # ESPN's "Opening" pseudo-book (2014-2018, as in CBB): its spread, total and moneylines are the opener.
    op = l["book"] == "Opening"
    for c in ("home_spread", "total", "home_ml", "away_ml"):
        oc = "open_" + c
        l.loc[op, oc] = l.loc[op, c]
        l.loc[op, c] = np.nan
    l = l[~reversed_records(l, games)]
    # A closing spread whose sign contradicts the record's own text ("OKC -1" with home_spread +1, home = ATL) by
    # more than a point is dropped (2023-24: mostly ESPN BET rows with prices in the spread field).
    m = l[["game_id"]].merge(games[["game_id", "home", "away"]], on="game_id", how="left")
    fav = l["details"].fillna("").str.extract(r"^([A-Z]+) -")[0].to_numpy()
    sp = l["home_spread"].to_numpy(float)
    bad = (((fav == m["home"].to_numpy()) & (sp > 1)) | ((fav == m["away"].to_numpy()) & (sp < -1)))
    l.loc[bad, "home_spread"] = np.nan
    l, consensus.counts = orient_openers(l)
    for c in ("home_spread", "open_home_spread"):
        l.loc[l[c].abs() > 30, c] = np.nan
    for c in ("total", "open_total"):
        l.loc[~l[c].between(150, 300), c] = np.nan
    for c in ("home_spread", "open_home_spread"):
        med = l.groupby("game_id")[c].transform("median")
        l.loc[(l[c] - med).abs() > 5, c] = np.nan
    return l.groupby("game_id").agg(
        home_spread=("home_spread", "median"), total=("total", "median"),
        open_home_spread=("open_home_spread", "median"), open_total=("open_total", "median"),
        books=("book", "nunique"), open_books=("open_home_spread", "count")).reset_index()
