# Phase 3 final spec

Suspect spread records excluded (opener favors the other team from the model by 10+): 17 (2024: 1, 2025: 10, 2026: 6).

## 1. Accuracy vs the closing line

| sample | games | model margin MAE | close margin MAE | model total MAE | close total MAE |
|---|---:|---:|---:|---:|---:|
| selection 2024-2025 | 2,639 | 10.94 | 10.64 | 14.36 | 14.14 |
| check 2026 | 1,322 | 11.34 | 11.01 | 14.67 | 14.51 |
| all three 2024-2026 | 3,961 | 11.08 | 10.76 | 14.47 | 14.26 |

## 2. Beyond the close: OLS of (result - close) on (model - close), date-clustered SE

| sample | margin slope (se) | total slope (se) |
|---|---:|---:|
| selection 2024-2025 | 0.015 (0.088) | 0.071 (0.091) |
| check 2026 | -0.069 (0.106) | 0.036 (0.141) |
| all three 2024-2026 | -0.016 (0.068) | 0.059 (0.077) |

## 3-4. At the opener: win %, ROI at -110, 95% date-bootstrap interval, opener CLV

| market | edge | sample | plays | win % | 95% interval | ROI | CLV (pts) |
|---|---|---|---:|---:|---|---:|---:|
| spread | 2+ | selection 2024-2025 | 1,148 | 53.0% | 49.9% - 55.9% | +1.1% | +0.70 |
| spread | 2+ | check 2026 | 629 | 52.3% | 48.2% - 56.5% | -0.1% | +0.37 |
| spread | 2+ | all three 2024-2026 | 1,777 | 52.7% | 50.2% - 55.3% | +0.7% | +0.58 |
| spread | 3+ | selection 2024-2025 | 673 | 54.8% | 51.0% - 58.8% | +4.7% | +0.90 |
| spread | 3+ | check 2026 | 381 | 53.8% | 48.7% - 58.8% | +2.7% | +0.31 |
| spread | 3+ | all three 2024-2026 | 1,054 | 54.5% | 51.4% - 57.7% | +4.0% | +0.69 |
| spread | 4+ | selection 2024-2025 | 361 | 56.2% | 50.5% - 61.7% | +7.4% | +1.33 |
| spread | 4+ | check 2026 | 199 | 52.8% | 46.1% - 59.7% | +0.7% | +0.49 |
| spread | 4+ | all three 2024-2026 | 560 | 55.0% | 50.7% - 59.6% | +5.0% | +1.03 |
| total | 3+ | selection 2024-2025 | 1,139 | 56.9% | 53.7% - 59.9% | +8.6% | +2.85 |
| total | 3+ | check 2026 | 520 | 57.5% | 53.3% - 61.6% | +9.8% | +2.02 |
| total | 3+ | all three 2024-2026 | 1,659 | 57.1% | 54.6% - 59.5% | +9.0% | +2.59 |
| total | 4+ | selection 2024-2025 | 794 | 58.8% | 55.3% - 62.3% | +12.3% | +3.41 |
| total | 4+ | check 2026 | 336 | 58.9% | 53.2% - 64.4% | +12.5% | +2.29 |
| total | 4+ | all three 2024-2026 | 1,130 | 58.8% | 55.8% - 61.9% | +12.3% | +3.08 |
| total | 5+ | selection 2024-2025 | 521 | 60.3% | 56.1% - 64.6% | +15.1% | +4.16 |
| total | 5+ | check 2026 | 209 | 60.3% | 53.2% - 67.6% | +15.1% | +3.08 |
| total | 5+ | all three 2024-2026 | 730 | 60.3% | 56.7% - 63.8% | +15.1% | +3.85 |

Opener scorecards use only seasons that have openers.

## By season

| spec | margin MAE | total MAE | spreads 3+ win % (plays) | CLV | totals 4+ win % (plays) | CLV | adopted | over share | model - opener, Mar-Jun |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 2024 | 10.904 | 14.338 | 54.0% (287) | +0.40 | 56.7% (372) | +2.40 |  71% | +1.70 |
| 2025 | 10.982 | 14.386 | 55.4% (386) | +1.27 | 60.7% (422) | +4.30 |  67% | +1.51 |
| 2026 | 11.341 | 14.672 | 53.8% (381) | +0.31 | 58.9% (336) | +2.29 |  64% | +1.55 |
