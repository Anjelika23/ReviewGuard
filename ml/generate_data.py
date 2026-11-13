"""Synthetic movie-review dataset with realistic fraud patterns.

Columns (exactly as the project spec): user_id, product_id, rating, review_text,
account_age_days, review_length, is_fake.  Also writes data/movies.csv.

Fraud patterns simulated
  * bot-farm 5-star campaigns on weak movies (templated gushing, new accounts, high velocity)
  * competitor-sabotage 1-star campaigns on strong movies
  * hard cases: LLM-style fluent fakes, 'sleeper' bot accounts with age, camouflage ratings,
    and genuine short/extreme reviews from new accounts (so the task is not trivially separable)
"""
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

TITLES = [
    ("Midnight Harbor", "Thriller"), ("The Last Cartographer", "Adventure"), ("Paper Lanterns", "Drama"),
    ("Neon Requiem", "Sci-Fi"), ("Salt & Smoke", "Crime"), ("A Quiet Orbit", "Sci-Fi"),
    ("The Glass Orchard", "Drama"), ("Rooftop Kings", "Action"), ("Echoes of Marrow", "Horror"),
    ("Hollow Crown", "Fantasy"), ("Seven Rivers", "Adventure"), ("Velvet Static", "Comedy"),
    ("The Long Tuesday", "Comedy"), ("Iron Lullaby", "Action"), ("Saffron Skies", "Romance"),
    ("Ghost Ledger", "Thriller"), ("Moonlit Arithmetic", "Drama"), ("Dust Choir", "Western"),
    ("Cold Signal", "Sci-Fi"), ("The Tailor of Vesper", "Mystery"), ("Fault Lines", "Drama"),
    ("Sparrow Protocol", "Action"), ("Autumn Detective", "Mystery"), ("Blue Hour Bakery", "Romance"),
    ("Wolves at Low Tide", "Horror"), ("Parade of Ashes", "War"), ("The Understudy", "Comedy"),
    ("Orbit Street", "Sci-Fi"), ("Lanterns Over Kiev Road", "Drama"), ("Copper Sun", "Western"),
    ("Mirror Season", "Fantasy"), ("The Quiet Heist", "Crime"), ("Fever Dream Motel", "Horror"),
    ("North of Nowhere", "Adventure"), ("Brass Hearts", "Romance"), ("Static Lullabies", "Drama"),
    ("The Archivist", "Mystery"), ("Thunder Alley", "Action"), ("Small Hours", "Drama"),
    ("Pocket Universe", "Comedy"),
]
ACTORS = ["Elena Marsh", "Daniel Okoro", "Priya Raman", "Tomas Weiss", "Aiko Tanaka", "Marcus Bell",
          "Lucia Fontaine", "Omar Haddad", "Sofia Lindgren", "Jamal Carter", "Ingrid Solberg",
          "Rafael Duarte", "Mei Lin", "Callum Reid", "Nadia Petrov", "Hugo Barrett", "Zara Ahmed",
          "Victor Hale", "Amara Diallo", "Felix Moreau"]
SCENES = ["the rooftop chase", "the final confrontation", "the dinner table argument",
          "the opening sequence", "the flashback in the desert", "the quiet train ride",
          "the courtroom reveal", "the storm at sea", "the museum heist", "the reunion at the airport"]
ASPECTS = ["cinematography", "soundtrack", "pacing", "script", "editing", "dialogue",
           "special effects", "ending", "production design", "second act"]

POS_OPEN = ["I really enjoyed this one.", "Went in with low expectations and came out impressed.",
            "A thoroughly satisfying watch.", "One of the better films I've seen this year.",
            "Solid from start to finish.", "This surprised me in the best way."]
NEG_OPEN = ["I wanted to like this but it fell flat.", "Disappointing, especially given the hype.",
            "Struggled to stay engaged after the first act.", "Not the film I was hoping for.",
            "This had potential and squandered most of it."]
MID_OPEN = ["It's decent but not memorable.", "Mixed feelings about this one.",
            "Some good ideas, uneven execution.", "Watchable, though it never fully clicked for me."]
POS_DET = ["{a} delivers a really convincing performance.", "The {x} was genuinely impressive.",
           "I loved {s}, it stayed with me for days.",
           "The chemistry between {a} and {b} made the whole thing believable.",
           "The {x} gave the story real emotional weight."]
NEG_DET = ["{a} felt miscast and the dialogue didn't help.", "The {x} was a letdown.",
           "{s} dragged on far longer than it needed to.",
           "I couldn't connect with the characters at all.", "The {x} felt rushed and underdeveloped."]
MID_DET = ["{a} was good but the {x} was uneven.", "{s} was great, yet the middle section dragged.",
           "The {x} worked, the rest was hit and miss."]
POS_CLOSE = ["Would happily watch it again.", "Recommended if you enjoy {g} films.",
             "Glad I caught it on the big screen."]
NEG_CLOSE = ["Probably won't rewatch it.", "Hard to recommend unless you're a {g} completist.",
             "Left the cinema underwhelmed."]
MID_CLOSE = ["Fine for a lazy weekend.", "Worth a rental if you like {g}, otherwise skip."]
POS_SHORT = ["Loved it!", "Great watch.", "Really good film.", "Fun movie, worth seeing.", "Brilliant."]
NEG_SHORT = ["Not for me.", "Pretty boring.", "Meh, disappointing.", "Waste of an evening.", "Awful."]
MID_SHORT = ["It was okay.", "Decent, nothing special.", "Average."]

BOOST = ["Amazing movie!!!", "Best film ever!", "Absolutely loved it, 10/10.", "Must watch for everyone.",
         "Five stars, highly recommended.", "Masterpiece. Worth every penny.",
         "Great acting great story great everything.", "Perfect movie, nothing negative to say.",
         "Don't miss this one, you will love it!", "Blockbuster hit. Unbelievable!!!"]
SABOTAGE = ["Worst movie ever.", "Total waste of money and time.", "Do not watch this garbage.",
            "Boring, terrible, awful acting.", "Zero stars if I could.",
            "Complete scam, don't be fooled by the hype.",
            "Pathetic script and the director should be ashamed.", "Save your money, trash film.",
            "Absolutely horrible, 0/10."]
LLM_POS = ["Overall, this movie offers a captivating storyline, stellar performances, and breathtaking visuals that make it a must-see.",
           "The film delivers an unforgettable cinematic experience with outstanding performances and a compelling narrative.",
           "A remarkable achievement in storytelling that will leave audiences inspired and entertained.",
           "Highly recommended for anyone who appreciates high-quality cinema."]
LLM_NEG = ["Overall, the movie fails to deliver a coherent narrative, with weak performances and uninspired direction.",
           "The film is a disappointing experience that wastes its premise and the audience's time.",
           "A forgettable production with poor pacing and no emotional payoff whatsoever.",
           "I cannot recommend this to anyone looking for quality entertainment."]


def _pick_rating(q, rng):
    r = int(round(rng.normal(q, 0.95)))
    if rng.random() < 0.08:
        r = 5 if rng.random() < (q - 1) / 4 else 1
    return int(np.clip(r, 1, 5))


def _genuine_text(rating, m, rng):
    sent = "pos" if rating >= 4 else "neg" if rating <= 2 else "mid"
    pools = {"pos": (POS_OPEN, POS_DET, POS_CLOSE, POS_SHORT), "neg": (NEG_OPEN, NEG_DET, NEG_CLOSE, NEG_SHORT),
             "mid": (MID_OPEN, MID_DET, MID_CLOSE, MID_SHORT)}
    op, det, cl, short = pools[sent]
    if rng.random() < 0.12:
        return rng.choice(short)
    a, b = rng.choice(m["actors"], 2, replace=False)
    fill = dict(a=a, b=b, s=rng.choice(m["scenes"]), x=rng.choice(ASPECTS), g=m["genre"].lower())
    parts = [rng.choice(op)] + [t.format(**fill) for t in rng.choice(det, rng.integers(1, 4), replace=False)]
    if rng.random() < 0.35:  # nuance: a contrasting remark
        contrast = POS_DET if sent == "neg" else NEG_DET
        parts.append("On the other hand, " + rng.choice(contrast).format(**fill)[0].lower() + rng.choice(contrast).format(**fill)[1:])
    if rng.random() < 0.6:
        parts.append(rng.choice(cl).format(**fill))
    return " ".join(parts)


def _template_text(kind, rng):
    pool = BOOST if kind == "boost" else SABOTAGE
    t = " ".join(rng.choice(pool, rng.integers(1, 4), replace=False))
    if rng.random() < 0.15:
        t = t.upper()
    return t


def _fake_text(kind, m, rng, stealth=0.32):
    if rng.random() < stealth:  # "stealth": paid writer imitates a genuine, detailed review
        return _genuine_text(5 if kind == "boost" else 1, m, rng)
    if rng.random() < 0.22:  # sophisticated / LLM-style
        pool = LLM_POS if kind == "boost" else LLM_NEG
        parts = list(rng.choice(pool, rng.integers(1, 3), replace=False))
        if rng.random() < 0.4:
            parts.insert(0, f"{rng.choice(m['actors'])} " + ("was great." if kind == "boost" else "was wasted."))
        return " ".join(parts)
    pool = BOOST if kind == "boost" else SABOTAGE
    t = " ".join(rng.choice(pool, rng.integers(1, 5), replace=False))
    if rng.random() < 0.25:
        t = t.upper()
    if rng.random() < 0.2:
        t += "!!!"
    return t


def generate(n_genuine=5700, n_fake=2800, seed=7):
    rng = np.random.default_rng(seed)
    random.seed(seed)

    movies = []
    for i, (title, genre) in enumerate(TITLES):
        movies.append(dict(product_id=f"M{i + 1:03d}", title=title, genre=genre, q=float(rng.uniform(2.4, 4.5)),
                           pop=float(rng.lognormal(0, 0.6)),
                           actors=list(rng.choice(ACTORS, 3, replace=False)),
                           scenes=list(rng.choice(SCENES, 3, replace=False))))
    low = [m for m in movies if m["q"] < 3.4]
    high = [m for m in movies if m["q"] > 3.8]
    boosted = list(rng.choice(low, min(7, len(low)), replace=False))
    sabotaged = list(rng.choice(high, min(6, len(high)), replace=False))

    ids = rng.permutation(np.arange(10000, 99999))
    gen_users = [f"U{i}" for i in ids[:2600]]
    bot_users = [f"U{i}" for i in ids[2600:2600 + 520]]
    gen_age = {u: int(rng.lognormal(np.log(450), 0.9)) + 3 if rng.random() > 0.16 else int(rng.integers(1, 40))
               for u in gen_users}
    bot_age = {u: int(rng.exponential(18)) + 1 if rng.random() > 0.38 else int(rng.integers(30, 700))
               for u in bot_users}
    gen_w = rng.lognormal(0, 1.25, len(gen_users)); gen_w /= gen_w.sum()
    bot_w = rng.lognormal(0, 0.35, len(bot_users)); bot_w /= bot_w.sum()
    bot_kind = {u: ("boost" if rng.random() < 0.55 else "sabotage") for u in bot_users}
    mp = np.array([m["pop"] for m in movies]); mp /= mp.sum()

    rows = []
    for _ in range(n_genuine):
        u = gen_users[rng.choice(len(gen_users), p=gen_w)]
        m = movies[rng.choice(len(movies), p=mp)]
        r = _pick_rating(m["q"], rng)
        if r in (1, 5) and rng.random() < 0.12:   # real fans/haters write gushing or ranting text too
            text = _template_text("boost" if r == 5 else "sabotage", rng)
        else:
            text = _genuine_text(r, m, rng)
        rows.append((u, m["product_id"], r, text, gen_age[u], 0))

    oneshot = 0
    for _ in range(n_fake):
        if rng.random() < 0.27:  # one-shot fake: hijacked / aged / throwaway account, behaviour looks normal
            oneshot += 1
            u = f"U{ids[4000 + oneshot]}"
            age = int(rng.lognormal(np.log(300), 1.0)) + 2 if rng.random() < 0.6 else int(rng.integers(1, 40))
            kind = "boost" if rng.random() < 0.55 else "sabotage"
            if rng.random() < 0.5:   # half of one-shot fakes are spread across ordinary movies
                m = movies[rng.integers(len(movies))]
            else:
                m = boosted[rng.integers(len(boosted))] if kind == "boost" else sabotaged[rng.integers(len(sabotaged))]
            r = 5 if kind == "boost" else 1
            if rng.random() < 0.25:
                r = 4 if kind == "boost" else 2
            rows.append((u, m["product_id"], r, _fake_text(kind, m, rng, stealth=0.08), age, 1))
            continue
        u = bot_users[rng.choice(len(bot_users), p=bot_w)]
        kind = bot_kind[u]
        if rng.random() < 0.22:  # camouflage: bot posts a normal-looking review to blend in
            m = movies[rng.integers(len(movies))]
            r = _pick_rating(m["q"], rng)
            rows.append((u, m["product_id"], r, _genuine_text(r, m, rng), bot_age[u], 1))
            continue
        m = boosted[rng.integers(len(boosted))] if kind == "boost" else sabotaged[rng.integers(len(sabotaged))]
        r = (5 if kind == "boost" else 1)
        if rng.random() < 0.10:
            r = 4 if kind == "boost" else 2
        rows.append((u, m["product_id"], r, _fake_text(kind, m, rng), bot_age[u], 1))

    df = pd.DataFrame(rows, columns=["user_id", "product_id", "rating", "review_text", "account_age_days", "is_fake"])
    flip = rng.random(len(df)) < 0.02          # annotation noise
    df["is_fake"] = np.where(flip, 1 - df["is_fake"], df["is_fake"])
    df = df.drop_duplicates(["user_id", "product_id"]).sample(frac=1, random_state=seed).reset_index(drop=True)
    df["review_length"] = df["review_text"].str.len()
    df = df[["user_id", "product_id", "rating", "review_text", "account_age_days", "review_length", "is_fake"]]
    movies_df = pd.DataFrame([{k: m[k] for k in ("product_id", "title", "genre")} for m in movies])
    return df, movies_df


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data")
    p.add_argument("--genuine", type=int, default=5700)
    p.add_argument("--fake", type=int, default=2800)
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    df, movies = generate(a.genuine, a.fake, a.seed)
    df.to_csv(out / "reviews.csv", index=False)
    movies.to_csv(out / "movies.csv", index=False)
    print(f"Wrote {len(df)} reviews ({df.is_fake.mean():.1%} fake) and {len(movies)} movies to {out}/")


if __name__ == "__main__":
    main()
