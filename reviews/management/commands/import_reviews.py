import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from reviews.models import Movie, Review
from reviews.services import rescore_all


class Command(BaseCommand):
    help = "Load reviews.csv (+ movies.csv) into the database, then score and build trust scores"

    def add_arguments(self, p):
        p.add_argument("--csv", default="data/reviews.csv")
        p.add_argument("--movies", default="data/movies.csv")
        p.add_argument("--no-score", action="store_true")
        p.add_argument("--keep", action="store_true", help="Do not wipe existing reviews first")

    @transaction.atomic
    def handle(self, *a, **o):
        df = pd.read_csv(o["csv"])
        if not o["keep"]:
            Review.objects.all().delete()
        try:
            for r in pd.read_csv(o["movies"]).to_dict("records"):
                Movie.objects.update_or_create(product_id=r["product_id"], defaults=dict(title=r["title"], genre=r["genre"]))
        except FileNotFoundError:
            for pid in df["product_id"].unique():
                Movie.objects.get_or_create(product_id=pid, defaults=dict(title=pid))
        Review.objects.bulk_create([
            Review(movie_id=r.product_id, user_id=r.user_id, rating=int(r.rating), review_text=r.review_text,
                   account_age_days=int(r.account_age_days), review_length=int(r.review_length),
                   is_fake=bool(r.is_fake) if "is_fake" in df.columns else None)
            for r in df.itertuples()], batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(df)} reviews"))
        if not o["no_score"]:
            self.stdout.write(str(rescore_all()))
