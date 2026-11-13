from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("movie/<str:product_id>/", views.movie_detail, name="movie_detail"),
    path("analyze/", views.analyze, name="analyze"),
    path("api/predict/", views.api_predict, name="api_predict"),
    path("api/trust/<str:product_id>/", views.api_trust, name="api_trust"),
]
