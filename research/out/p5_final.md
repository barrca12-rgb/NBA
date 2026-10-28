# Phase 5 final: check season 2026 and betting scorecards 2024-2026

- phase 4 spec: accuracy 2015-2025 margin 10.262 / total 14.375; 2026 check margin 11.343 / total 14.672
- phase 5 spec: accuracy 2015-2025 margin 10.249 / total 14.376; 2026 check margin 11.304 / total 14.675

# Phase 5 spec at the opener

Suspect spread records excluded (opener favors the other team from the model by 10+): 17 (2024: 1, 2025: 10, 2026: 6).

## 1. Accuracy vs the closing line

| sample | games | model margin MAE | close margin MAE | model total MAE | close total MAE |
|---|---:|---:|---:|---:|---:|
| 2024-2025 | 2,639 | 10.90 | 10.64 | 14.36 | 14.14 |
| check 2026 | 1,322 | 11.30 | 11.01 | 14.68 | 14.51 |
| all three 2024-2026 | 3,961 | 11.04 | 10.76 | 14.47 | 14.26 |

## 2. Beyond the close: OLS of (result - close) on (model - close), date-clustered SE

| sample | margin slope (se) | total slope (se) |
|---|---:|---:|
| 2024-2025 | 0.092 (0.088) | 0.071 (0.091) |
| check 2026 | 0.010 (0.107) | 0.027 (0.141) |
| all three 2024-2026 | 0.063 (0.068) | 0.056 (0.077) |

## 3-4. At the opener: win %, ROI at -110, 95% date-bootstrap interval, opener CLV

| market | edge | sample | plays | win % | 95% interval | ROI | CLV (pts) |
|---|---|---|---:|---:|---|---:|---:|
| spread | 2+ | 2024-2025 | 1,188 | 53.4% | 50.5% - 56.4% | +1.9% | +0.73 |
| spread | 2+ | check 2026 | 634 | 53.0% | 48.9% - 56.7% | +1.2% | +0.42 |
| spread | 2+ | all three 2024-2026 | 1,822 | 53.2% | 50.9% - 55.6% | +1.6% | +0.63 |
| spread | 3+ | 2024-2025 | 736 | 55.8% | 52.1% - 59.7% | +6.6% | +0.98 |
| spread | 3+ | check 2026 | 366 | 54.4% | 49.2% - 59.5% | +3.8% | +0.52 |
| spread | 3+ | all three 2024-2026 | 1,102 | 55.4% | 52.2% - 58.4% | +5.7% | +0.83 |
| spread | 4+ | 2024-2025 | 401 | 60.1% | 55.4% - 65.1% | +14.7% | +1.42 |
| spread | 4+ | check 2026 | 215 | 55.3% | 48.9% - 61.9% | +5.7% | +0.55 |
| spread | 4+ | all three 2024-2026 | 616 | 58.4% | 54.6% - 62.4% | +11.6% | +1.12 |
| total | 3+ | 2024-2025 | 1,140 | 56.6% | 53.6% - 59.6% | +8.0% | +2.87 |
| total | 3+ | check 2026 | 516 | 57.4% | 53.2% - 61.6% | +9.5% | +2.04 |
| total | 3+ | all three 2024-2026 | 1,656 | 56.8% | 54.1% - 59.3% | +8.5% | +2.61 |
| total | 4+ | 2024-2025 | 780 | 59.7% | 56.3% - 63.2% | +14.1% | +3.43 |
| total | 4+ | check 2026 | 340 | 58.5% | 52.6% - 64.0% | +11.7% | +2.30 |
| total | 4+ | all three 2024-2026 | 1,120 | 59.4% | 56.4% - 62.4% | +13.4% | +3.08 |
| total | 5+ | 2024-2025 | 516 | 60.7% | 56.2% - 64.9% | +15.8% | +4.18 |
| total | 5+ | check 2026 | 204 | 62.3% | 54.5% - 69.5% | +18.9% | +3.11 |
| total | 5+ | all three 2024-2026 | 720 | 61.1% | 57.3% - 64.6% | +16.7% | +3.87 |

Opener scorecards use only seasons that have openers.

## Per season, phase 4 vs phase 5

| spec | margin MAE | total MAE | spreads 3+ win % (plays) | CLV | totals 4+ win % (plays) | CLV | adopted | over share | model - opener, Mar-Jun |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| phase 4 spec 2024 | 10.875 | 14.338 | 56.1% (310) | +0.51 | 56.7% (372) | +2.40 |  71% | +1.70 |
| phase 4 spec 2025 | 10.978 | 14.386 | 55.3% (421) | +1.26 | 60.7% (422) | +4.30 |  67% | +1.51 |
| phase 4 spec 2026 | 11.343 | 14.672 | 53.4% (384) | +0.47 | 58.9% (336) | +2.29 |  64% | +1.55 |
| phase 5 spec 2024 | 10.873 | 14.340 | 53.3% (315) | +0.64 | 57.1% (359) | +2.42 |  70% | +1.62 |
| phase 5 spec 2025 | 10.936 | 14.388 | 57.7% (421) | +1.24 | 62.0% (421) | +4.29 |  66% | +1.45 |
| phase 5 spec 2026 | 11.304 | 14.675 | 54.4% (366) | +0.52 | 58.5% (340) | +2.30 |  62% | +1.50 |
