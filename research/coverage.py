"""Step 1 data coverage: per season, share of games with an opening / closing spread and total (ESPN, free),
books per game, opener orientation counts and reversed records.

    python -m research.coverage            # writes research/out/coverage.md
"""
from __future__ import annotations

import os

import pandas as pd

from nba import data, lines

OUT = os.path.join(os.path.dirname(__file__), "out")


def main(start=2014, end=2026):
    rows, books = [], []
    for s in range(start, end + 1):
        g, _ = data.season_games(s)
        raw = pd.read_csv(os.path.join(lines.OUT, f"espn_{s}.csv"))
        real = raw[~raw["book"].fillna("").isin(lines.NOT_BOOKS | {"", "fetch failed"})]
        rev = lines.reversed_records(real, g)
        c = lines.consensus(raw, g)
        m = g[["game_id"]].merge(c, on="game_id", how="left")
        n = len(g)
        rows.append({"season": f"{s - 1}-{str(s)[2:]}", "games": n,
                     "close spread": m["home_spread"].notna().mean(), "close total": m["total"].notna().mean(),
                     "open spread": m["open_home_spread"].notna().mean(), "open total": m["open_total"].notna().mean(),
                     "books/game (median)": m["books"].median(),
                     "books w/ opener (median)": m["open_books"].median(),
                     "reversed records": int(rev.sum()), "games w/ reversed record": int(real.loc[rev, "game_id"].nunique()),
                     "openers mis-oriented (flipped)": lines.consensus.counts["mis-oriented"],
                     "fetch failed": int((raw["book"] == "fetch failed").sum())})
        books.append(real.groupby("book")["game_id"].nunique().rename(s))
    t = pd.DataFrame(rows).set_index("season")
    pct = ["close spread", "close total", "open spread", "open total"]
    md = ["# Data coverage: ESPN stored NBA odds (free)", "",
          "Share of completed games (regular season, play-in, playoffs) with each line after cleaning "
          "(real books only, reversed records dropped, openers oriented by their own moneylines).", "",
          t.to_markdown(floatfmt=".0%") if False else _md(t, pct), "",
          "## Books by season (games covered)", "", _books(pd.concat(books, axis=1).fillna(0).astype(int)), ""]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "coverage.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))


def _md(t, pct):
    out = ["| season | " + " | ".join(t.columns) + " |", "|---|" + "---:|" * len(t.columns)]
    for k, r in t.iterrows():
        out.append(f"| {k} | " + " | ".join(f"{r[c]:.0%}" if c in pct else f"{r[c]:,.0f}" for c in t.columns) + " |")
    return "\n".join(out)


def _books(b):
    out = ["| book | " + " | ".join(map(str, b.columns)) + " |", "|---|" + "---:|" * len(b.columns)]
    for k, r in b.sort_values(b.columns[-1], ascending=False).iterrows():
        out.append(f"| {k} | " + " | ".join(f"{v:,}" for v in r) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    main()
