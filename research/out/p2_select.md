# Phase 2 selection (seasons 2024 and 2025 only)

Closing line on these games: margin MAE 10.643, total MAE 14.140.

| spec | margin MAE | total MAE | spreads 3+ win % (plays) | CLV | totals 4+ win % (plays) | CLV | adopted |
|---|---:|---:|---:|---:|---:|---:|---|
| S1 base (trained from 2014) | 11.086 | 14.722 | 51.1% (884) | +0.68 | 54.6% (981) | +2.26 | base |
| P1 player strength | 10.989 | 14.688 | 52.0% (638) | +0.94 | 55.9% (953) | +2.43 | margin, total |
| P2 3-point luck regressed | 10.952 | 14.620 | 53.2% (637) | +1.01 | 57.8% (928) | +2.60 | yes |
| P3 fatigue, travel, altitude | 10.950 | 14.607 | 54.3% (661) | +0.97 | 57.0% (940) | +2.57 | margin, total |
| P4 recent seasons weighted (half-life 3) | 10.945 | 14.613 | 54.5% (683) | +0.93 | 56.8% (946) | +2.50 | no |
| P5 pace half-life 15 days | 10.950 | 14.545 | 54.7% (666) | +0.97 | 56.8% (949) | +2.76 | yes |
| diagnostic: dressed list (known near tip, not at the open) | 10.920 | 14.531 | 54.0% (635) | +1.42 | 57.1% (941) | +2.81 | n/a |

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
  "altitude"
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
  "altitude"
 ],
 "walk_forward": {},
 "adopted": [
  "P1 player strength",
  "P2 3-point luck regressed",
  "P3 fatigue, travel, altitude",
  "P5 pace half-life 15 days"
 ]
}
```
