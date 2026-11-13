"""Dual-feature engineering: behavioural metadata + NLP text analysis."""
import numpy as np
import pandas as pd

from .text_utils import normalize, text_features

REQUIRED = ["user_id", "product_id", "rating", "review_text", "account_age_days"]

BEHAVIOR_COLS = [
    "rating", "is_extreme", "is_five", "is_one",
    "account_age_days", "log_account_age", "is_new_account", "review_length",
    "user_review_count", "user_reviews_per_month", "user_extreme_share",
    "user_rating_std", "user_mean_rating",
    "product_dev", "product_abs_dev", "product_new_acct_share",
    "dup_text_count", "ip_review_count", "device_review_count",
]
TEXT_COLS = [
    "n_words", "avg_word_len", "n_sentences", "avg_sentence_len", "exclaim_count", "exclaim_ratio",
    "question_count", "caps_ratio", "all_caps_words", "stretched_chars", "digit_count",
    "lexical_diversity", "generic_hits", "aspect_hits", "first_person", "specificity",
    "pos_words", "neg_words", "sentiment_score",
]
CROSS_COLS = ["sentiment_rating_gap"]  # needs both text and rating


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return one feature row per review (index aligned with `df`).

    Aggregates (per user / per product / duplicates) are computed over the
    frame you pass in, so pass the full review history you want to reason over.
    Optional columns `ip_address` and `device_id` enable velocity features.
    """
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.reset_index(drop=True).copy()
    df["review_text"] = df["review_text"].fillna("").astype(str)
    if "review_length" not in df.columns:
        df["review_length"] = df["review_text"].str.len()

    f = pd.DataFrame(index=df.index)
    r = df["rating"].astype(float)
    age = df["account_age_days"].astype(float).clip(lower=0)

    # ---- behavioural: rating extremes & account profile
    f["rating"] = r
    f["is_extreme"] = r.isin([1, 5]).astype(int)
    f["is_five"] = (r == 5).astype(int)
    f["is_one"] = (r == 1).astype(int)
    f["account_age_days"] = age
    f["log_account_age"] = np.log1p(age)
    f["is_new_account"] = (age < 30).astype(int)
    f["review_length"] = df["review_length"].astype(float)

    # ---- behavioural: user velocity / consistency
    g = df.groupby("user_id")["rating"]
    cnt = g.transform("count")
    f["user_review_count"] = cnt
    f["user_reviews_per_month"] = cnt / (age / 30.0 + 1.0)
    f["user_extreme_share"] = f.groupby(df["user_id"])["is_extreme"].transform("mean")
    f["user_rating_std"] = g.transform("std").fillna(0.0)
    f["user_mean_rating"] = g.transform("mean")

    # ---- behavioural: product context (leave-one-out consensus)
    gp = df.groupby("product_id")["rating"]
    n, s = gp.transform("count"), gp.transform("sum")
    loo_mean = ((s - r) / (n - 1)).where(n > 1, r)
    f["product_dev"] = r - loo_mean
    f["product_abs_dev"] = f["product_dev"].abs()
    f["product_new_acct_share"] = f.groupby(df["product_id"])["is_new_account"].transform("mean")

    # ---- behavioural: duplicates + optional IP/device velocity
    norm = df["review_text"].map(normalize)
    f["dup_text_count"] = norm.groupby(norm).transform("count") - 1
    for col, out in (("ip_address", "ip_review_count"), ("device_id", "device_review_count")):
        if col in df.columns and df[col].notna().any():
            f[out] = df.groupby(col)["rating"].transform("count").where(df[col].notna(), 1)
        else:
            f[out] = 0

    # ---- NLP
    nlp = pd.DataFrame([text_features(t) for t in df["review_text"]], index=df.index)[TEXT_COLS]
    f = pd.concat([f, nlp], axis=1)
    rating_norm = (r - 3.0) / 2.0  # -1..1
    f["sentiment_rating_gap"] = (f["sentiment_score"].clip(-1, 1) - rating_norm).abs()

    f["clean_text"] = norm
    return f
