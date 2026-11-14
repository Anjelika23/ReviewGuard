import json

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import ReviewAnalysisForm
from .models import Movie, Review, TrustScore
from .services import score_single


def _metrics():
    try:
        return json.loads(settings.METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def health_check(request):
    """Zero-dependency health check endpoint for container orchestrators and reverse proxies."""
    db_ok = True
    db_err = None
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        db_ok = False
        db_err = str(e)

    model_ready = settings.MODEL_PATH.exists()
    status_code = 200 if (db_ok and model_ready) else 200  # Return 200 so orchestrator doesn't kill cold instances

    return JsonResponse({
        "status": "healthy" if db_ok else "degraded",
        "service": "ReviewGuard",
        "version": "2.0.0",
        "database": "connected" if db_ok else f"error: {db_err}",
        "model_loaded": model_ready,
        "total_movies": Movie.objects.count() if db_ok else 0,
        "total_reviews": Review.objects.count() if db_ok else 0,
    }, status=status_code)


def dashboard(request):
    q = request.GET.get("q", "").strip()
    grade = request.GET.get("grade", "").strip()
    status_filter = request.GET.get("status", "").strip()
    genre_filter = request.GET.get("genre", "").strip()
    sort = request.GET.get("sort", "trust_score")
    order = request.GET.get("order", "desc")

    qs = TrustScore.objects.select_related("movie").all()
    if q:
        qs = qs.filter(Q(movie__title__icontains=q) | Q(movie__genre__icontains=q) | Q(movie__product_id__icontains=q))
    if grade in {"Excellent", "Good", "Fair", "Poor"}:
        qs = qs.filter(grade=grade)
    if genre_filter:
        qs = qs.filter(movie__genre__iexact=genre_filter)
    if status_filter == "manipulated":
        qs = qs.filter(manipulated=True)
    elif status_filter == "clean":
        qs = qs.filter(manipulated=False)

    valid_sorts = {
        "trust_score": "trust_score",
        "title": "movie__title",
        "reviews": "n_reviews",
        "flagged": "n_flagged",
        "raw_avg": "raw_avg",
        "verified_avg": "verified_avg",
        "fake_share": "fake_share",
        "rating_inflation": "rating_inflation",
    }
    sort_field = valid_sorts.get(sort, "trust_score")
    if order == "desc":
        sort_field = "-" + sort_field
    scores = qs.order_by(sort_field)

    all_scores = TrustScore.objects.all()
    total = Review.objects.count()
    flagged = Review.objects.filter(predicted_fake=True).count()
    avg_infl = all_scores.aggregate(a=Avg("rating_inflation"))["a"] or 0
    n_manip = all_scores.filter(manipulated=True).count()

    # Distinct genres for dropdown
    genres = sorted([g for g in Movie.objects.values_list("genre", flat=True).distinct() if g])

    ctx = {
        "scores": scores,
        "total_movies": all_scores.count(),
        "filtered_count": scores.count(),
        "total": total,
        "flagged": flagged,
        "pct": (100 * flagged / total) if total else 0,
        "avg_infl": avg_infl,
        "n_manip": n_manip,
        "metrics": _metrics(),
        "genres": genres,
        "q": q,
        "grade_filter": grade,
        "genre_filter": genre_filter,
        "status_filter": status_filter,
        "sort": sort,
        "order": order,
    }
    return render(request, "reviews/dashboard.html", ctx)


def movie_detail(request, product_id):
    movie = get_object_or_404(Movie, pk=product_id)
    view = request.GET.get("view", "all")
    if view not in {"flagged", "genuine", "all"}:
        view = "all"

    star = request.GET.get("star", "")
    q = request.GET.get("q", "").strip()

    qs = movie.reviews.all()
    if view == "flagged":
        qs = qs.filter(predicted_fake=True)
    elif view == "genuine":
        qs = qs.filter(predicted_fake=False)

    if star.isdigit() and 1 <= int(star) <= 5:
        qs = qs.filter(rating=int(star))

    if q:
        qs = qs.filter(Q(review_text__icontains=q) | Q(user_id__icontains=q))

    # Paginate reviews (30 per page)
    paginator = Paginator(qs.order_by("-fake_probability", "-id"), 30)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Rating distribution: genuine vs flagged
    dist = {k: dict(movie.reviews.filter(predicted_fake=k).values_list("rating").annotate(n=Count("id")))
            for k in (False, True)}
    total_reviews = movie.reviews.count()
    rows = []
    for s in (5, 4, 3, 2, 1):
        g = dist[False].get(s, 0)
        f = dist[True].get(s, 0)
        tot = g + f
        pct = (tot / total_reviews * 100) if total_reviews else 0
        rows.append({
            "star": s,
            "genuine": g,
            "fake": f,
            "total": tot,
            "pct": round(pct, 1)
        })

    ctx = {
        "movie": movie,
        "trust": getattr(movie, "trust", None),
        "view": view,
        "reviews": page_obj,
        "dist": rows,
        "star": star,
        "q": q,
        "total_reviews": total_reviews,
        "flagged_count": movie.reviews.filter(predicted_fake=True).count(),
        "genuine_count": movie.reviews.filter(predicted_fake=False).count(),
    }
    return render(request, "reviews/movie_detail.html", ctx)


def analyze(request):
    result = None
    form = ReviewAnalysisForm(request.POST or None)
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json"

    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            if Movie.objects.filter(pk=data["movie"]).exists():
                result = score_single(
                    data["movie"], data["user_id"], data["rating"], data["review_text"],
                    data["account_age_days"], ip=request.META.get("REMOTE_ADDR")
                )
                if is_ajax:
                    return JsonResponse({"success": True, "result": result})
            else:
                form.add_error("movie", "Please select a valid movie.")
                if is_ajax:
                    return JsonResponse({"success": False, "error": "Invalid movie selected."}, status=400)
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    movies = Movie.objects.all().order_by("title")
    return render(request, "reviews/analyze.html", {
        "movies": movies,
        "result": result,
        "form": form,
    })


def api_docs(request):
    """Interactive API documentation and schema."""
    sample_movie = Movie.objects.first()
    sample_id = sample_movie.product_id if sample_movie else "M001"
    return render(request, "reviews/api_docs.html", {
        "sample_id": sample_id,
    })


@csrf_exempt
@require_POST
def api_predict(request):
    """Production JSON endpoint for fake-review risk classification.
    
    Accepts:
        movie (str): Movie product_id
        user_id (str, optional): Reviewer ID
        rating (int): Star rating (1-5)
        review_text (str): Full review text (3-5000 chars)
        account_age_days (int): Reviewer account age in days
        ip_address (str, optional): Client IP
        device_id (str, optional): Device fingerprint
    """
    try:
        body = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
        data = json.loads(body or "{}")
        if not isinstance(data, dict):
            return JsonResponse({"error": "JSON body must be an object."}, status=400)

        movie_id = str(data.get("movie", "")).strip()
        if not movie_id:
            return JsonResponse({"error": "Missing required field: 'movie'."}, status=400)

        if not Movie.objects.filter(pk=movie_id).exists():
            return JsonResponse({"error": f"Movie with ID '{movie_id}' not found."}, status=404)

        user_id = str(data.get("user_id", "anonymous"))[:64]
        review_text = str(data.get("review_text", "")).strip()
        if len(review_text) < 3:
            return JsonResponse({"error": "review_text must have at least 3 characters."}, status=400)
        if len(review_text) > 5000:
            return JsonResponse({"error": "review_text must not exceed 5000 characters."}, status=400)

        raw_rating = data.get("rating")
        if raw_rating is None:
            return JsonResponse({"error": "Missing required field: 'rating'."}, status=400)
        try:
            rating = int(raw_rating)
        except (ValueError, TypeError):
            return JsonResponse({"error": "rating must be an integer between 1 and 5."}, status=400)
        if not 1 <= rating <= 5:
            return JsonResponse({"error": "rating must be between 1 and 5."}, status=400)

        raw_age = data.get("account_age_days", 0)
        try:
            account_age = int(raw_age)
        except (ValueError, TypeError):
            return JsonResponse({"error": "account_age_days must be an integer."}, status=400)
        if not 0 <= account_age <= 36500:
            return JsonResponse({"error": "account_age_days must be between 0 and 36500."}, status=400)

        out = score_single(
            movie_id, user_id, rating, review_text, account_age,
            ip=data.get("ip_address") or request.META.get("REMOTE_ADDR"),
            device=data.get("device_id")
        )
        return JsonResponse({
            "status": "success",
            "movie": movie_id,
            "prediction": out
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid or malformed JSON payload."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Internal prediction error: {str(e)}"}, status=500)


@require_GET
def api_trust(request, product_id):
    t = get_object_or_404(TrustScore.objects.select_related("movie"), movie_id=product_id)
    return JsonResponse({
        "product_id": product_id,
        "title": t.movie.title,
        "genre": t.movie.genre,
        "verified_trust_score": t.trust_score,
        "grade": t.grade,
        "raw_avg": round(t.raw_avg, 2),
        "verified_avg": round(t.verified_avg, 2),
        "rating_inflation": round(t.rating_inflation, 2),
        "reviews": t.n_reviews,
        "flagged_fake": t.n_flagged,
        "fake_share": round(t.fake_share, 3),
        "manipulated": t.manipulated,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None
    })
