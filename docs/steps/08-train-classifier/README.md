# Step 8: Train the ML Classifier (Milestone 6)

Train Random Forest, MLP, and SVM classifiers on the labeled port statistics
dataset and evaluate using Accuracy, Precision, Recall, and F-Measure — the
metrics from Table III of the paper.

The trained Random Forest model is saved to `data/model.pkl` for use by the
Threat Detection and Localization modules (Milestones 7 and 8).

## Prerequisites

Step 7 must be complete:

```
data/train.csv
data/test.csv
```

## Run

```bash
python3 simulation/train_classifier.py
```

With explicit paths:

```bash
python3 simulation/train_classifier.py \
  --train data/train.csv \
  --test data/test.csv \
  --model-out data/model.pkl \
  --results-out data/results.json
```

## Expected output

```
  TABLE III — Classifier performance
==================================================
  Classifier             Accuracy  Precision     Recall  F-Measure
  ──────────────────────────────────────────────────────────────────
  Random Forest           99.342%    99.342%    99.342%    99.342%
  MLP                     51.409%    51.409%    51.409%    51.409%
  Support Vector Machine  97.852%    97.852%    97.852%    97.852%
```

Numbers will vary based on your collected data, but Random Forest should
outperform MLP and SVM — consistent with Table III of the paper.

## Output files

| File | Description |
|------|-------------|
| `data/model.pkl` | Trained Random Forest model (pickle) — used by Milestones 7 & 8 |
| `data/results.json` | Accuracy, Precision, Recall, F-Measure for all three classifiers |

## Verify

```bash
python3 - <<'EOF'
import pickle, pandas as pd
from simulation.build_dataset import FEATURE_COLS

model = pickle.load(open("data/model.pkl", "rb"))
df = pd.read_csv("data/test.csv")
preds = model.predict(df[FEATURE_COLS])
print("Prediction counts:", dict(zip(*[v.tolist() for v in __import__('numpy').unique(preds, return_counts=True)])))
print("Classes:", model.classes_)
EOF
```

Next step:
- `../09-threat-detection/README.md` (Milestone 7: real-time threat detection with port threshold Φ)
