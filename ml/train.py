"""Train + evaluate. Usage: python -m ml.train [--csv data/reviews.csv] [--out models]"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

from .detector import FakeReviewDetector
from .features import build_features
from .trust import compute_trust_scores


def _metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    return {"accuracy": accuracy_score(y, pred), "precision": precision_score(y, pred),
            "recall": recall_score(y, pred), "f1": f1_score(y, pred),
            "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "confusion_matrix": confusion_matrix(y, pred).tolist()}


def main(csv="data/reviews.csv", out="models", seed=42):
    df = pd.read_csv(csv)
    y = df["is_fake"].astype(int).values
    feats = build_features(df)
    idx_tr, idx_te = train_test_split(np.arange(len(df)), test_size=0.25, stratify=y, random_state=seed)
    Xtr, Xte = feats.iloc[idx_tr], feats.iloc[idx_te]

    results, models = {}, {}
    for mode in ("text", "behavior", "dual"):
        det = FakeReviewDetector(mode=mode, random_state=seed).fit(Xtr, y[idx_tr])
        results[mode] = _metrics(y[idx_te], det.predict_proba(Xte))
        models[mode] = det
        m = results[mode]
        print(f"[{mode:8s}] acc={m['accuracy']:.3f} prec={m['precision']:.3f} rec={m['recall']:.3f} "
              f"f1={m['f1']:.3f} auc={m['roc_auc']:.3f}")

    # permutation importance for the dual model
    dual = models["dual"]
    pi = permutation_importance(dual.meta, dual._matrix(Xte), y[idx_te], n_repeats=5,
                                random_state=seed, scoring="roc_auc")
    top = sorted(zip(dual.columns_, pi.importances_mean), key=lambda t: -t[1])[:12]

    # trust-score sanity check on the held-out evaluation of the full dataset
    final = FakeReviewDetector(mode="dual", random_state=seed).fit(feats, y)
    proba = final.predict_proba(feats)
    ts = compute_trust_scores(df.assign(fake_prob=proba))
    true_clean = df[df.is_fake == 0].groupby("product_id")["rating"].mean()
    ts = ts.set_index("product_id")
    ts["true_clean_avg"] = true_clean
    err_raw = (ts["raw_avg"] - ts["true_clean_avg"]).abs().mean()
    err_ver = (ts["verified_avg"] - ts["true_clean_avg"]).abs().mean()
    print(f"\nMean |rating error| vs true genuine average: raw={err_raw:.3f}  verified={err_ver:.3f}")

    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    final.save(out / "fake_review_detector.joblib")
    report = {"holdout": results, "top_features": [(n, round(float(v), 4)) for n, v in top],
              "trust_rating_error": {"raw": round(float(err_raw), 3), "verified": round(float(err_ver), 3)},
              "n_reviews": int(len(df)), "fake_rate": round(float(y.mean()), 3)}
    (out / "metrics.json").write_text(json.dumps(report, indent=2))
    print("\nTop features:", ", ".join(f"{n}({v:.3f})" for n, v in top[:8]))
    print(f"Saved model + metrics to {out}/")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/reviews.csv")
    ap.add_argument("--out", default="models")
    a = ap.parse_args()
    main(a.csv, a.out)
