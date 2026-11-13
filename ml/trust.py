"""Verified Trust Score: product rating after fake reviews are filtered out."""
import numpy as np
import pandas as pd

PRIOR_N = 10           # Bayesian prior strength (pseudo-reviews)
W_QUALITY = 0.75       # weight of verified quality in the final score
W_AUTHENTICITY = 0.25  # weight of review-integrity in the final score


def grade(score: float) -> str:
    return "Excellent" if score >= 80 else "Good" if score >= 65 else "Fair" if score >= 50 else "Poor"


def compute_trust_scores(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """df needs: product_id, rating, account_age_days, fake_prob.

    verified_avg = credibility-weighted mean, each review weighted by
                   (1 - fake_prob) * (0.6 + 0.4 * min(account_age/365, 1)); flagged reviews get 0
    bayes_avg    = verified_avg shrunk toward the global genuine mean (prior PRIOR_N)
    trust_score  = 100 * (0.75 * (bayes_avg-1)/4 + 0.25 * (1 - fake_share))
    """
    d = df.copy()
    d["flagged"] = d["fake_prob"] >= threshold
    genuine = d[~d["flagged"]]
    global_mean = float(genuine["rating"].mean()) if len(genuine) else float(d["rating"].mean())

    d["cred"] = 0.6 + 0.4 * np.minimum(d["account_age_days"].astype(float) / 365.0, 1.0)
    d["w"] = np.where(d["flagged"], 0.0, (1.0 - d["fake_prob"]) * d["cred"])
    d["wr"] = d["w"] * d["rating"]

    agg = d.groupby("product_id").agg(
        n_reviews=("rating", "size"), n_flagged=("flagged", "sum"),
        raw_avg=("rating", "mean"), sw=("w", "sum"), swr=("wr", "sum"))
    agg["fake_share"] = agg["n_flagged"] / agg["n_reviews"]
    safe_sw = agg["sw"].where(agg["sw"] > 0, 1.0)
    agg["verified_avg"] = np.where(agg["sw"] > 0, agg["swr"] / safe_sw, global_mean)
    agg["bayes_avg"] = (agg["swr"] + PRIOR_N * global_mean) / (agg["sw"] + PRIOR_N)
    quality = (agg["bayes_avg"] - 1) / 4
    agg["trust_score"] = (100 * (W_QUALITY * quality + W_AUTHENTICITY * (1 - agg["fake_share"]))).round(1)
    agg["rating_inflation"] = agg["raw_avg"] - agg["verified_avg"]
    agg["grade"] = agg["trust_score"].map(grade)
    agg["manipulated"] = (agg["fake_share"] > 0.25) | (agg["rating_inflation"].abs() > 0.5)
    agg["n_flagged"] = agg["n_flagged"].astype(int)
    return agg.drop(columns=["sw", "swr"]).reset_index()
