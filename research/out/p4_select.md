# Phase 4 selection (seasons 2024 and 2025 only; adoption by margin MAE)

| spec | margin MAE | total MAE | spreads 3+ win % (plays) | CLV | totals 4+ win % (plays) | CLV | adopted | over share | model - opener, Mar-Jun |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| phase 3 spec | 10.943 | 14.362 | 54.8% (673) | +0.90 | 58.8% (794) | +3.41 | base 69% | +1.60 |
| M1 roster-adjusted ratings c=0.5 | 10.977 | 14.358 | 55.3% (725) | +0.87 | 59.0% (805) | +3.31 |  67% | +1.63 |
| M1 roster-adjusted ratings c=1.0 | 11.035 | 14.368 | 53.1% (794) | +0.69 | 58.3% (829) | +3.21 |  67% | +1.65 |
| M2 team-specific home court | 10.940 | 14.362 | 54.5% (683) | +0.89 | 58.8% (794) | +3.41 | yes 69% | +1.60 |
| M3 blowouts count half in stage 1 | 10.944 | 14.393 | 55.5% (679) | +0.91 | 57.9% (788) | +3.43 | no 66% | +1.54 |
| M4 margin model weights recent seasons (half-life 3) | 10.927 | 14.362 | 55.7% (731) | +0.94 | 58.8% (794) | +3.41 | yes 69% | +1.60 |
| M5 recent form | 10.930 | 14.362 | 55.3% (714) | +0.93 | 58.8% (794) | +3.41 | no 69% | +1.60 |

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
 "hook": null,
 "adopted_phase4": [
  "M2 team-specific home court",
  "M4 margin model weights recent seasons (half-life 3)"
 ]
}
```
