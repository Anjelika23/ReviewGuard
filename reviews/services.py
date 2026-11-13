"""Glue between Django models and the ML package."""
from functools import lru_cache

import pandas as pd
from django.conf import settings
from django.db.models import Q

from ml.detector import FakeReviewDetector
from ml.features import build_features
from ml.trust import compute_trust_scores

from .models import Movie, Review, TrustScore

COLS = ["id", "user_id", "movie_id", "rating", "review_text", "account_age_days",
        "review_length", "ip_address", "device_id"]


@lru_cache(maxsize=1)
def get_detector() -> FakeReviewDetector:
    det = FakeReviewDetector.load(settings.MODEL_PATH)
    det.threshold = settings.FAKE_THRESHOLD
    return det


def _frame(qs) -> pd.DataFrame:
    df = pd.DataFrame(list(qs.values(*COLS))).rename(columns={"movie_id": "product_id"})
    if not df.empty:
        df["ip_address"] = df["ip_address"].astype("object")
    return df


def refresh_trust_scores(scored: pd.DataFrame) -> int:
    ts = compute_trust_scores(scored[["product_id", "rating", "account_age_days", "fake_prob"]],
                              threshold=settings.FAKE_THRESHOLD)
    for row in ts.to_dict("records"):
        TrustScore.objects.update_or_create(
            movie_id=row["product_id"],
            defaults=dict(n_reviews=row["n_reviews"], n_flagged=row["n_flagged"],
                          fake_share=row["fake_share"], raw_avg=row["raw_avg"],
                          verified_avg=row["verified_avg"], rating_inflation=row["rating_inflation"],
                          trust_score=row["trust_score"], grade=row["grade"],
                          manipulated=bool(row["manipulated"])))
    return len(ts)


def rescore_all() -> dict:
    """Score every review in the DB, store flags + reasons, rebuild trust scores."""
    det = get_detector()
    df = _frame(Review.objects.all())
    if df.empty:
        return {"reviews": 0, "flagged": 0, "movies": 0}
    feats = build_features(df)
    proba = det.predict_proba(feats)
    reasons = det.explain_frame(feats, proba)
    objs = [Review(id=int(i), fake_probability=float(p), predicted_fake=bool(p >= det.threshold),
                   reasons=" | ".join(rs)) for i, p, rs in zip(df["id"], proba, reasons)]
    Review.objects.bulk_update(objs, ["fake_probability", "predicted_fake", "reasons"], batch_size=1000)
    n_movies = refresh_trust_scores(df.assign(fake_prob=proba))
    return {"reviews": len(df), "flagged": int((proba >= det.threshold).sum()), "movies": n_movies}


def score_single(movie_id, user_id, rating, text, account_age_days, ip=None, device=None) -> dict:
    """Score one (possibly unseen) review using the user's and movie's existing history as context."""
    det = get_detector()
    ctx = _frame(Review.objects.filter(Q(movie_id=movie_id) | Q(user_id=user_id)))
    new = pd.DataFrame([{"id": -1, "user_id": user_id, "product_id": movie_id, "rating": rating,
                         "review_text": text, "account_age_days": account_age_days,
                         "review_length": len(text), "ip_address": ip, "device_id": device}])
    df = new if ctx.empty else pd.concat([ctx, new], ignore_index=True)
    feats = build_features(df)
    p = float(det.predict_proba(feats.iloc[[-1]])[0])
    return {"fake_probability": round(p, 4), "is_fake": p >= det.threshold,
            "label": "Likely fake" if p >= det.threshold else "Likely genuine",
            "reasons": det.explain_row(feats.iloc[-1]) if p >= 0.35 else []}
