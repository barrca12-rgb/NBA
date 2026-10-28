"""LUMA Basketball Research API (lumahoops.org; data CC BY 4.0, credit LUMA Basketball Research).

Pulls dated snapshots the model can use without looking ahead, into data/luma/ (committed, so every number the
model used is on record and backtests are reproducible). The free key allows 6 queries a minute and 2,500 rows a
day, so the pull is filtered server-side and runs daily until the history is in, in this order:
  arc_live_<current>.csv   this season's in-season ARC, every weekly snapshot, rotation players (200+ possessions)
  loki_pre_<season>.csv    each season's preseason LOKI board (rookies and returning players)
  arc_monthly_<season>.csv first snapshot of each month, rotation players, newest seasons first
  players.csv              pid, name (last)

    LUMA_KEY=... python -m nba.luma pull --start 2014 --end 2027

Needs LUMA_KEY (header x-luma-key; free key = 1,500 queries a day). The SQL tool returns at most 200 rows a
query, so a full history is several hundred queries; the pull is resumable (finished past seasons are skipped,
the current season's file is refreshed every run) and stops before passing the daily row budget.
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
ROW_BUDGET = 2400          # free key: 2,500 rows a day (resets 00:00 UTC); stop a little short
MIN_POSS = 200             # rotation players only (season possessions at the snapshot)
# Each job: (file, count SQL, page SQL). Filtered server-side to what the model can use (LUMA's advice).
MONTHLY = ('"asof" IN (SELECT min("asof") FROM arc_live WHERE season = {season} '
           'GROUP BY date_trunc(\'month\', CAST("asof" AS DATE)))')
ARC_COLS = 'season, "asof" AS asof, pid, team, net, "O" AS o, "D" AS d, poss_season AS poss, gp_season AS gp'


def jobs(current: int, start: int) -> list[tuple[str, str, str]]:
    out = []
    w = f"season = {current} AND poss_season >= {MIN_POSS}"
    have = os.path.join(OUT, f"arc_live_{current}.csv")
    if os.path.exists(have):                          # incremental: only snapshots newer than the file
        last = pd.read_csv(have)["asof"].max()
        w += f" AND \"asof\" > '{last}'"
    out.append((f"arc_live_{current}.csv", f"SELECT count(*) AS n FROM arc_live WHERE {w}",
                f'SELECT {ARC_COLS} FROM arc_live WHERE {w} ORDER BY "asof", pid LIMIT {{lim}} OFFSET {{off}}'))
    for s in range(current, start - 1, -1):          # preseason LOKI board, every season (rookies, returners)
        w = (f'season = {s} AND release = (SELECT min(release) FROM loki WHERE season = {s})')
        out.append((f"loki_pre_{s}.csv", f"SELECT count(*) AS n FROM loki WHERE {w}",
                    f'SELECT season, "asof" AS asof, release, pid, team, net, "O" AS o, "D" AS d FROM loki WHERE {w} '
                    f"ORDER BY pid LIMIT {{lim}} OFFSET {{off}}"))
    for s in range(current - 1, start - 1, -1):      # monthly in-season ARC, test seasons first, then older
        w = f"season = {s} AND poss_season >= {MIN_POSS} AND " + MONTHLY.format(season=s)
        out.append((f"arc_monthly_{s}.csv", f"SELECT count(*) AS n FROM arc_live WHERE {w}",
                    f'SELECT {ARC_COLS} FROM arc_live WHERE {w} ORDER BY "asof", pid LIMIT {{lim}} OFFSET {{off}}'))
    return out


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
            time.sleep(11)                       # pace: LUMA allows 6 queries a minute
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
            if attempt or wait > 120:
                raise Budget(f"LUMA rate limit (retry after {wait:.0f}s)")
            time.sleep(wait)
    raise Budget("LUMA rate limit")


def sql(query: str) -> pd.DataFrame:
    d = q("sql", query=query)
    if not d.get("ok", True):
        raise RuntimeError(d)
    return pd.DataFrame(d["rows"], columns=d["columns"])


def pull_job(name: str, count_sql: str, page_sql: str, refresh: bool) -> None:
    path = os.path.join(OUT, name)
    if os.path.exists(path) and not refresh:
        return
    n = int(sql(count_sql)["n"].iloc[0])
    if getattr(q, "rows", 0) + n > ROW_BUDGET:
        raise Budget(f"next file {name} ({n:,} rows) would pass today's row budget")
    parts = []
    for off in range(0, n, PAGE):
        parts.append(sql(page_sql.format(lim=PAGE, off=off)))
        q.rows = getattr(q, "rows", 0) + len(parts[-1])
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(df) != n:
        raise RuntimeError(f"{name}: got {len(df)} of {n} rows")
    if refresh and os.path.exists(path):              # current season: append the new snapshots
        if not n:
            return
        df = pd.concat([pd.read_csv(path), df], ignore_index=True).drop_duplicates(["asof", "pid"])
    df.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)
    print(f"{name}: {n:,} rows ({q.calls} calls, {q.rows:,} rows today)", flush=True)


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
        for name, c, pg in jobs(a.current, a.start):
            pull_job(name, c, pg, refresh=name == f"arc_live_{a.current}.csv")
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
