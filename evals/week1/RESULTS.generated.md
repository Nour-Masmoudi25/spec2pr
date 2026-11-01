| Row | Agent | Tasks × runs | Pass rate | Median known cost (USD, lower bound) | Median logged steps | API error rows | Tasks solved at least once | Commit |
|---|---|---|---|---|---|---|---|---|
| 0 | Single agent | 5 × 3 | 12/15 (80.0%) | 0.004149 | 6 | 15 | 4/5 | `834104fcf4b11b687a336b0e633daa1b6948be83` |

pass^3: 80.0% (tasks passing all three repetitions).

The cost column is a lower bound, not the full billed cost. The median full cost is unknown.

Steps count trace rows; api_error_calls counts rows with unknown usage. The frozen agent does not log each internal rate-limit retry separately.
