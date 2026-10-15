# Step 2 results

Run date: 2026-10-15. Snapshot: Transfermarkt 2026-07-06.

Pre transfer records: 1669 (train 694, validation 246, test 333, embargo 396 not used).
Test regular starter rate: 30.9%.

| model | precision | recall | ROC AUC | AUC 95% CI (bootstrap) |
|---|---|---|---|---|
| baseline_prior | 0.309 | 1.000 | 0.500 | 0.500 to 0.500 |
| baseline_minutes | 0.398 | 0.816 | 0.706 | 0.646 to 0.764 |
| logistic_regression | 0.469 | 0.670 | 0.737 | 0.679 to 0.794 |
| gradient_boosting | 0.490 | 0.718 | 0.745 | 0.686 to 0.798 |
| pytorch_mlp | 0.462 | 0.757 | 0.740 | 0.682 to 0.796 |

Selected hyperparameters (by validation ROC AUC):

- baseline_prior: {"prior": 0.326}
- baseline_minutes: {"rule": "minutes_365 / 3400"}
- logistic_regression: {"C": 0.01}
- gradient_boosting: {"learning_rate": 0.03, "max_depth": 2, "n_estimators": 100}
- pytorch_mlp: {"hidden": [32, 16], "dropout": 0.4, "weight_decay": 0.01, "epochs_run": 47}
