from django.core.management.base import BaseCommand

from ml.train import main


class Command(BaseCommand):
    help = "Train + evaluate the fake-review detector and save it to models/"

    def add_arguments(self, p):
        p.add_argument("--csv", default="data/reviews.csv")
        p.add_argument("--out", default="models")

    def handle(self, *a, **o):
        main(o["csv"], o["out"])
