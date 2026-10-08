# Experiment Log

## Phase 3 centralized baseline

- Model: `sklearn.linear_model.SGDClassifier`
- Loss: `log_loss`
- Class weighting: `balanced`
- Random state: `42`
- Training data: leakage-free IID operator partitions
- Evaluation data: untouched test set using the saved Phase 2 preprocessing
- Training time: `11.064863399980823` seconds
- Evaluation time: `0.17126790000475012` seconds
- Accuracy: `0.9821741116568888`
- Weighted precision: `0.9974889424043196`
- Weighted recall: `0.9821741116568888`
- Weighted F1: `0.9888945377079611`
- Macro-F1: `0.4531986011347878`

Detailed per-class metrics and the confusion matrix are saved in
`data/processed/centralized_baseline_results.json`.

## Phase 4 federated learning

- Framework: `Flower 1.17.0`
- Model: `sklearn.linear_model.SGDClassifier(loss="log_loss")`
- Clients: four (`Operator A`, `Operator B`, `Operator C`, `Operator D`)
- Partition mode: IID
- Rounds: `3`
- Random state: `42`
- Client sample counts: `144348`, `144346`, `144342`, `144339`
- Training time across rounds: `5.325679100002162` seconds
- Evaluation data: untouched test set using the saved Phase 2 preprocessing
- Accuracy: `0.9680848333666959`
- Weighted precision: `0.9939677095533188`
- Weighted recall: `0.9680848333666959`
- Weighted F1: `0.9806707802878049`
- Macro-F1: `0.44836304820179085`
- Aggregation: Flower FedAvg weighted by client sample count
- Exchanged model arrays: `coef_`, `intercept_` (`2520` bytes per round)

The complete round history and final metrics are saved in
`data/processed/federated_iid_report.json`.

This file must contain only measured results from actual executions. Do not
add placeholder metrics, fabricated distributions, or simulated outcomes.
