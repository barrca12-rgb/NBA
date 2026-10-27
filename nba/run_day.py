"""Build the NBA card: live lines (SportsGameOdds), projections, plays log, grading, and the HTML pages.

    python -m nba.run_day --auto            # today (ET) and tomorrow when tomorrow has lines
    python -m nba.run_day --date 2026-10-28

Writes reports/nba_<date>.html and reports/days.json; updates lines/openers.csv, lines/closing.csv and
bets/plays.csv.
"""
from __future__ import annotations

import argparse
import json
import os

import pandas as pd

from . import card, data, live, odds, record, report_html

REPORTS = os.path.join(os.path.dirname(__file__), "..", "reports")


def season_of(day: pd.Timestamp) -> int:
    return day.year + 1 if day.month >= 8 else day.year


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--auto", action="store_true")
    a = ap.parse_args()
    today = pd.Timestamp(pd.Timestamp.now(tz="America/New_York").date())
    season = season_of(today)
    sch = data.fetch("schedule", season, refresh=True)
    names = dict(zip(sch["home_id"].astype(int), sch["home_display_name"]))
    try:
        lines = odds.fetch(sch)
        op, cl = odds.track(lines)
        opens, usage = odds.fetch.opens, odds.fetch.usage
    except Exception as e:                       # no key or feed down: last stored lines, no new plays logged
        print(f"SGO unavailable ({e}); using the last stored lines")
        opens, usage = {}, {"error": str(e)}
        op = pd.read_csv(os.path.join(odds.LINES, "openers.csv")) if os.path.exists(os.path.join(odds.LINES, "openers.csv")) else pd.DataFrame(columns=["sgo_event", "total", "home_spread", "seen"])
        cl = pd.read_csv(os.path.join(odds.LINES, "closing.csv")) if os.path.exists(os.path.join(odds.LINES, "closing.csv")) else pd.DataFrame(columns=["sgo_event", "home_spread", "total"])
        now = pd.Timestamp.now(tz="UTC")
        lines = cl[pd.to_datetime(cl["start"], utc=True) > now].reindex(columns=odds.COLS) if len(cl) else pd.DataFrame(columns=odds.COLS)
        a.stale = True
    if a.date:
        days = [pd.Timestamp(a.date)]
    else:
        days = [today]
        tmr = today + pd.Timedelta(days=1)
        if len(lines):
            et = pd.to_datetime(lines["start"], utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
            if (et == f"{tmr:%Y-%m-%d}").any():
                days.append(tmr)
    built = []
    for day in days:
        proj, rt = live.project(day, season_of(day))
        games, plays = card.build(proj, lines, opens, op, day, live=day >= today and not getattr(a, "stale", False))
        record.log(plays)
        built.append((day, games, rt))
        print(f"{day:%Y-%m-%d}: {len(games)} games, {sum(g['total_verdict'] == 'BET' for g in games)} plays, "
              f"{sum(g['spread_verdict'] == 'LEAN' for g in games)} leans", flush=True)
    rec = record.status(record.grade(cl))
    os.makedirs(REPORTS, exist_ok=True)
    for day, games, rt in built:
        page = report_html.build(games, rt, names, day, season_of(day), rec, usage)
        with open(os.path.join(REPORTS, f"nba_{day:%Y-%m-%d}.html"), "w") as f:
            f.write(page)
    have = sorted(f[4:14] for f in os.listdir(REPORTS) if f.startswith("nba_") and f.endswith(".html"))
    with open(os.path.join(REPORTS, "days.json"), "w") as f:
        json.dump({"days": have, "current": f"{today:%Y-%m-%d}" if f"{today:%Y-%m-%d}" in have else have[-1]}, f)


if __name__ == "__main__":
    main()
