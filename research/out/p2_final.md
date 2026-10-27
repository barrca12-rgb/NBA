# Phase 2 final spec

Suspect spread records excluded (opener favors the other team from the model by 10+): 18 (2024: 2, 2025: 10, 2026: 6).

## 1. Accuracy vs the closing line

| sample | games | model margin MAE | close margin MAE | model total MAE | close total MAE |
|---|---:|---:|---:|---:|---:|
| selection 2024-2025 | 2,639 | 10.95 | 10.64 | 14.55 | 14.14 |
| check 2026 | 1,322 | 11.34 | 11.01 | 14.77 | 14.51 |
| all three 2024-2026 | 3,961 | 11.08 | 10.76 | 14.62 | 14.26 |

## 2. Beyond the close: OLS of (result - close) on (model - close), date-clustered SE

| sample | margin slope (se) | total slope (se) |
|---|---:|---:|
| selection 2024-2025 | -0.005 (0.088) | 0.054 (0.077) |
| check 2026 | -0.052 (0.106) | 0.029 (0.125) |
| all three 2024-2026 | -0.022 (0.068) | 0.047 (0.066) |

## 3-4. At the opener: win %, ROI at -110, 95% date-bootstrap interval, opener CLV

| market | edge | sample | plays | win % | 95% interval | ROI | CLV (pts) |
|---|---|---|---:|---:|---|---:|---:|
| spread | 2+ | selection 2024-2025 | 1,148 | 52.8% | 49.8% - 55.8% | +0.8% | +0.71 |
| spread | 2+ | check 2026 | 630 | 52.4% | 48.5% - 56.5% | +0.0% | +0.38 |
| spread | 2+ | all three 2024-2026 | 1,778 | 52.6% | 50.2% - 55.1% | +0.5% | +0.59 |
| spread | 3+ | selection 2024-2025 | 666 | 54.7% | 51.0% - 58.5% | +4.3% | +0.97 |
| spread | 3+ | check 2026 | 390 | 53.1% | 47.7% - 58.3% | +1.3% | +0.36 |
| spread | 3+ | all three 2024-2026 | 1,056 | 54.1% | 51.0% - 57.1% | +3.2% | +0.74 |
| spread | 4+ | selection 2024-2025 | 360 | 57.2% | 51.4% - 62.7% | +9.2% | +1.35 |
| spread | 4+ | check 2026 | 205 | 54.1% | 47.2% - 60.5% | +3.4% | +0.44 |
| spread | 4+ | all three 2024-2026 | 565 | 56.1% | 51.8% - 60.5% | +7.1% | +1.02 |
| total | 3+ | selection 2024-2025 | 1,288 | 55.7% | 52.9% - 58.5% | +6.4% | +2.33 |
| total | 3+ | check 2026 | 553 | 55.5% | 51.1% - 59.9% | +6.0% | +1.75 |
| total | 3+ | all three 2024-2026 | 1,841 | 55.7% | 53.2% - 57.9% | +6.3% | +2.16 |
| total | 4+ | selection 2024-2025 | 949 | 56.8% | 53.7% - 60.0% | +8.4% | +2.76 |
| total | 4+ | check 2026 | 383 | 54.8% | 49.7% - 60.1% | +4.7% | +2.11 |
| total | 4+ | all three 2024-2026 | 1,332 | 56.2% | 53.5% - 58.9% | +7.4% | +2.58 |
| total | 5+ | selection 2024-2025 | 695 | 58.1% | 54.5% - 62.0% | +11.0% | +3.11 |
| total | 5+ | check 2026 | 262 | 56.5% | 50.7% - 62.5% | +7.8% | +2.26 |
| total | 5+ | all three 2024-2026 | 957 | 57.7% | 54.5% - 61.0% | +10.1% | +2.88 |

Opener scorecards use only seasons that have openers.
