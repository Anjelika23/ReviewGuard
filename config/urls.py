from django.contrib import admin
from django.urls import include, path
from reviews.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="root_health"),
    path("healthz/", health_check, name="root_healthz"),
    path("", include("reviews.urls")),
]
