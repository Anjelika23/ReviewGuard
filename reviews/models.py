from django.db import models


class Movie(models.Model):
    product_id = models.CharField(max_length=32, primary_key=True)
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.product_id})"


class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="reviews")
    user_id = models.CharField(max_length=64, db_index=True)
    rating = models.PositiveSmallIntegerField()
    review_text = models.TextField()
    account_age_days = models.PositiveIntegerField()
    review_length = models.PositiveIntegerField()
    is_fake = models.BooleanField(null=True, blank=True, help_text="Ground-truth label (training data only)")
    # optional live-traffic metadata used for IP/device velocity features
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # model output
    fake_probability = models.FloatField(null=True, blank=True, db_index=True)
    predicted_fake = models.BooleanField(default=False, db_index=True)
    reasons = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["movie", "predicted_fake"])]

    def __str__(self):
        return f"{self.user_id} → {self.movie_id}: {self.rating}★"

    @property
    def reason_list(self):
        return [r for r in self.reasons.split(" | ") if r]


class TrustScore(models.Model):
    movie = models.OneToOneField(Movie, on_delete=models.CASCADE, related_name="trust")
    n_reviews = models.PositiveIntegerField()
    n_flagged = models.PositiveIntegerField()
    fake_share = models.FloatField()
    raw_avg = models.FloatField()
    verified_avg = models.FloatField()
    rating_inflation = models.FloatField()
    trust_score = models.FloatField(db_index=True)
    grade = models.CharField(max_length=16)
    manipulated = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-trust_score"]
