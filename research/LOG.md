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

## Entry 7 (2026-10-27): phase 2 selection, seasons 2024-2025 only (`research/out/p2_select.md`)

Base = S1 with stage 2 trained from 2014. Candidates added in the logged order, kept by the adoption rule
(selection-season MAE), win % shown for information only.

| spec | margin MAE | total MAE | spreads 3+ win % (plays) | CLV | totals 4+ win % (plays) | CLV | adopted |
|---|---:|---:|---:|---:|---:|---:|---|
| S1 base | 11.086 | 14.722 | 51.1% (884) | +0.68 | 54.6% (981) | +2.26 | base |
| P1 player strength (LUMA ARC, last-game availability) | 10.989 | 14.688 | 52.0% (638) | +0.94 | 55.9% (953) | +2.43 | margin, total |
| P2 3-point luck regressed | 10.952 | 14.620 | 53.2% (637) | +1.01 | 57.8% (928) | +2.60 | yes |
| P3 fatigue, travel, altitude | 10.950 | 14.607 | 54.3% (661) | +0.97 | 57.0% (940) | +2.57 | margin, total |
| P4 recent seasons weighted | 10.945 | 14.613 | 54.5% (683) | +0.93 | 56.8% (946) | +2.50 | no (total worse; sum worse) |
| P5 pace half-life 15 days | 10.950 | 14.545 | 54.7% (666) | +0.97 | 56.8% (949) | +2.76 | yes |
| diagnostic: dressed list (near tip, not bettable at the open) | 10.920 | 14.531 | 54.0% (635) | +1.42 | 57.1% (941) | +2.81 | n/a |

Closing line on these games: margin 10.643, total 14.140. Player strength was the biggest single gain on
margin. Knowing tonight's dressed list adds little on top (0.03 points of margin), so late injury news is not
where most of the remaining gap to the close is.

## Entry 8 (2026-10-27): phase 2 final spec and the one-time 2026 check (`research/out/p2_final.md`)

Spec frozen in `research/out/p2_spec.json` (P1, P2, P3, P5). 2026 scored once.

| | S1 2024 | P2 2024 | S1 2025 | P2 2025 | S1 2026 | **P2 2026 (check)** |
|---|---:|---:|---:|---:|---:|---:|
| Spreads 3+ at the opener | 47.1% (410) | 53.8% (288) | 54.3% (475) | 55.3% (378) | 51.3% (470) | **53.1% (390)** |
| Totals 4+ at the opener | 50.4% (520) | 53.2% (476) | 59.6% (463) | 60.5% (473) | 52.5% (381) | **54.8% (383)** |

All three seasons, phase 2 spec: spreads 3+ 54.1% (1,056 plays, interval 51.0-57.1%, CLV +0.74); totals 4+ 56.2%
(1,332 plays, 53.5-58.9%, CLV +2.58). 2026 alone: spreads 3+ interval 47.7-58.3%, totals 4+ 49.7-60.1%.

* The gain held on the untouched check season for both markets (+1.8 and +2.3 points of win rate).
* The model still has no information beyond the close (slopes about 0); the edge is at the opener only.
* Totals plays still lean to overs (67-79% of plays), as in S1. Not corrected here; a candidate for the next
  round, to be judged on 2024-25 the same way.

---

## Entry 9 (2026-10-27): phase 3 plan (over lean, LUMA subskills), written before any phase-3 run

**Diagnosis of the over lean** (phase 2 spec; selection seasons 2024-25 and earlier only): no overall bias at
the start of the season (model minus opener about 0 from October to February), but +2.6 points in March, +5.1 in
April and +8.2 in May (playoffs). Late-season and playoff games score less, and the model's scoring-environment
input (season average so far) lags that. Bigger edges cluster late, hence the over lean.

**Same rules as entry 6:** candidates in this order, starting from the phase 2 spec, each kept only if it
lowers the 2024-25 miss (margin MAE for margin features, total MAE for total features). Win % and the over share
of total plays are reported, not used to choose. 2026 is scored once, on the final spec. Note: 2026 was already
scored once in entry 8, so it is no longer completely fresh; it has still never been used to choose anything.

* P6 late season and playoffs: playoff/play-in flag; late-season ramp = (games played - 60) / 22, floored at 0,
  regular season only. Both stages' margin and total.
* P7 recent scoring environment: average total of the league's last 150 games before the date, minus the
  season average so far (total only).
* P8 LUMA subskills for totals: minutes-weighted sums over both teams of shooting, playmaking, ball security,
  offensive rebounding (offense) and defensive rebounding and defense (defense), same availability rule as P1.
* P9 the same six subskills as home-minus-away differences for the margin.
* P10 three-point profile for totals: sums of offensive 3-point shot selection and making (O_sel_thr,
  O_make_thr) and defensive 3-point selection allowed (D_sel_thr).

## Entry 10 (2026-10-27): phase 3 selection result, and one added candidate (written before running it)

Selection on 2024-25 (`research/out/p3_select.md`; base reproduces the phase 2 spec exactly):

| spec | margin MAE | total MAE | spreads 3+ | totals 4+ | adopted | over share | model - opener, Mar-Jun |
|---|---:|---:|---:|---:|---|---:|---:|
| phase 2 spec | 10.950 | 14.545 | 54.7% (666) | 56.8% (949) | base | 73% | +4.02 |
| P6 late season and playoffs | 10.943 | 14.459 | 54.8% (673) | 58.2% (921) | margin, total | 77% | +3.28 |
| P7 recent scoring environment | 10.943 | 14.417 | 54.8% (673) | 57.4% (853) | total | 75% | +2.65 |
| P8 subskills, totals | 10.943 | 14.417 | 54.8% (673) | 57.1% (860) | no | 74% | +2.56 |
| P9 subskills, margin | 10.944 | 14.417 | 55.0% (665) | 57.4% (853) | no | 75% | +2.65 |
| P10 three-point profile, totals | 10.943 | 14.420 | 54.8% (673) | 57.2% (867) | no | 74% | +2.64 |

LUMA subskills add nothing beyond overall ARC offense/defense. The late-season fix cut the March-June gap to the
opener from +4.0 to +2.7 points, but the model still runs 1-2 points above results from January to April
(model minus result +0.95, +1.93, +2.01, +1.72), so totals plays stay ~75% overs (overs win 55.8%, unders 62.3%).

* P11 in-season bias correction (totals): final total + k x (mean of result minus model total over the league's
  last 150 games on earlier dates, same season; 0 before 150 games). k from {0.25, 0.5, 1.0}, chosen by 2024-25
  total MAE, adopted only if it beats P7.

## Entry 11 (2026-10-27): P11 result and the phase 3 final spec (`research/out/p3_final.md`)

P11 on 2024-25: total MAE 14.417 -> 14.381 (k 0.25), **14.362 (k 0.5, adopted)**, 14.368 (k 1.0). Over share
75% -> 69%; March-June model minus opener +2.65 -> +1.60.

Final phase 3 spec = phase 2 + P6 + P7 + P11 (k 0.5); `research/out/p3_spec.json`. 2026 scored once for this
spec (its second look overall; never used to choose).

| at the opener | 2024 | 2025 | **2026 (check)** | all three | phase 2 spec, all three |
|---|---:|---:|---:|---:|---:|
| Spreads 3+ | 54.0% (287) | 55.4% (386) | **53.8% (381)** | 54.5% (1,054), 51.4-57.7% | 54.1% (1,056) |
| Totals 4+ | 56.7% (372) | 60.7% (422) | **58.9% (336)**, 53.2-64.4% | 58.8% (1,130), 55.8-61.9% | 56.2% (1,332) |
| Totals over share | 71% | 67% | 64% | | 73-79% |
| Totals CLV (pts) | +2.40 | +4.30 | +2.29 | +3.08 | +2.58 |

* Totals improved on the check season (54.8% -> 58.9%); the lean to overs is reduced, not gone (64-71%).
* Spreads essentially unchanged (53.1% -> 53.8% in 2026); none of the phase 3 inputs were aimed at spreads.
* Still no information beyond the close (slopes 0.06 total, -0.02 margin, both well inside 1 se of 0).
* Caution (CBB lesson): results near 60% in a backtest deserve suspicion. Openers in 2025-26 come from single
  books, and nothing here verifies opener timing, limits or fills.

---

## Entry 12 (2026-10-27): phase 4 plan (spreads), written before any phase-4 run

Starting point: phase 3 spec. Same rules: candidates in this order, each kept only if it lowers the 2024-25
**margin** MAE; win % at the opener reported, not used to choose; 2026 scored once on the final spec (its third
look; still never used to choose).

* M1 roster-adjusted ratings: before stage 1 fits a past game, its points per 100 are adjusted for who actually
  played: minus c x (the team's played offensive ARC minus its season-to-date typical), plus c x (the opponent's
  played defensive ARC minus its typical). Ratings then describe each team at its usual strength, and tonight's
  availability (P1 inputs) does the rest. c from {0.5, 1.0} by 2024-25 margin MAE. Played ARC uses past box
  scores only (after those games), so nothing leaks into a prediction.
* M2 team-specific home court: each team's home-minus-road residual vs the ratings over the three previous
  seasons, shrunk with 60 games of prior (CBB `team_hca_table`).
* M3 blowout down-weighting in stage 1: games decided by 20+ points count half (garbage time).
* M4 recent seasons weighted more in stage 2, margin model only (season half-life 3; in phase 2 this helped the
  margin and hurt the total, so it was dropped as a shared change).
* M5 recent form: each team's average (result minus model margin) over its last 10 games, shrunk by 10 games,
  home minus away.

## Entry 13 (2026-10-27): phase 4 results, spreads (`research/out/p4_select.md`, `p4_final.md`)

Selection, 2024-25 (adoption by margin MAE):

| spec | margin MAE | spreads 3+ win % (plays) | CLV | adopted |
|---|---:|---:|---:|---|
| phase 3 spec | 10.943 | 54.8% (673) | +0.90 | base |
| M1 roster-adjusted ratings c=0.5 | 10.977 | 55.3% (725) | +0.87 | no |
| M1 roster-adjusted ratings c=1.0 | 11.035 | 53.1% (794) | +0.69 | no |
| M2 team-specific home court | 10.940 | 54.5% (683) | +0.89 | yes |
| M3 blowouts count half | 10.944 | 55.5% (679) | +0.91 | no |
| M4 margin model weights recent seasons | 10.927 | 55.7% (731) | +0.94 | yes |
| M5 recent form | 10.930 | 55.3% (714) | +0.93 | no |

Final spec (phase 3 + M2 + M4; `research/out/p4_spec.json`), at the opener:

| spreads 3+ | 2024 | 2025 | **2026 (check)** | all three |
|---|---:|---:|---:|---:|
| phase 3 spec | 54.0% (287) | 55.4% (386) | 53.8% (381) | 54.5% (1,054) |
| phase 4 spec | 56.1% (310) | 55.3% (421) | **53.4% (384)**, 48.5-58.2% | 54.9% (1,115), 52.1-57.7% |

* The margin gains were tiny (0.016 points of MAE) and did not carry to the check season: 2026 spreads 3+ went
  from 53.8% to 53.4%. **Spreads are not meaningfully improved by phase 4.** Totals unchanged (58.9% in 2026).
* Roster-adjusting the ratings for who played made margins worse, not better. The player-strength inputs from
  phase 2 already carry the availability signal.
* The model's margin miss (10.93) is still 0.3 points behind the closing line (10.64); the remaining spread edge
  vs the opener is small (about 53-56% at 3+, interval lower bounds near 50% in any one season).

---

## Entry 14 (2026-10-27): live check of the under lean on the Oct 28 card (`research/live/under_check.py`)

All four totals plays so far are unders (LAL/POR 234.5; PHI/IND, WSH/CLE, DEN/NO 239.5). On the 52 completed
2026-27 games (live model as of each morning; ESPN's stored closes, free feed):

| | points |
|---|---:|
| average result | 229.2 |
| average model total | 228.4 (result minus model +0.8, se 2.5) |
| average closing total | 232.3 (result minus close -3.2) |
| model vs close | below the close by 4+ in 23 games, above by 4+ in 0 |
| those 23 vs the close | 14-9 |

The lean is relative to the market, not to results: so far the market has run about 3 points above what games
score, and the model about 1 below. 52 games is far too few to call either a bias (se 2.5). It mirrors the
backtest pattern in reverse: there the model ran over the opener late in the season. Nothing changed; watch it.

Injury news (ESPN injury feed, Oct 27 evening) vs the model's assumption (players from each team's last game):
* PHI/IND: Haliburton questionable (played last game, so the model counts him; out would lower IND's offense,
  pointing further under). McConnell, Zubac, Nembhard, Walker out or questionable but already absent last game.
  Line has moved 239.5 -> 237.5 toward the play.
* WSH/CLE: Champagnie out (4 minutes last game), Dybantsa questionable (has not played). CLE: none. No effect.
* DEN/NO: Cameron Johnson doubtful, S. Jones and Diallo out, all absent last game; Poole probable. No effect.
