# NBA feasibility test

Can a simple team-ratings model beat NBA opening lines by enough to matter? A research-only test; no live card.
Design follows barrca12-rgb/CBB (ratings, walk-forward second stage, scorecards). Free data only: hoopR results
and box scores, ESPN's stored odds. No Odds API.

* `research/LOG.md`: data coverage, the pre-registered specification and pass/kill rule, every run.
* `nba/data.py` results and box scores; `nba/lines.py` ESPN openers/closes and cleaning; `nba/ratings.py` stage 1;
  `nba/model.py` walk-forward; `nba/scorecards.py` the scorecards.

    pip install -r requirements.txt
    python -m nba.lines --start 2014 --end 2026     # odds (resumable; raw rows committed in data/lines)
    python -m research.coverage                     # coverage table
    python -m research.s1 grid                      # stage-1 grid on development results only
    python -m research.s1 run                       # frozen model + scorecards + verdict

## Live card (2026-27)

`barrca12-rgb.github.io/NBA/`, built by `.github/workflows/update.yml` (8 runs a day, October-June, plus the
Update button). Same design as the CBB card.

* Lines: SportsGameOdds only (`nba/odds.py`, secret `SGO_API_KEY`); first number seen per book is kept in
  `lines/openers.csv`, the last pregame number in `lines/closing.csv`. No Odds API.
* Model: frozen phase 4 spec (`data/model.json`, from `python -m nba.fit 2027`); `nba/live.py` projects a day.
* Plays: totals with edge 4+ vs the best number (price -130 or better), 1 unit; spreads 3+ are leans (tracked,
  not bet). Every play is logged at the number it first appeared in `bets/plays.csv` and graded vs the close and
  the final (`nba/record.py`).

    python -m nba.run_day --auto        # today, plus tomorrow when tomorrow has lines
