# Vision tag check

Images: 162. Model: claude-sonnet-5-5. Date: 2026-10-15.

Each tag from the vision model is compared with the rule based tag computed from the StatsBomb event data (thresholds fixed before any comparison, in `rag/vision/summarise.py`).

| Tag | Agreement | Always predicting the most common data tag |
|---|---|---|
| passing_territory | 66% | 41% |
| pass_direction | 49% | 43% |
| pass_length | 73% | 62% |
| carrying | 72% | 86% |
| shooting | 67% | 46% |

## Confusion (rows: data tag, columns: vision tag)

### passing_territory

| tag_passing_territory   |   balanced |   mostly_final_third |   mostly_own_half |
|:------------------------|-----------:|---------------------:|------------------:|
| balanced                |         41 |                    5 |                20 |
| mostly_final_third      |         28 |                   16 |                 0 |
| mostly_own_half         |          2 |                    0 |                50 |

### pass_direction

| tag_pass_direction      |   mixed |   mostly_forward |
|:------------------------|--------:|-----------------:|
| mixed                   |      45 |               25 |
| mostly_forward          |      32 |               35 |
| mostly_sideways_or_back |      23 |                2 |

### pass_length

| tag_pass_length   |   long |   medium |   short |
|:------------------|-------:|---------:|--------:|
| long              |     14 |        5 |       0 |
| medium            |      3 |       85 |      12 |
| short             |      0 |       24 |      19 |

### carrying

| tag_carrying                 |   carries_into_final_third |   few_carries_into_final_third |
|:-----------------------------|---------------------------:|-------------------------------:|
| carries_into_final_third     |                         13 |                             10 |
| few_carries_into_final_third |                         36 |                            103 |

### shooting

| tag_shooting     |   shots_from_close |   shots_from_range |   shots_mixed |   too_few_shots |
|:-----------------|-------------------:|-------------------:|--------------:|----------------:|
| shots_from_close |                 32 |                  0 |             0 |               3 |
| shots_from_range |                 13 |                  1 |             2 |               6 |
| shots_mixed      |                 28 |                  0 |             0 |               2 |
| too_few_shots    |                  0 |                  0 |             0 |              75 |
