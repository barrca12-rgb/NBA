"""Live NBA lines from SportsGameOdds (api.sportsgameodds.com/v2), one row per (book, game), with betslip links.

Adapted from barrca12-rgb/CBB cbb/odds.py. Needs SGO_API_KEY (sent as X-Api-Key). Each pull updates
lines/openers.csv (first number seen per game and book, with when it was first seen) and lines/closing.csv (last
pregame number; started games drop out of the feed, so their row stays as the close). The Odds API is not used.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

API = "https://api.sportsgameodds.com/v2/events"
LINES = os.path.join(os.path.dirname(__file__), "..", "lines")
BOOKS = {"fanduel": "FanDuel", "draftkings": "DraftKings", "betmgm": "BetMGM", "caesars": "Caesars",
         "fanatics": "Fanatics", "bet365": "bet365", "espnbet": "theScore Bet"}
ODDS = {"points-home-game-sp-home": ("home_spread", "home_spread_odds", "home_spread_link"),
        "points-away-game-sp-away": (None, "away_spread_odds", "away_spread_link"),
        "points-all-game-ou-over": ("total", "over_odds", "over_link"),
        "points-all-game-ou-under": (None, "under_odds", "under_link"),
        "points-home-game-ml-home": (None, "home_ml", "home_ml_link"),
        "points-away-game-ml-away": (None, "away_ml", "away_ml_link")}
MAX_AGE = pd.Timedelta(hours=12)
BUDGET_STOP = 0.95
COLS = ["book", "sgo_event", "start", "home_id", "away_id", "home_spread", "home_spread_odds", "away_spread_odds",
        "total", "over_odds", "under_odds", "home_ml", "away_ml", "home_spread_link", "away_spread_link",
        "over_link", "under_link", "home_ml_link", "away_ml_link"]


def _num(x):
    try:
        return float(str(x).replace("+", ""))
    except (TypeError, ValueError):
        return np.nan


def norm(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", "", str(s).lower().replace("_nba", "").replace("_", " "))
    return re.sub(r"\s+", " ", s.replace("los angeles clippers", "la clippers")).strip()


def lookup(schedule: pd.DataFrame) -> dict:
    out = {}
    for side in ("home", "away"):
        for col in ("display_name",):
            out.update({norm(n): int(i) for n, i in zip(schedule[f"{side}_{col}"], schedule[f"{side}_id"])})
    return out


def _get(path: str, q: dict | None = None) -> dict:
    url = "https://api.sportsgameodds.com/v2/" + path + ("?" + urllib.parse.urlencode(q) if q else "")
    req = urllib.request.Request(url, headers={"User-Agent": "nba-card", "X-Api-Key": os.environ.get("SGO_API_KEY", "")})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def usage() -> dict:
    try:
        m = _get("account/usage")["data"]["rateLimits"]["per-month"]
        return {"used": int(m["current-entities"]), "max": int(m["max-entities"])}
    except Exception:
        return {}


def fetch(schedule: pd.DataFrame) -> pd.DataFrame:
    """Current pregame lines for every NBA game SGO has odds for. Also returns, per event, the market's opening
    consensus (fetch.opens: sgo_event -> {open_total, open_home_spread})."""
    u = usage()
    fetch.usage = u
    if u and u["used"] >= BUDGET_STOP * u["max"]:
        raise RuntimeError(f"SGO monthly allowance nearly used ({u['used']:,} of {u['max']:,} entities)")
    events, cursor = [], None
    while True:
        q = {"leagueID": "NBA", "oddsAvailable": "true", "limit": 100, "oddID": ",".join(ODDS)}
        if cursor:
            q["cursor"] = cursor
        body = _get("events", q)
        events += body.get("data") or []
        cursor = body.get("nextCursor")
        if not cursor or len(events) > 400:
            break
    lk = lookup(schedule)
    now = pd.Timestamp.now(tz="UTC")
    rows, opens, early = [], {}, []
    for ev in events:
        st = ev.get("status") or {}
        if st.get("started") or st.get("ended") or st.get("cancelled"):
            continue
        tm = ev.get("teams") or {}
        ids = []
        for side in ("home", "away"):
            t = tm.get(side) or {}
            cand = [((t.get("names") or {}).get("long")), t.get("teamID")]
            ids.append(next((lk[norm(c)] for c in cand if c and norm(c) in lk), None))
        h, a = ids
        if h is None or a is None:
            continue
        odds = ev.get("odds") or {}
        ou, sp = odds.get("points-all-game-ou-over") or {}, odds.get("points-home-game-sp-home") or {}
        opens[ev.get("eventID")] = {"open_total": _num(ou.get("openBookOverUnder")),
                                    "open_home_spread": _num(sp.get("openBookSpread"))}
        per_book: dict = {}
        off_board: dict = {}   # posted, then taken down (look-ahead lines days out): shown as early lines only
        for odd_id, (line_col, price_col, link_col) in ODDS.items():
            for bk, o in ((odds.get(odd_id) or {}).get("byBookmaker") or {}).items():
                if o.get("available") is False:
                    if bk in BOOKS:              # only the books we bet
                        r = off_board.setdefault(bk, {"book": BOOKS.get(bk, bk), "sgo_event": ev.get("eventID"),
                                                      "start": st.get("startsAt"), "home_id": h, "away_id": a})
                        r[price_col] = _num(o.get("odds"))
                        if line_col == "home_spread":
                            r["home_spread"] = _num(o.get("spread"))
                        elif line_col == "total":
                            r["total"] = _num(o.get("overUnder"))
                    continue
                if bk not in BOOKS:
                    continue
                upd = pd.to_datetime(o.get("lastUpdatedAt"), utc=True, errors="coerce")
                if pd.notna(upd) and now - upd > MAX_AGE:
                    continue
                r = per_book.setdefault(bk, {"book": BOOKS[bk], "sgo_event": ev.get("eventID"),
                                             "start": st.get("startsAt"), "home_id": h, "away_id": a})
                r[price_col] = _num(o.get("odds"))
                if o.get("deeplink"):
                    r[link_col] = o["deeplink"]
                if line_col == "home_spread":
                    r["home_spread"] = _num(o.get("spread"))
                elif line_col == "total":
                    r["total"] = _num(o.get("overUnder"))
        rows += per_book.values()
        early += [r for bk, r in off_board.items() if bk not in per_book]
    fetch.opens, fetch.events = opens, len(events)
    fetch.early = pd.DataFrame(early).reindex(columns=COLS)
    return pd.DataFrame(rows).reindex(columns=COLS)


def track(cur: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Update lines/openers.csv (first number per event and book) and lines/closing.csv (latest pregame number)."""
    os.makedirs(LINES, exist_ok=True)
    now = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    keep = ["sgo_event", "book", "start", "home_id", "away_id", "home_spread", "total", "home_spread_odds",
            "away_spread_odds", "over_odds", "under_odds"]
    c = cur[keep].assign(seen=now)
    op_path, cl_path = os.path.join(LINES, "openers.csv"), os.path.join(LINES, "closing.csv")
    op = pd.read_csv(op_path) if os.path.exists(op_path) else pd.DataFrame(columns=keep + ["seen"])
    new = c[~(c["sgo_event"] + "|" + c["book"]).isin(set(op["sgo_event"] + "|" + op["book"]))]
    op = pd.concat([op, new], ignore_index=True) if len(new) else op
    op.to_csv(op_path, index=False)
    cl = pd.read_csv(cl_path) if os.path.exists(cl_path) else pd.DataFrame(columns=keep + ["seen"])
    cl = pd.concat([cl[~(cl["sgo_event"] + "|" + cl["book"]).isin(set(c["sgo_event"] + "|" + c["book"]))], c],
                   ignore_index=True)
    cl.to_csv(cl_path, index=False)
    return op, cl
