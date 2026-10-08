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

This file must contain only measured results from actual executions. Do not
add placeholder metrics, fabricated distributions, or simulated outcomes.
