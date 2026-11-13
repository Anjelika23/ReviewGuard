from django.core.management.base import BaseCommand

from reviews.services import rescore_all


class Command(BaseCommand):
    help = "Re-score every review in the DB and rebuild Verified Trust Scores"

    def handle(self, *a, **o):
        self.stdout.write(self.style.SUCCESS(str(rescore_all())))
