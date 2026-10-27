# Phase 3 selection (seasons 2024 and 2025 only)

| spec | margin MAE | total MAE | spreads 3+ win % (plays) | CLV | totals 4+ win % (plays) | CLV | adopted | over share | model - opener, Mar-Jun |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| phase 2 spec | 10.950 | 14.545 | 54.7% (666) | +0.97 | 56.8% (949) | +2.76 | base 73% | +4.02 |
| P6 late season and playoffs | 10.943 | 14.459 | 54.8% (673) | +0.90 | 58.2% (921) | +2.86 | margin, total 77% | +3.28 |
| P7 recent scoring environment | 10.943 | 14.417 | 54.8% (673) | +0.90 | 57.4% (853) | +3.05 | total 75% | +2.65 |
| P8 subskills, totals | 10.943 | 14.417 | 54.8% (673) | +0.90 | 57.1% (860) | +3.09 | no 74% | +2.56 |
| P9 subskills, margin | 10.944 | 14.417 | 55.0% (665) | +0.93 | 57.4% (853) | +3.05 | no 75% | +2.65 |
| P10 three-point profile, totals | 10.943 | 14.420 | 54.8% (673) | +0.90 | 57.2% (867) | +3.03 | no 74% | +2.64 |

Adopted spec:

```
{
 "cfg": {
  "half_life": 30.0,
  "prior_games": 10.0,
  "pace_prior_games": 10.0,
  "carry": 0.5,
  "hca_prior": 1.5,
  "pace_half_life": 15.0,
  "ppp_col": "ppp_luck"
 },
 "margin": [
  "pred_margin",
  "pred_margin_x_early",
  "venue",
  "home_b2b",
  "away_b2b",
  "rest_diff",
  "avail_diff",
  "avail_diff_x_early",
  "miss_diff",
  "fatigue_3in4_diff",
  "g7_diff",
  "tz_diff",
  "altitude",
  "playoff",
  "late"
 ],
 "total": [
  "pred_total",
  "pred_total_x_early",
  "season_avg_total",
  "b2b_sum",
  "rest_sum",
  "avail_O_sum",
  "avail_D_sum",
  "miss_O_sum",
  "miss_D_sum",
  "fatigue_3in4_sum",
  "g7_sum",
  "tz_sum",
  "altitude",
  "playoff",
  "late",
  "recent_dev"
 ],
 "walk_forward": {},
 "adopted": [
  "P6 late season and playoffs",
  "P7 recent scoring environment"
 ]
}
```
