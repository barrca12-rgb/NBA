# NBA feasibility test: research log

Question: can a simple team-ratings model beat NBA **opening** lines by enough to matter? If not, we stop.

Every specification tried is logged here, failures included, in the order run. Nothing is tuned on the holdout
seasons (2024-25 and 2025-26).

Seasons are named by the year they end: 2025 = 2024-25.

---

## Entry 1 (2026-10-27): data and coverage, before any modeling

**Sources (free, no Odds API, no credits used):**

* Results and team box scores: sportsdataverse hoopR NBA parquet files on GitHub releases
  (`nba/data.py`), seasons 2012-2026. The 30 franchises only; regular season, play-in and playoffs.
  Possessions = FGA - ORB + TOV + 0.44 FTA, averaged over both teams; pace per 48 minutes.
  Data fixes: 2018's file has no team-turnover total and 2012's double-counts it, so those seasons use player
  turnovers (about 1 per game short). Pace and efficiency by season then track the known league trend
  (93.6 possessions in 2012 up to 101.8 in 2026).
* Opening and closing spreads and totals: ESPN's stored odds, `sports.core.api.espn.com` (`nba/lines.py`),
  one request per game, every book ESPN kept, with each book's opener, close, opening and closing moneylines,
  and the record's own home/away team ids. Raw rows are committed in `data/lines/espn_<season>.csv`.

**Cleaning (pregame information only; the close is never used to fix an opener):**

* Projection services listed like books (accuscore, numberfire, teamrankings, ESPN's "consensus", ...) dropped
  (CBB list).
* Reversed records: a record whose own home team id is the game's away team is dropped. **None found** in any
  season (0 of about 163,000 records).
* A closing spread whose sign contradicts the record's own text ("OKC -1") by more than a point is dropped. This
  catches 440 ESPN BET records in 2022-23 that hold prices (-105/-115) in the spread field, and 61 near-pick'em
  records in 2023-24. Plausibility: |spread| <= 30, totals 150-300.
* Openers oriented by their own opening moneylines (CBB "flip" rule): an opener that favors the team its own
  moneyline makes the underdog, by more than a point, has its sign corrected. 5-54 per season.
* ESPN's "Opening" pseudo-book (2014-2017) is the opener for those seasons, as in CBB.
* Consensus per game = median across books; a book more than 5 points off the median spread is dropped.

**Coverage** (share of completed games with each line; full table and book list in `research/out/coverage.md`):

| season | games | close spread | close total | open spread | open total | books/game | books with opener |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2013-14 | 1,318 | 100% | 100% | 100% | 100% | 5 | 1 ("Opening") |
| 2014-15 | 1,311 | 97% | 97% | 97% | 97% | 5 | 1 ("Opening") |
| 2015-16 | 1,316 | 100% | 100% | 100% | 100% | 7 | 1 ("Opening") |
| 2016-17 | 1,308 | 97% | 97% | 97% | 97% | 10 | 1 ("Opening") |
| 2017-18 to 2022-23 | 7,574 | 100% | 100% | **0%** | **0%** | 6-12 | 0 |
| 2023-24 | 1,319 | 100% | 100% | 100% | 100% | 10 | 10 |
| 2024-25 | 1,321 | 100% | 100% | 100% | 100% | 1 (ESPN BET) | 1 |
| 2025-26 | 1,322 | 100% | 100% | 100% | 100% | 1 (DraftKings, some ESPN BET) | 1 |

**Openers look genuine:** they differ from the close in 76-87% of games (mean move 1.1-1.8 points on spreads,
2.0-3.4 on totals), and the close beats the opener on accuracy in every season (e.g. 2024-25 margin miss 11.01
at the open vs 10.64 at the close).

**Opener seasons:** 2014-2017 and 2024-2026, about 9,200 games. Closes exist for every season 2014-2026.
Limitation: 2025 and 2026 openers come from a single book each, and the 2014-17 openers from ESPN's unnamed
"Opening" feed.

Verdict for step 1: openers are available free, so the test proceeds.

---

## Entry 2 (2026-10-27): pre-registration, written before any model is run against a line

### Specification S1 (the only specification that decides pass/kill)

Code: `nba/ratings.py`, `nba/model.py`, `nba/scorecards.py`, run by `research/s1.py`.

**Stage 1, ratings** (CBB `cbb/ratings.py` without Four Factors). For each game date, fit on this season's games
strictly before that date:

    points per 100 possessions = b0 + hca * venue + off[team] - def[opp]
    pace                      = p0 + tempo[team] + tempo[opp]

Weighted ridge: weight halves every `half_life` days; shrinks toward a preseason prior = last season's final
ratings times `carry` (with `prior_games` of strength); league baseline before any games = last season's average.
Home court is a fitted parameter (light pull toward 1.5 per 100 per side). The 2020 Orlando bubble games
(from 2020-07-30) are treated as neutral. Output: ratings-only margin and total.

Stage 1 hyperparameters are chosen once, by a small grid scored **only on results (not lines) in development
seasons 2014-2024**, criterion = margin MAE + total MAE of the ratings-only prediction:
half_life in {30, 60, 120} days, prior_games (also used for pace) in {5, 10, 20}, carry in {0.5, 0.75}
(18 runs). Season 2013 is a burn-in (prior from 2012). The chosen values are then frozen.

**Stage 2, walk-forward ridge by season** (CBB `cbb/projection.py`, lambda 1). Season s is predicted with
coefficients fit only on seasons 2013..s-1 (first predicted season 2014).

* Margin features: ratings margin, ratings margin x early, venue (0 neutral), home back-to-back, away
  back-to-back, rest difference (days off beyond one, capped at 3 each).
* Total features: ratings total, ratings total x early, season scoring average so far (earlier dates, once 100
  games; else last season's), back-to-backs (sum), rest (sum).
* early = 1 - (average games played by the two teams)/20, floored at 0.

The market line is never an input.

**Samples.** Development: 2014-2024 (opener scorecards therefore use 2014-2017 and 2024). Holdout: 2025, 2026.
All completed games with the needed line: regular season, play-in and playoffs.

**Suspect-record rule** (CBB `evaluate.swapped()` adapted; NBA has no KenPom, so model only): spread plays are
excluded where the opener's favorite is the other team from the model's and the two disagree by 10+ points.
Count reported. Totals unaffected.

### Scorecards (development and holdout reported separately)

1. **MAE**: model vs closing line, margin and total, games with a close.
2. **Beyond the close**: OLS of (result - close) on (model - close), intercept included, standard errors
   clustered by date; margin and total. Slope > 0 with a t-stat above 2 = information the close lacks.
3. **At the opener**: bet the model's side when |model - opener| >= edge. Spread edges 2 / 3 / 4+, total edges
   3 / 4 / 5+. Win % (pushes excluded), ROI at -110, play counts, 95% intervals from a bootstrap that resamples
   game dates (2,000 draws, seed 0).
4. **Opener CLV**: mean points the close moved toward each play (plays with both an opener and a close).

### Pass rule (fixed now)

Pre-registered thresholds: **spreads at 3+ points, totals at 4+ points** (the other edges are descriptive only).

The NBA idea **passes** if, for spreads at 3+ **or** totals at 4+, all of these hold for that market:

* win % at the opener above 52.4% in development **and** above 52.4% in holdout;
* holdout 95% bootstrap interval lower bound above 50%;
* mean opener CLV above 0 in development **and** in holdout.

Otherwise the NBA idea is **killed**, and that is said plainly. If it passes: stop and report; no live card.

Any further specification after S1 is exploratory, logged below, and cannot change the verdict.

---

## Entry 3 (2026-10-27): stage-1 grid (development results only, no lines)

18 configurations, ratings-only predictions, development seasons 2014-2024, criterion margin MAE + total MAE
(`research/out/s1_grid.csv`). Best: **half_life 30 days, prior_games 10, carry 0.5** (margin 10.27, total 14.48).
All 18 were within 0.22 points of each other on the criterion; the choice barely matters. Frozen in
`research/out/s1_config.json`.

## Entry 4 (2026-10-27): S1 result, the pre-registered run (`research/out/s1.md`)

Run once with the frozen configuration. 34 spread plays excluded as suspect records (13 of them in 2025).

| | development | holdout |
|---|---:|---:|
| Margin miss, model / close | 10.24 / 9.87 | 11.27 / 10.82 |
| Total miss, model / close | 14.46 / 14.06 | 14.77 / 14.33 |
| Beyond the close, margin slope (se) | 0.011 (0.034) | -0.015 (0.067) |
| Beyond the close, total slope (se) | -0.065 (0.039) | -0.046 (0.077) |
| Spreads 3+ at the opener: win %, plays, CLV | 49.5%, 1,654, +0.54 | 52.8% (49.3-56.1), 945, +0.66 |
| **Totals 4+ at the opener: win %, plays, CLV** | **53.2%, 1,614, +1.65** | **56.4% (52.9-59.7), 844, +2.49** |

Pass rule:
* spreads at 3+: development 49.5% (below 52.4%) and holdout interval low 49.3% -> **fail**
* totals at 4+: development 53.2% > 52.4%, holdout 56.4% > 52.4%, holdout interval low 52.9% > 50%, CLV +1.65
  and +2.49 -> **pass**

**Verdict under the pre-registered rule: PASS (totals only).** Per the plan, stop here; no live card.

## Entry 5 (2026-10-27): exploratory checks on the totals pass (`research/out/s1_checks.md`)

Not pre-registered; cannot change the verdict. They say how much weight it deserves.

* **The holdout pass leans on one season.** Totals 4+ by season: 2014 53.8%, 2015 55.1%, 2016 53.0%,
  2017 56.6%, 2024 **50.4%**, 2025 **59.6%** (CLV +3.56), 2026 **52.5%** (CLV +1.19). 2026 on its own is
  break-even at -110.
* **It looks like a "soft opener" effect.** The winning seasons have a single opening source (ESPN's unnamed
  "Opening" feed in 2014-17; ESPN BET alone in 2025, whose opener missed by 14.73 vs 14.14 at the close, the
  widest gap of any season). 2024, the one season whose opener is a median of about 10 books, is 50.4%.
* **No information beyond the close** (slopes about 0, totals slightly negative): the model only knows things
  the market adds by closing time. Any edge exists only before the line moves, so it depends on getting the
  opener at a real limit.
* **Not a directional bias in openers:** always-over and always-under lose (49-51%); betting the season scoring
  average loses (51-52%). The ratings-only total (before stage 2) does about as well as S1 (54.7% / 55.1%), so the
  signal is the ratings.
* The model ran 1-2 points over the opener on average in 2024-26 (more overs than unders); not corrected, since
  that would be tuning after seeing results.
* Spreads: positive CLV (+0.5 to +0.8) but no win rate, consistent with the opener moving the model's way by less
  than the model's error.

---

## Entry 6 (2026-10-27): phase 2 plan, written before any phase-2 run

Chad's direction: test only on the last three seasons (2023-24, 2024-25, 2025-26; all have openers) and improve
the stats the model uses, for spreads and totals. Reference: lumahoops.org.

**Guard against fooling ourselves.** Tuning features on all three test seasons would leave no out-of-sample
check, so:
* **Selection seasons: 2024 and 2025** (2023-24, 2024-25). Every candidate is scored there.
* **Check season: 2026** (2025-26), scored once, on the final specification only.
* Stage 2 is still trained walk-forward on earlier seasons only (2013 on); old seasons are training data, not
  tests.
* **Adoption rule:** a candidate feature is kept if it lowers the selection-season miss (margin MAE for spread
  features, total MAE for total features) vs the current spec. Win % at the opener is reported for every
  candidate but not used to choose: at about 600 plays a season it is too noisy to select on without
  overfitting.
* Scorecards and the 52.4% / interval / CLV rule are unchanged. Spreads 3+ and totals 4+ remain the headline
  thresholds.

**New data (free, no keys):** LUMA ARC v3.1 season boards (lumahoops.org open data, CC BY 4.0, release SHA-256
dffdf0b2...0f33): player impact per 100 possessions, 1997-98 to 2025-26. hoopR player box scores 2013-2026.
Players are matched by name (ESPN to NBA ids). A player's ARC for season s is the season s-1 board (2-year
window), so nothing from season s is used. Caveat: ARC's box-score weights are fit by LUMA across all seasons,
which may leak slightly.

**Pregame timing.** Player box scores list only players dressed for a game (announced near tip), after the
opener. Bettable features use only players who played in the team's previous game; for a team's first game of a
season (no previous game), the dressed list stands in (about 30 games a season).

**Candidates, in this order, each added only if it passes the adoption rule:**
* P1 player strength: minutes-weighted ARC of the players who played in the team's previous game (expected
  minutes = their average over their last 10 appearances), plus the same for the team's usual rotation (last 10
  team games). Margin: available-strength difference and missing-strength difference. Total: offensive and
  defensive ARC sums.
* P2 3-point luck regressed in the ratings (CBB THREE_LUCK = 0.35).
* P3 schedule fatigue: 3 games in 4 nights, games in the last 7 days; travel (time zones crossed since the last
  game); altitude (Denver, Utah home games).
* P4 stage 2 weights recent seasons more (season half-life 3).
* P5 a shorter half-life for pace than for efficiency (pace 15 days).

**Diagnostic only (not bettable at the open):** the same player strength from the dressed list, to show how much
late injury news is worth.
