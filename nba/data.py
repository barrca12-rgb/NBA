"""NBA game results and team box scores from hoopR (sportsdataverse), cached locally.

Same source and layout as barrca12-rgb/CBB cbb/data.py, NBA files:
  * schedules  (espn_nba_schedules/nba_schedule_{season}.parquet)
  * team box   (espn_nba_team_boxscores/team_box_{season}.parquet): two rows per game

`season` is the year the season ends: 2025 = the 2024-25 season.

Outputs (the 30 NBA franchises only, completed regular-season, play-in and playoff games; All-Star and
exhibition games against non-NBA teams drop out):
  games       one row per game: date, home/away ESPN ids, neutral, scores, periods, pace
  team_games  two rows per game (offense `team` vs defense `opp`): points per 100 possessions and pace
"""
from __future__ import annotations

import os
import urllib.request

import numpy as np
import pandas as pd

RELEASES = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
FILES = {
    "schedule": "espn_nba_schedules/nba_schedule_{season}.parquet",
    "team_box": "espn_nba_team_boxscores/team_box_{season}.parquet",
}
CACHE = os.path.join(os.path.dirname(__file__), "cache")
TEAMS = set(range(1, 31))      # ESPN ids of the 30 franchises
FT_WEIGHT = 0.44               # free-throw weight in the possession estimate (Oliver; standard for the NBA)


def fetch(kind: str, season: int, refresh: bool = False) -> pd.DataFrame:
    rel = FILES[kind].format(season=season)
    path = os.path.join(CACHE, os.path.basename(rel))
    if refresh or not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        req = urllib.request.Request(f"{RELEASES}/{rel}", headers={"User-Agent": "nba-feasibility"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path + ".tmp", "wb") as f:
            f.write(r.read())
        os.replace(path + ".tmp", path)
    return pd.read_parquet(path)


def possessions(fga, orb, tov, fta):
    return fga - orb + tov + FT_WEIGHT * fta


def season_games(season: int, refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    sch = fetch("schedule", season, refresh)
    box = fetch("team_box", season, refresh)
    sch = sch[sch["status_type_completed"].fillna(False).astype(bool)].drop_duplicates("game_id")
    g = pd.DataFrame({
        "game_id": sch["game_id"].astype(int),
        "season": season,
        "season_type": sch["season_type"].astype(int),   # 2 regular, 3 playoffs, 5 play-in
        "date": pd.to_datetime(sch["game_date"]),
        "start": pd.to_datetime(sch["game_date_time"], utc=True),
        "home_id": sch["home_id"].astype(int),
        "away_id": sch["away_id"].astype(int),
        "home": sch["home_abbreviation"],
        "away": sch["away_abbreviation"],
        "neutral": sch["neutral_site"].fillna(False).astype(bool),
        "home_pts": pd.to_numeric(sch["home_score"], errors="coerce"),
        "away_pts": pd.to_numeric(sch["away_score"], errors="coerce"),
        "periods": pd.to_numeric(sch["status_period"], errors="coerce"),
    })
    g = g[g["home_id"].isin(TEAMS) & g["away_id"].isin(TEAMS) & g["season_type"].isin([2, 3, 5])]

    b = box.drop_duplicates(["game_id", "team_id"])
    t = pd.DataFrame({
        "game_id": b["game_id"].astype(int), "team_id": b["team_id"].astype(int),
        "opp_id": b["opponent_team_id"].astype(int), "pts": b["team_score"].astype(float),
        "fga": b["field_goals_attempted"], "fta": b["free_throws_attempted"],
        # Turnovers include team turnovers (total_turnovers). 2018 lacks that field and 2012 double-counts it
        # (team_turnovers = turnovers); there player turnovers stand in (~1 per game short).
        "orb": b["offensive_rebounds"],
        "tov": b["total_turnovers"].where(b["team_turnovers"] < 0.5 * b["turnovers"]).fillna(b["turnovers"]),
    })
    opp = t[["game_id", "team_id", "fga", "orb", "tov", "fta"]].rename(
        columns={"team_id": "opp_id", "fga": "o_fga", "orb": "o_orb", "tov": "o_tov", "fta": "o_fta"})
    t = t.merge(opp, on=["game_id", "opp_id"]).merge(
        g[["game_id", "season", "season_type", "date", "home_id", "neutral", "periods"]], on="game_id")
    # Possessions: average of both teams' estimates; pace per 48 minutes so overtime doesn't inflate it.
    t["poss"] = (possessions(t["fga"], t["orb"], t["tov"], t["fta"]) +
                 possessions(t["o_fga"], t["o_orb"], t["o_tov"], t["o_fta"])) / 2
    minutes = 48 + 5 * (t["periods"].fillna(4) - 4).clip(lower=0)
    t["pace"] = t["poss"] * 48 / minutes
    t["ppp"] = 100 * t["pts"] / t["poss"]
    t["venue"] = np.where(t["neutral"], 0, np.where(t["team_id"] == t["home_id"], 1, -1))
    t = t[t["poss"] > 0].drop(columns=["home_id", "o_fga", "o_orb", "o_tov", "o_fta"])
    pace = t.groupby("game_id")["pace"].first()
    g = g[g["game_id"].isin(pace.index)].copy()
    g["pace"] = g["game_id"].map(pace)
    return g.reset_index(drop=True), t[t["game_id"].isin(g["game_id"])].reset_index(drop=True)


def load(seasons, refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    parts = [season_games(s, refresh) for s in seasons]
    return (pd.concat([p[0] for p in parts], ignore_index=True),
            pd.concat([p[1] for p in parts], ignore_index=True))
