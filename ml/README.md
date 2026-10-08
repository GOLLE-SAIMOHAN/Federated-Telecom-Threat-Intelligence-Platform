# Python machine-learning layer

Phase 2 provides the reusable 5G-NIDD data pipeline in
[`ml/data/pipeline.py`](data/pipeline.py). The actual downloaded dataset must
be placed at `data/raw/5g-nidd` (or configured in `configs/dataset.json`).

The pipeline requires the real label column to be set in
`configs/dataset.json` after inspection. It does not assume or invent column
names, labels, class distributions, or statistics.

Run inspection after placing the dataset and setting `label_column`:

```powershell
python -m ml.data.inspect_dataset --config configs/dataset.json
```
