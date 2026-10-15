---
note_id: shortlist_method
kind: method_report
title: How the top 100 shortlist works
author: draft generated from repo data
written: 2026-10-15
season: 2025/26
leagues: []
player_ids: []
---
# How the top 100 shortlist works

Draft written 2026-10-15. The shortlist is produced by `python -m src.shortlist`.

1. The pre transfer models were trained on 1,669 moves from nine European leagues into the top five (see the README). The best model on validation data was a small PyTorch network.
2. For each current player in a source league the model gives a probability of becoming a regular starter within two seasons after a move, averaged over the five destination leagues.
3. The shortlist score is the percentile rank of that probability minus the percentile rank of market value inside the league. High probability and low value rank first.
4. Only players aged 30 or under with at least 450 minutes in the last 365 days are eligible.

Limits: on the test moves the models only modestly beat a simple rule based on minutes played, and market value is Transfermarkt's own estimate. The shortlist is a place to start a conversation, not a verdict that a player is undervalued.
