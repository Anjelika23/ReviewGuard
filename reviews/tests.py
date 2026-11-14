import json
from django.test import TestCase
from django.urls import reverse

from .models import Movie, Review, TrustScore
from .services import score_single


class ReviewGuardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.movie = Movie.objects.create(product_id="MTEST", title="Test Movie", genre="Sci-Fi")
        cls.trust = TrustScore.objects.create(
            movie=cls.movie,
            n_reviews=10,
            n_flagged=2,
            fake_share=0.2,
            raw_avg=4.5,
            verified_avg=4.2,
            rating_inflation=0.3,
            trust_score=78.5,
            grade="Good",
            manipulated=False,
        )
        Review.objects.create(
            movie=cls.movie,
            user_id="U_reviewer_1",
            rating=5,
            review_text="This is an authentic and thoughtful movie review with sufficient detail.",
            account_age_days=150,
            review_length=75,
            fake_probability=0.08,
            predicted_fake=False,
            reasons="",
        )
        Review.objects.create(
            movie=cls.movie,
            user_id="U_bot_1",
            rating=5,
            review_text="Best movie ever 10/10 masterpiece must watch!",
            account_age_days=1,
            review_length=45,
            fake_probability=0.88,
            predicted_fake=True,
            reasons="Generic, templated superlative language",
        )

    def test_dashboard_loads(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")

    def test_dashboard_filter_search(self):
        response = self.client.get(reverse("dashboard") + "?q=Sci-Fi")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")

        response_empty = self.client.get(reverse("dashboard") + "?q=NonExistentMovie123")
        self.assertEqual(response_empty.status_code, 200)
        self.assertNotContains(response_empty, "Test Movie")

    def test_movie_detail_loads(self):
        response = self.client.get(reverse("movie_detail", kwargs={"product_id": "MTEST"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")
        self.assertContains(response, "78.5")

    def test_analyze_page_loads(self):
        response = self.client.get(reverse("analyze"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analyze Review")

    def test_health_check_endpoint(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["service"], "ReviewGuard")
        self.assertIn("status", data)
        self.assertIn("database", data)

    def test_root_health_check(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)

    def test_api_docs_loads(self):
        response = self.client.get(reverse("api_docs"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REST API Documentation")

    def test_api_trust_endpoint(self):
        response = self.client.get(reverse("api_trust", kwargs={"product_id": "MTEST"}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["product_id"], "MTEST")
        self.assertEqual(data["verified_trust_score"], 78.5)
        self.assertEqual(data["grade"], "Good")

    def test_api_rejects_get(self):
        response = self.client.get(reverse("api_predict"))
        self.assertEqual(response.status_code, 405)

    def test_api_predict_valid_json(self):
        payload = {
            "movie": "MTEST",
            "user_id": "test_analyst",
            "rating": 5,
            "review_text": "Remarkable acting and cinematography, visually engaging story.",
            "account_age_days": 180,
        }
        response = self.client.post(
            reverse("api_predict"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("prediction", data)
        self.assertIn("fake_probability", data["prediction"])
        self.assertIn("is_fake", data["prediction"])

    def test_api_rejects_invalid_rating(self):
        response = self.client.post(reverse("api_predict"), data=json.dumps({
            "movie": "MTEST", "rating": 8, "review_text": "A long enough review",
            "account_age_days": 10
        }), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_api_rejects_nonexistent_movie(self):
        response = self.client.post(reverse("api_predict"), data=json.dumps({
            "movie": "NON_EXISTENT_ID", "rating": 4, "review_text": "Good movie overall",
            "account_age_days": 10
        }), content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_service_score_single(self):
        res = score_single(
            movie_id="MTEST",
            user_id="U_test_single",
            rating=5,
            text="Best movie ever 10/10 masterpiece must watch!",
            account_age_days=1,
        )
        self.assertIn("fake_probability", res)
        self.assertIn("is_fake", res)
        self.assertIn("risk_level", res)
        self.assertIn("reasons", res)
