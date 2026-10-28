# Phase 5 selection (accuracy on 2015-2025, about 12,000 games)

| spec | margin MAE | total MAE | games | adopted | note |
|---|---:|---:|---:|---|---|
| phase 4 spec | 10.2618 | 14.3750 | 14,149 | base |  |
| T1 early-season level (totals) | 10.2618 | 14.3760 | 14,149 | no |  |
| T2 possessions x early, efficiency x early (totals) | 10.2618 | 14.3770 | 14,149 | no |  |
| S1 half_life=20 | 10.2708 | 14.3764 | 14,149 | no |  |
| S1 half_life=45 | 10.2614 | 14.3815 | 14,149 | no |  |
| S1 half_life=60 | 10.2638 | 14.3893 | 14,149 | no |  |
| S1 prior_games=5 | 10.2646 | 14.3765 | 14,149 | no |  |
| S1 prior_games=15 | 10.2625 | 14.3831 | 14,149 | no |  |
| S1 prior_games=20 | 10.2651 | 14.3928 | 14,149 | no |  |
| S1 carry=0.3 | 10.2617 | 14.3811 | 14,149 | no |  |
| S1 carry=0.7 | 10.2648 | 14.3792 | 14,149 | no |  |
| S1 pace_half_life=8 | 10.2620 | 14.3911 | 14,149 | no |  |
| S1 pace_half_life=30 | 10.2618 | 14.3934 | 14,149 | no |  |
| R1 preseason LOKI for unrated players | 10.7035 | 14.4069 | 5,283 | yes | scored on 2022-2025 (base on these seasons: 10.7380 / 14.4030) |

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
  "late",
  "team_hca"
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
 "walk_forward": {
  "margin_half_life": 3.0
 },
 "adopted": [
  "P6 late season and playoffs",
  "P7 recent scoring environment"
 ],
 "bias_k": 0.5,
 "loki_pre": true,
 "adopted_phase5": [
  "R1 preseason LOKI for unrated players"
 ]
}
```
