"""Supervised fake-review detector.

Architecture ("dual-feature stacking"):
  1. Text model  : TF-IDF (1-2 grams) + Logistic Regression -> out-of-fold P(fake | text)
  2. Meta model  : Gradient boosting over [behavioural features + NLP stylometry
                   + text_prob + sentiment/rating gap] -> final P(fake)
`mode` lets you ablate: "text", "behavior" or "dual" (default, the innovation).
"""
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from .features import BEHAVIOR_COLS, CROSS_COLS, TEXT_COLS


def _text_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, strip_accents="unicode")),
        ("lr", LogisticRegression(C=3.0, max_iter=1000)),
    ])


class FakeReviewDetector:
    def __init__(self, mode="dual", threshold=0.5, random_state=42):
        assert mode in {"text", "behavior", "dual"}
        self.mode, self.threshold, self.random_state = mode, threshold, random_state
        self.base_cols = {
            "text": TEXT_COLS,
            "behavior": BEHAVIOR_COLS,
            "dual": BEHAVIOR_COLS + TEXT_COLS + CROSS_COLS,
        }[mode]
        self.use_text = mode in {"text", "dual"}
        self.text_model = None
        self.meta = None

    # -------------------------------------------------------------- training
    def fit(self, feats, y):
        y = np.asarray(y).astype(int)
        X = feats[self.base_cols].copy()
        if self.use_text:
            cv = StratifiedKFold(5, shuffle=True, random_state=self.random_state)
            X["text_prob"] = cross_val_predict(
                _text_model(), feats["clean_text"], y, cv=cv, method="predict_proba")[:, 1]
            self.text_model = _text_model().fit(feats["clean_text"], y)
        self.meta = HistGradientBoostingClassifier(
            max_iter=250, learning_rate=0.06, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=self.random_state).fit(X, y)
        self.columns_ = list(X.columns)
        return self

    # ------------------------------------------------------------- inference
    def _matrix(self, feats):
        X = feats[self.base_cols].copy()
        if self.use_text:
            X["text_prob"] = self.text_model.predict_proba(feats["clean_text"])[:, 1]
        return X[self.columns_]

    def predict_proba(self, feats):
        return self.meta.predict_proba(self._matrix(feats))[:, 1]

    def predict(self, feats):
        return (self.predict_proba(feats) >= self.threshold).astype(int)

    # ---------------------------------------------------------- explanations
    @staticmethod
    def explain_row(r, max_reasons=4):
        out = []
        if r["is_new_account"] and r["account_age_days"] < 14:
            d = int(r["account_age_days"])
            out.append(f"Very new account ({d} day{'s' if d != 1 else ''} old)")
        if r["user_reviews_per_month"] > 6 and r["user_review_count"] >= 4:
            out.append(f"High posting velocity ({r['user_reviews_per_month']:.1f} reviews/month)")
        if r["dup_text_count"] > 0:
            out.append(f"Near-identical text appears {int(r['dup_text_count'])} other time(s)")
        if r["generic_hits"] >= 2 or (r["generic_hits"] >= 1 and r["is_extreme"] and r["aspect_hits"] == 0):
            out.append("Generic, templated superlative language")
        if r["is_extreme"] and r["n_words"] <= 12 and r["specificity"] == 0 and r["aspect_hits"] == 0:
            out.append("Short extreme rating with no specifics")
        if r["sentiment_rating_gap"] > 1.0:
            out.append("Text sentiment contradicts the star rating")
        if r["is_extreme"] and r["product_abs_dev"] >= 2:
            out.append("Extreme rating far from the movie's consensus")
        if r["user_extreme_share"] >= 0.9 and r["user_review_count"] >= 3:
            out.append("Account posts almost only 1★/5★ reviews")
        if r["product_new_acct_share"] > 0.5 and r["is_new_account"]:
            out.append("Movie is receiving a burst of reviews from new accounts")
        if r["ip_review_count"] >= 5 or r["device_review_count"] >= 5:
            out.append("Many reviews from the same IP/device")
        return out[:max_reasons]

    def explain_frame(self, feats, proba=None):
        proba = self.predict_proba(feats) if proba is None else proba
        return [self.explain_row(row) if p >= 0.35 else [] for (_, row), p in zip(feats.iterrows(), proba)]

    # ----------------------------------------------------------- persistence
    def save(self, path):
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)
