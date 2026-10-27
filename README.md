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
