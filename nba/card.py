"""One day's NBA card: projections (live.py) joined to SportsGameOdds lines (odds.py), best number per side across
books, plays and leans, and the plays log (record.py).

Rules (from the backtest, research/LOG.md): totals edge 4+ points vs the best available number = BET (1 unit,
price -130 or better); 3-4 = WATCH. Spreads edge 3+ = LEAN, tracked but not bet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import record

TOTAL_EDGE, TOTAL_WATCH, SPREAD_EDGE, MIN_PRICE = 4.0, 3.0, 3.0, -130
# At most this many totals plays per side (over / under) per day, from Oct 27, 2026 (Chad): plays on one side share
# one risk (the season's scoring level). Plays already logged that day count first; new ones fill open slots by
# edge; the rest show as CAPPED and are not logged.
MAX_PER_SIDE = 3
# From Oct 28, 2026 (Chad, research/LOG.md entry 19): a totals play also needs REL_EDGE+ after removing the market-wide
# gap (median model total minus opener over the last 60 games), so a disagreement about the whole league's scoring
# level cannot by itself make every game a play. Backtest 2024-2026: 59.3% on 968 plays vs 59.4% on 1,120.
REL_EDGE = 3.0
# backtest win rate at the opener by edge (phase 4 spec, 2024-2026; 6+ shrunk toward the 4+ rate)
def total_p(e): return 0.557 if e < 6 else 0.60
SPREAD_P = 0.545


def _payout(o):
    return np.nan if o is None or pd.isna(o) else (o / 100 if o > 0 else 100 / -o)


def best(lines: pd.DataFrame, col: str, price: str, higher: bool):
    """Best number for one side across books (most favorable line, then best price)."""
    d = lines.dropna(subset=[col])
    if not len(d):
        return None
    d = d.assign(_k=d[col] * (1 if higher else -1), _p=d[price].map(_payout).fillna(-1))
    r = d.sort_values(["_k", "_p"], ascending=False).iloc[0]
    link = r.get(price.replace("_odds", "_link"))
    return {"book": r["book"], "line": float(r[col]), "odds": None if pd.isna(r[price]) else float(r[price]),
            "link": link if isinstance(link, str) else None}


def build(proj: pd.DataFrame, lines: pd.DataFrame, opens: dict, openers: pd.DataFrame, day: pd.Timestamp,
          live: bool = True, early: bool = False, gap: float = 0.0) -> tuple[list[dict], list[dict]]:
    """early: the day's lines are look-ahead numbers the books have taken down; edges are shown, nothing is logged."""
    live = live and not early
    games, plays = [], []
    now = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    ln = lines.copy()
    if len(ln):
        ln["et"] = pd.to_datetime(ln["start"], utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    for _, g in proj.iterrows():
        row = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in g.items()
               if k in ("game_id", "start", "home", "away", "home_id", "away_id", "home_name", "away_name", "neutral", "model_margin",
                        "model_total", "model_home_pts", "model_away_pts", "model_home_spread", "p_home_win",
                        "home_rest", "away_rest", "home_avail_net", "away_avail_net", "home_usual_net", "away_usual_net",
                        "early_w")}
        row["start"] = str(g["start"])
        row["early"] = early
        row["home_id"], row["away_id"] = int(g["home_id"]), int(g["away_id"])
        L = ln[(ln.get("et") == f"{day:%Y-%m-%d}") & (ln["home_id"] == g["home_id"]) & (ln["away_id"] == g["away_id"])] if len(ln) else ln
        row["n_books"] = int(L["book"].nunique()) if len(L) else 0
        row["book_lines"] = [{k: (None if pd.isna(v) else v) for k, v in r.items() if k not in ("et",)}
                             for r in L.drop(columns=["sgo_event", "start", "home_id", "away_id"], errors="ignore").to_dict("records")]
        ev = L["sgo_event"].iloc[0] if len(L) else None
        row["sgo_event"] = ev
        o = opens.get(ev, {}) if ev else {}
        fo = openers[openers["sgo_event"] == ev] if ev is not None and len(openers) else openers.iloc[0:0]
        row["open_total"] = o.get("open_total") if o.get("open_total") == o.get("open_total") else (fo["total"].median() if len(fo) else None)
        row["open_home_spread"] = o.get("open_home_spread") if o.get("open_home_spread") == o.get("open_home_spread") else (fo["home_spread"].median() if len(fo) else None)
        row["first_seen"] = fo["seen"].min() if len(fo) else None
        mt, mm = g["model_total"], g["model_margin"]
        # totals
        bo, bu = best(L, "total", "over_odds", higher=False), best(L, "total", "under_odds", higher=True)
        cand = []
        if bo: cand.append(("over", mt - bo["line"], bo))
        if bu: cand.append(("under", bu["line"] - mt, bu))
        row["total_verdict"] = None
        if cand and pd.notna(mt):
            side, e, b = max(cand, key=lambda x: x[1])
            ok_price = b["odds"] is None or b["odds"] >= MIN_PRICE
            p = total_p(e)
            row.update({"total_pick": side.title(), "total_line": b["line"], "total_odds": b["odds"], "total_book": b["book"],
                        "total_link": b["link"], "total_edge": round(e, 2), "total_p": p,
                        "total_ev": p * _payout(b["odds"] if b["odds"] is not None else -110) - (1 - p),
                        # line a play needs: edge 4+ and 3+ after the league-wide gap
                        "total_good_to": (mt - max(TOTAL_EDGE, REL_EDGE + gap) if side == "over"
                                          else mt + max(TOTAL_EDGE, REL_EDGE - gap)),
                        "total_units": 1.0})
            rel = e + gap if side == "under" else e - gap       # edge with the league-wide gap removed
            row["total_rel_edge"], row["market_gap"] = round(rel, 2), round(gap, 2)
            row["total_verdict"] = ("BET" if e >= TOTAL_EDGE and rel >= REL_EDGE and ok_price
                                    else "WATCH" if e >= TOTAL_WATCH else None)
            if row["total_verdict"] == "WATCH" and e >= TOTAL_EDGE and rel < REL_EDGE:
                row["total_gap_note"] = (f"Edge {e:.1f} but only {rel:.1f} after the league-wide gap "
                                         f"(model {gap:+.1f} vs openers lately); needs {REL_EDGE:g}+")
            if e >= 8:
                row["total_warn"] = ("Edge of 8+ points: rare in the backtest. Check injury news and the lineup; the "
                                     "model only knows who played in each team's last game.")
            if row["total_verdict"] == "BET" and live:
                row["_play"] = _play(day, g, ev, "total", "play", side, f"{side.title()} {b['line']:g}", b, mt, e, p, now)
        # spreads (leans only)
        bh, ba = best(L, "home_spread", "home_spread_odds", higher=True), None
        if len(L) and L["home_spread"].notna().any():
            A = L.assign(away_spread=-L["home_spread"])
            ba = best(A, "away_spread", "away_spread_odds", higher=True)
        cand = []
        if bh: cand.append(("home", mm + bh["line"], bh))
        if ba: cand.append(("away", -mm + ba["line"], ba))
        row["spread_verdict"] = None
        if cand and pd.notna(mm):
            side, e, b = max(cand, key=lambda x: x[1])
            team = g["home"] if side == "home" else g["away"]
            row.update({"spread_side": side, "spread_pick": team, "spread_line": b["line"], "spread_odds": b["odds"],
                        "spread_book": b["book"], "spread_link": b["link"], "spread_edge": round(e, 2), "spread_p": SPREAD_P})
            if e >= SPREAD_EDGE:
                row["spread_verdict"] = "LEAN"
                if live:
                    plays.append(_play(day, g, ev, "spread", "lean", side, f"{team} {b['line']:+g}", b, mm if side == "home" else -mm,
                                       e, SPREAD_P, now))
        games.append(row)
    _logged(games, day)
    _cap(games, plays, day)
    return games, plays


def _logged(games: list[dict], day) -> None:
    """A totals play logged earlier stays on the card at the number it was logged at, with where the line is now
    (as on the CBB card), even if the current number no longer qualifies."""
    lg = record.load()
    lg = lg[(lg["date"] == f"{day:%Y-%m-%d}") & (lg["market"] == "total") & (lg["kind"] == "play")]
    for g in games:
        r = lg[lg["game_id"].astype(int) == int(g["game_id"])]
        if not len(r):
            continue
        r = r.iloc[0]
        g["total_logged"] = {"pick": r["pick"], "line": float(r["line"]), "odds": None if pd.isna(r["odds"]) else float(r["odds"]),
                             "book": r["book"], "edge": float(r["edge"]), "logged_at": str(r["logged_at"])[:16]}
        still = g.get("total_verdict") == "BET" and str(g.get("total_pick", "")).lower() == r["side"]
        now = g.get("total_line")
        g["total_logged_status"] = (f"Logged {str(r['logged_at'])[5:16].replace('T', ' ')} UTC at {r['pick']} ({r['book']}). "
                                    + (f"Still a play now at {now:g}." if still else
                                       f"Line now {now:g}: not a play at this number. Your bet stands." if now is not None else ""))


def _cap(games: list[dict], plays: list[dict], day) -> None:
    """Apply MAX_PER_SIDE to the day's totals BETs (see above). Logged plays keep their slot."""
    logged = record.load()
    logged = logged[(logged["date"] == f"{day:%Y-%m-%d}") & (logged["market"] == "total") & (logged["kind"] == "play")]
    for side in ("Over", "Under"):
        bets = [g for g in games if g.get("total_verdict") == "BET" and g.get("total_pick") == side]
        ids = set(logged.loc[logged["side"] == side.lower(), "game_id"].astype(int))
        keep = [g for g in bets if int(g["game_id"]) in ids]
        slots = max(0, MAX_PER_SIDE - len(ids))
        new = sorted((g for g in bets if int(g["game_id"]) not in ids), key=lambda g: -g["total_edge"])
        keep += new[:slots]
        for g in new[slots:]:
            g["total_verdict"] = "CAPPED"
            g["total_capped"] = f"Over the {MAX_PER_SIDE}-per-side daily cap ({side.lower()}s); not logged"
        for g in keep:
            if g.get("_play"):
                plays.append(g["_play"])
    for g in games:
        g.pop("_play", None)


def _play(day, g, ev, market, kind, side, pick, b, model, edge, p, now) -> dict:
    return {"bet_id": f"{day:%Y-%m-%d}|{g['game_id']}|{market}|{side}", "date": f"{day:%Y-%m-%d}", "game_id": int(g["game_id"]),
            "sgo_event": ev, "start": str(g["start"]), "home": g["home"], "away": g["away"], "market": market, "kind": kind,
            "side": side, "pick": pick, "line": b["line"], "odds": b["odds"], "book": b["book"], "model": round(float(model), 2),
            "edge": round(float(edge), 2), "win_p": p, "logged_at": now}


HOLD_STATUSES = {"Out"}


def injury_hold(games: list[dict], plays: list[dict], gap: float = 0.0) -> list[dict]:
    """From Oct 30, 2026 (Chad, research/LOG.md entry 20): when ESPN lists a player Out who played in his team's
    last game (the projection still counts him), re-check the edge with the model's own estimate of his absence
    (injuries.py: d_total, d_home_margin). A play or lean that no longer qualifies is HELD: shown with the reason,
    not logged. Never creates a play. Returns the plays that still stand."""
    held = set()
    for g in games:
        outs = [a for a in g.get("injury_alerts") or [] if a["status"] in HOLD_STATUSES]
        if not outs:
            continue
        dt = sum(a["d_total"] for a in outs)
        dm = sum(a["d_home_margin"] for a in outs)
        names = ", ".join(f"{a['player']} ({a['team']})" for a in outs)
        if g.get("total_verdict") == "BET":
            adj = g["model_total"] + dt
            e = (g["total_line"] - adj) if g["total_pick"] == "Under" else (adj - g["total_line"])
            rel = e + gap if g["total_pick"] == "Under" else e - gap
            if e < TOTAL_EDGE or rel < REL_EDGE:
                g["total_verdict"] = "HELD"
                g["total_hold"] = (f"Held: {names} out. With his absence the model is {adj:.1f}, edge {e:+.1f} "
                                   f"({rel:+.1f} after the league-wide gap). Not logged.")
                held.add((g["game_id"], "total"))
        if g.get("spread_verdict") == "LEAN" and g.get("spread_side"):
            mm = g["model_margin"] + dm
            line = g["spread_line"]
            e = (mm + line) if g["spread_side"] == "home" else (-mm + line)
            if e < SPREAD_EDGE:
                g["spread_verdict"] = "HELD"
                g["spread_hold"] = f"Held: {names} out. Adjusted edge {e:+.1f}. Not logged."
                held.add((g["game_id"], "spread"))
    return [p for p in plays if (p["game_id"], p["market"]) not in held]
