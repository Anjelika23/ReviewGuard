from django.test import TestCase
from django.urls import reverse

from .models import Movie


class ReviewGuardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Movie.objects.create(product_id="MTEST", title="Test Movie", genre="Drama")

    def test_dashboard_loads(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_analyze_page_loads(self):
        response = self.client.get(reverse("analyze"))
        self.assertEqual(response.status_code, 200)

    def test_api_rejects_get(self):
        response = self.client.get(reverse("api_predict"))
        self.assertEqual(response.status_code, 405)

    def test_api_rejects_invalid_rating(self):
        response = self.client.post(reverse("api_predict"), data={
            "movie": "MTEST", "rating": 8, "review_text": "A long enough review",
            "account_age_days": 10
        }, content_type="application/json")
        self.assertEqual(response.status_code, 400)
