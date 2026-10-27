# Phase 4 final spec

Suspect spread records excluded (opener favors the other team from the model by 10+): 18 (2024: 1, 2025: 11, 2026: 6).

## 1. Accuracy vs the closing line

| sample | games | model margin MAE | close margin MAE | model total MAE | close total MAE |
|---|---:|---:|---:|---:|---:|
| selection 2024-2025 | 2,639 | 10.93 | 10.64 | 14.36 | 14.14 |
| check 2026 | 1,322 | 11.34 | 11.01 | 14.67 | 14.51 |
| all three 2024-2026 | 3,961 | 11.07 | 10.76 | 14.47 | 14.26 |

## 2. Beyond the close: OLS of (result - close) on (model - close), date-clustered SE

| sample | margin slope (se) | total slope (se) |
|---|---:|---:|
| selection 2024-2025 | 0.054 (0.087) | 0.071 (0.091) |
| check 2026 | -0.036 (0.107) | 0.036 (0.141) |
| all three 2024-2026 | 0.022 (0.068) | 0.059 (0.077) |

## 3-4. At the opener: win %, ROI at -110, 95% date-bootstrap interval, opener CLV

| market | edge | sample | plays | win % | 95% interval | ROI | CLV (pts) |
|---|---|---|---:|---:|---|---:|---:|
| spread | 2+ | selection 2024-2025 | 1,183 | 52.8% | 50.1% - 55.7% | +0.9% | +0.65 |
| spread | 2+ | check 2026 | 631 | 51.0% | 47.4% - 54.7% | -2.6% | +0.40 |
| spread | 2+ | all three 2024-2026 | 1,814 | 52.2% | 49.8% - 54.5% | -0.3% | +0.56 |
| spread | 3+ | selection 2024-2025 | 731 | 55.7% | 52.0% - 59.5% | +6.3% | +0.94 |
| spread | 3+ | check 2026 | 384 | 53.4% | 48.5% - 58.2% | +1.9% | +0.47 |
| spread | 3+ | all three 2024-2026 | 1,115 | 54.9% | 52.1% - 57.7% | +4.8% | +0.78 |
| spread | 4+ | selection 2024-2025 | 384 | 56.0% | 50.9% - 60.8% | +6.9% | +1.31 |
| spread | 4+ | check 2026 | 219 | 53.9% | 47.7% - 60.0% | +2.9% | +0.55 |
| spread | 4+ | all three 2024-2026 | 603 | 55.2% | 51.1% - 59.2% | +5.4% | +1.04 |
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
| 2024 | 10.875 | 14.338 | 56.1% (310) | +0.51 | 56.7% (372) | +2.40 |  71% | +1.70 |
| 2025 | 10.978 | 14.386 | 55.3% (421) | +1.26 | 60.7% (422) | +4.30 |  67% | +1.51 |
| 2026 | 11.343 | 14.672 | 53.4% (384) | +0.47 | 58.9% (336) | +2.29 |  64% | +1.55 |
