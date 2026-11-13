import json

from django.conf import settings
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .forms import ReviewAnalysisForm
from .models import Movie, Review, TrustScore
from .services import score_single


def _metrics():
    try:
        return json.loads(settings.METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def dashboard(request):
    scores = TrustScore.objects.select_related("movie").all()
    total = Review.objects.count()
    flagged = Review.objects.filter(predicted_fake=True).count()
    avg_infl = scores.aggregate(a=Avg("rating_inflation"))["a"] or 0
    ctx = {"scores": scores, "total": total, "flagged": flagged,
           "pct": (100 * flagged / total) if total else 0, "avg_infl": avg_infl,
           "n_manip": scores.filter(manipulated=True).count(), "metrics": _metrics()}
    return render(request, "reviews/dashboard.html", ctx)


def movie_detail(request, product_id):
    movie = get_object_or_404(Movie, pk=product_id)
    view = request.GET.get("view", "flagged")
    if view not in {"flagged", "genuine", "all"}:
        view = "flagged"
    qs = movie.reviews.all()
    if view == "flagged":
        qs = qs.filter(predicted_fake=True)
    elif view == "genuine":
        qs = qs.filter(predicted_fake=False)
    dist = {k: dict(movie.reviews.filter(predicted_fake=k).values_list("rating").annotate(n=Count("id")))
            for k in (False, True)}
    rows = [{"star": s, "genuine": dist[False].get(s, 0), "fake": dist[True].get(s, 0)} for s in (5, 4, 3, 2, 1)]
    return render(request, "reviews/movie_detail.html", {
        "movie": movie, "trust": getattr(movie, "trust", None), "view": view,
        "reviews": qs.order_by("-fake_probability")[:200], "dist": rows})


def analyze(request):
    result = None
    form = ReviewAnalysisForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if Movie.objects.filter(pk=data["movie"]).exists():
            result = score_single(data["movie"], data["user_id"], data["rating"], data["review_text"],
                                  data["account_age_days"], ip=request.META.get("REMOTE_ADDR"))
        else:
            form.add_error("movie", "Please select a valid movie.")
    return render(request, "reviews/analyze.html", {"movies": Movie.objects.all(), "result": result, "form": form})


@require_POST
def api_predict(request):
    """POST JSON: movie, user_id, rating, review_text, account_age_days."""
    try:
        data = json.loads(request.body or b"{}")
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        movie_id = str(data.get("movie", ""))
        user_id = str(data.get("user_id", "anonymous"))[:64]
        review_text = str(data.get("review_text", ""))
        rating = int(data.get("rating"))
        account_age = int(data.get("account_age_days", 0))
        if not Movie.objects.filter(pk=movie_id).exists():
            return JsonResponse({"error": "Unknown movie."}, status=400)
        if not 1 <= rating <= 5 or not 0 <= account_age <= 36500 or not 3 <= len(review_text) <= 5000:
            return JsonResponse({"error": "Rating, account age or review text is outside allowed limits."}, status=400)
        out = score_single(movie_id, user_id, rating, review_text, account_age,
                           data.get("ip_address"), data.get("device_id"))
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return JsonResponse({"error": "Invalid JSON or missing/invalid fields."}, status=400)
    return JsonResponse(out)


def api_trust(request, product_id):
    t = get_object_or_404(TrustScore.objects.select_related("movie"), movie_id=product_id)
    return JsonResponse({
        "product_id": product_id, "title": t.movie.title, "verified_trust_score": t.trust_score,
        "grade": t.grade, "raw_avg": round(t.raw_avg, 2), "verified_avg": round(t.verified_avg, 2),
        "reviews": t.n_reviews, "flagged_fake": t.n_flagged, "fake_share": round(t.fake_share, 3),
        "manipulated": t.manipulated})
