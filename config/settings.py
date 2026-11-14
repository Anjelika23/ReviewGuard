import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TESTING = "test" in sys.argv or os.getenv("TESTING", "0") == "1"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-local-development-key-change-before-deploy")
DEBUG = os.getenv("DJANGO_DEBUG", "0").lower() in {"1", "true", "yes"}

# Allow all hosts by default in development or wildcard, or parse comma-separated hosts
_allowed = os.getenv("DJANGO_ALLOWED_HOSTS", "*")
if _allowed == "*" or not _allowed:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]
    if "*" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.extend([".vercel.app", ".now.sh", "localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "reviews",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]

# Inject WhiteNoise if installed
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")
except ImportError:
    pass

MIDDLEWARE.extend([
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
])

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

# Vercel serverless environment support
IS_VERCEL = "VERCEL" in os.environ or "VERCEL_ENV" in os.environ or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
if IS_VERCEL:
    # /var/task is read-only on Vercel; copy sqlite db to /tmp/db.sqlite3 so it is writable
    db_tmp = Path("/tmp/db.sqlite3")
    db_src = BASE_DIR / "db.sqlite3"
    if not db_tmp.exists() and db_src.exists():
        try:
            import shutil
            shutil.copy2(db_src, db_tmp)
        except Exception:
            pass
    db_path = db_tmp if db_tmp.exists() else db_src
else:
    db_path = BASE_DIR / "db.sqlite3"

# Database Configuration: DATABASE_URL / POSTGRES_URL > DB_NAME > SQLite
database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if database_url:
    try:
        import dj_database_url
        DATABASES = {"default": dj_database_url.config(default=database_url, conn_max_age=600)}
    except ImportError:
        import urllib.parse as up
        url = up.urlparse(database_url)
        DATABASES = {"default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path[1:],
            "USER": url.username or "postgres",
            "PASSWORD": url.password or "",
            "HOST": url.hostname or "localhost",
            "PORT": str(url.port or 5432),
        }}
elif os.getenv("DB_NAME"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql", "NAME": os.environ["DB_NAME"],
        "USER": os.getenv("DB_USER", "postgres"), "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"), "PORT": os.getenv("DB_PORT", "5432"),
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": db_path}}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MODEL_PATH = BASE_DIR / "models" / "fake_review_detector.joblib"
METRICS_PATH = BASE_DIR / "models" / "metrics.json"
FAKE_THRESHOLD = float(os.getenv("FAKE_THRESHOLD", "0.5"))

# Security headers & Reverse proxy support (prevents 502 Bad Gateway / SSL redirect loop)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

if DEBUG or TESTING:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "0") == "1"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1") == "1"
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "1") == "1"

# CSRF Trusted Origins for cross-origin or deployed web views
_csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        "https://*.vercel.app",
        "https://*.now.sh",
        "https://*.onrender.com",
        "https://*.railway.app",
        "https://*.herokuapp.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

