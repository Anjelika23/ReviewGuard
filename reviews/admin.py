from django.contrib import admin

from .models import Movie, Review, TrustScore


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("product_id", "title", "genre")
    search_fields = ("title", "product_id")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user_id", "movie", "rating", "fake_probability", "predicted_fake", "is_fake")
    list_filter = ("predicted_fake", "rating", "is_fake")
    search_fields = ("user_id", "review_text")


@admin.register(TrustScore)
class TrustScoreAdmin(admin.ModelAdmin):
    list_display = ("movie", "trust_score", "grade", "raw_avg", "verified_avg", "fake_share", "manipulated")
