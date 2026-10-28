"""LUMA Basketball Research API (lumahoops.org; data CC BY 4.0, credit LUMA Basketball Research).

Pulls the dated snapshots the model can use without looking ahead, into data/luma/ (committed, so every number the
model used is on record and backtests are reproducible):
  arc_live_<season>.csv   in-season ARC, about weekly (asof = snapshot date): pid, team, net, O, D, poss, games
  loki_<season>.csv       LOKI predicted ARC, 4 releases a season since 2007-08 (preseason, quarter, ...)
  players.csv             pid, name

    LUMA_KEY=... python -m nba.luma pull --start 2014 --end 2027

Needs LUMA_KEY (header x-luma-key; free key = 1,500 queries a day). The SQL tool returns at most 200 rows a
query, so a full history is several hundred queries; the pull is resumable (finished past seasons are skipped,
the current season is always refreshed) and stops cleanly near the daily limit.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request

import pandas as pd

API = "https://lumahoops.org/api/luma/q"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "luma")
PAGE = 200
TABLES = {
    "arc_live": 'SELECT season, "asof" AS asof, pid, team, net, "O" AS o, "D" AS d, poss_season AS poss, '
                'gp_season AS gp FROM arc_live WHERE season = {season} ORDER BY "asof", pid LIMIT {lim} OFFSET {off}',
    "loki": 'SELECT season, "asof" AS asof, release, pid, team, net, "O" AS o, "D" AS d FROM loki '
            'WHERE season = {season} ORDER BY "asof", pid LIMIT {lim} OFFSET {off}',
}
COUNT = {"arc_live": "SELECT count(*) AS n FROM arc_live WHERE season = {season}",
         "loki": "SELECT count(*) AS n FROM loki WHERE season = {season}"}


class Budget(Exception):
    pass


def q(tool: str, **args) -> dict:
    """One call. On 429 waits retry_after_s once; a second 429 stops the pull (daily limit)."""
    body = json.dumps({"tool": tool, "args": args}).encode()
    for attempt in range(2):
        req = urllib.request.Request(API, data=body, method="POST", headers={
            "content-type": "application/json", "x-luma-key": os.environ.get("LUMA_KEY", ""),
            "User-Agent": "nba-card (Off The Glass)"})
        try:
            time.sleep(1.0)                      # pace: one call a second
            with urllib.request.urlopen(req, timeout=60) as r:
                q.calls = getattr(q, "calls", 0) + 1
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            raw = e.read() or b"{}"
            info = json.loads(raw)
            hdr = {k: v for k, v in e.headers.items() if "limit" in k.lower() or "retry" in k.lower()}
            print(f"LUMA 429 after {getattr(q, 'calls', 0)} calls: {raw.decode()[:500]} {hdr}", flush=True)
            wait = float(info.get("retry_after_s", 60))
            if attempt or wait > 300:
                raise Budget(f"LUMA rate limit (retry after {wait:.0f}s)")
            time.sleep(wait)
    raise Budget("LUMA rate limit")


def sql(query: str) -> pd.DataFrame:
    d = q("sql", query=query)
    if not d.get("ok", True):
        raise RuntimeError(d)
    return pd.DataFrame(d["rows"], columns=d["columns"])


def pull_table(table: str, season: int, refresh: bool) -> None:
    path = os.path.join(OUT, f"{table}_{season}.csv")
    if os.path.exists(path) and not refresh:
        return
    n = int(sql(COUNT[table].format(season=season))["n"].iloc[0])
    parts = [sql(TABLES[table].format(season=season, lim=PAGE, off=off)) for off in range(0, n, PAGE)]
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(df) != n:
        raise RuntimeError(f"{table} {season}: got {len(df)} of {n} rows")
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)
    print(f"{table} {season}: {n:,} rows ({getattr(q, 'calls', 0)} calls so far)", flush=True)


def pull_players() -> None:
    n = int(sql("SELECT count(*) AS n FROM players")["n"].iloc[0])
    df = pd.concat([sql(f"SELECT pid, name FROM players ORDER BY pid LIMIT {PAGE} OFFSET {o}") for o in range(0, n, PAGE)])
    df.to_csv(os.path.join(OUT, "players.csv"), index=False)
    print(f"players: {len(df):,}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pull"])
    ap.add_argument("--start", type=int, default=2014)
    ap.add_argument("--end", type=int, default=2027)
    ap.add_argument("--current", type=int, default=2027, help="season always refreshed")
    a = ap.parse_args()
    if not os.environ.get("LUMA_KEY"):
        raise SystemExit("LUMA_KEY is not set")
    os.makedirs(OUT, exist_ok=True)
    try:
        # LOKI first (about 14 calls a season), then in-season ARC (about 80 a season); newest seasons first.
        # Names come from the ARC/LOKI download files, so the players table is pulled last.
        for t in ("loki", "arc_live"):
            for s in range(a.end, a.start - 1, -1):
                pull_table(t, s, refresh=(s == a.current))
        if not os.path.exists(os.path.join(OUT, "players.csv")):
            pull_players()
    except Budget as e:
        print(f"stopped: {e}; rerun tomorrow to continue")
    # manifest: what is on disk and when this pull ran (for citing the data a backtest used)
    files = {f: int(sum(1 for _ in open(os.path.join(OUT, f))) - 1) for f in sorted(os.listdir(OUT)) if f.endswith(".csv")}
    with open(os.path.join(OUT, "MANIFEST.json"), "w") as f:
        json.dump({"pulled_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "calls": getattr(q, "calls", 0),
                   "source": "LUMA Basketball Research (lumahoops.org), CC BY 4.0", "rows": files}, f, indent=1)
    print(f"{getattr(q, 'calls', 0)} LUMA calls")


if __name__ == "__main__":
    main()
