from django.core.management.base import BaseCommand

from ml.generate_data import generate


class Command(BaseCommand):
    help = "Generate the dummy reviews.csv / movies.csv dataset"

    def add_arguments(self, p):
        p.add_argument("--out", default="data")
        p.add_argument("--genuine", type=int, default=5700)
        p.add_argument("--fake", type=int, default=2800)

    def handle(self, *a, **o):
        from pathlib import Path
        out = Path(o["out"]); out.mkdir(exist_ok=True)
        df, movies = generate(o["genuine"], o["fake"])
        df.to_csv(out / "reviews.csv", index=False); movies.to_csv(out / "movies.csv", index=False)
        self.stdout.write(self.style.SUCCESS(f"{len(df)} reviews, {df.is_fake.mean():.1%} fake → {out}/"))
