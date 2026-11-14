# 🛡️ ReviewGuard — AI Trust Analytics & Fake Review Detection

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Django 5.0+](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-orange.svg)](https://scikit-learn.org/)
[![Deploy on Render](https://img.shields.io/badge/Deploy%20on-Render-46E3B7.svg)](https://render.com)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

**ReviewGuard** is an end-to-end machine learning web application that detects coordinated bot spam, incentivized 5★ campaigns, and competitor-sabotage 1★ reviews. It computes a **Verified Trust Score** that counteracts rating distortion and restores consumer confidence in online reviews.

---

## 🌟 Key Features

- **Dual-Feature Stacking ML Architecture**: Combines TF-IDF NLP n-gram stylometry with 19 behavioral velocity indicators (account maturity, review frequency, consensus deviation, text duplication, and sentiment-rating contradiction).
- **Bayesian Verified Trust Scores**: Calculates credibility-weighted star ratings shrunken toward consensus, stripping out artificial rating inflation and malicious downvoting.
- **Real-Time Interactive Playground**: Test and evaluate individual reviews with 1-click attack simulation presets (Bot Farm Spam, Competitor Sabotage, Genuine Nuanced).
- **Modern Responsive UI**: Dark & Light theme switcher, interactive rating distribution bars, live filtering/sorting, search toolbar, and risk badges.
- **Production-Ready REST API**: Complete with `/health/` orchestration probes, stateless `/api/predict/` risk scoring, and `/api/trust/<id>/` trust summaries.
- **Zero-Friction Cloud Deployment**: Pre-configured with `render.yaml`, `build.sh`, `Procfile`, `Dockerfile`, and `docker-compose.yml` to prevent common **502 Bad Gateway** deployment crashes.

---

## 🚨 Fixing 502 Bad Gateway in Cloud Deployments

If your deployment on **Render**, **Railway**, or **Heroku** returns a **502 Bad Gateway**, this repository now provides built-in fixes for the primary root causes:

| Root Cause | Problem | How ReviewGuard Solves It |
| :--- | :--- | :--- |
| **Missing WSGI Server** | `requirements.txt` lacked `gunicorn`, so the web container immediately crashed on startup. | Added `gunicorn>=21.2.0` and `Procfile` (`gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`). |
| **Missing Static Files** | `whitenoise` was missing, causing static assets to fail in `DEBUG=False`. | Added `whitenoise>=6.6.0` with auto-injection in Django middleware. |
| **SSL Redirect Loop** | Cloud reverse proxies terminate SSL at the edge; Django's default `SECURE_SSL_REDIRECT=1` caused infinite 301 redirects, failing health checks. | Added `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` and disabled redirect during testing or internal HTTP proxying. |
| **ALLOWED_HOSTS Rejection** | Cloud domains (e.g. `*.onrender.com`) were blocked by strict host filtering. | Auto-configured `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to support Render, Railway, and localhost out-of-the-box. |
| **Empty Database on Ephemeral Disk** | SQLite tables and sample datasets were not automatically migrated or seeded on cold start. | Added `build.sh` and `--if-empty` flag to `import_reviews`, ensuring migrations and initial data are populated on build. |
| **Missing Health Probe** | Reverse proxies could not verify container readiness. | Added a lightweight `/health/` and `/healthz` endpoint returning HTTP 200 OK without database overhead. |

---

## 🏗️ Architecture: Dual-Feature Stacking

ReviewGuard avoids relying solely on text (which is easily fooled by LLMs) or solely on metadata (which misses semantic cues). Instead, it uses a **2-stage stacked classifier**:

```
Raw Review Input (Text + Metadata)
  ├── 1. Text Model: TF-IDF (1-2 grams) + Logistic Regression ➔ P(fake | text)
  └── 2. Behavioral Extractor: 19 Signals (Account age, Posting velocity, Dev from consensus, Duplicates)
        │
        └── Combined Feature Vector ➔ HistGradientBoosting Meta-Classifier ➔ Final P(fake)
```

### Top Evaluated Signals:
1. `user_extreme_share`: Accounts posting exclusively 1★ or 5★ reviews.
2. `dup_text_count`: Templated review phrases replicated across accounts.
3. `generic_hits`: Overuse of superlative hype words (`"best movie ever"`, `"must watch 10/10"`).
4. `sentiment_rating_gap`: Text sentiment conflicting with the assigned star rating.
5. `is_new_account` & `account_age_days`: Spikes in reviews originating from newly registered accounts.

---

## 🚀 Quickstart: Local Setup

### 1. Clone & Setup Virtual Environment

**Windows (PowerShell):**
```powershell
git clone https://github.com/Anjelika23/ReviewGuard.git
cd ReviewGuard
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
git clone https://github.com/Anjelika23/ReviewGuard.git
cd ReviewGuard
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Initialize Database & Run Server

```bash
# Run database migrations
python manage.py migrate

# Seed sample movies and reviews (auto-scores them)
python manage.py import_reviews

# Run tests
python manage.py test

# Start the development server
python manage.py runserver
```

Open your browser to: **http://127.0.0.1:8000/**

---

## ☁️ Deployment Guide

### Option 1: Deploy on Render (Recommended)

1. Fork or push this repository to your GitHub account.
2. Go to [Render Dashboard](https://dashboard.render.com/) and click **New + > Blueprint** (or **New Web Service**).
3. Connect your repository.
4. Render will automatically read `render.yaml`:
   - **Build Command**: `bash build.sh`
   - **Start Command**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   - **Health Check Path**: `/health/`
5. Click **Apply / Deploy**.

### Option 2: Deploy with Docker

```bash
# Build the Docker image
docker build -t reviewguard .

# Run container on port 8000
docker run -p 8000:8000 -e DJANGO_DEBUG=1 reviewguard

# Or using docker-compose
docker compose up --build
```

---

## 🔌 REST API Reference

ReviewGuard includes REST endpoints for programmatic integrations:

### 1. Health Probe
- **Endpoint**: `GET /health/`
- **Description**: Verifies service status, database connectivity, and ML model loading.
```bash
curl -X GET https://your-domain/health/
```

### 2. Predict Review Authenticity
- **Endpoint**: `POST /api/predict/`
- **Description**: Real-time fake-review classification with risk probability and explainability reasons.
```bash
curl -X POST https://your-domain/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "movie": "M001",
    "user_id": "U_eval_01",
    "rating": 5,
    "review_text": "Best movie ever! 10/10 masterpiece, must watch, nothing negative to say!",
    "account_age_days": 1
  }'
```
**Response (200 OK):**
```json
{
  "status": "success",
  "movie": "M001",
  "prediction": {
    "fake_probability": 0.8612,
    "fake_percentage": 86.1,
    "is_fake": true,
    "risk_level": "Critical Risk",
    "label": "Likely fake",
    "reasons": [
      "Generic, templated superlative language",
      "Short extreme rating with no specifics",
      "Very new account (1 day old)"
    ]
  }
}
```

### 3. Movie Trust Score Summary
- **Endpoint**: `GET /api/trust/<product_id>/`
- **Description**: Returns verified trust score, raw rating, verified rating, and manipulation flag.
```bash
curl -X GET https://your-domain/api/trust/M001/
```

---

## 🛠️ Management Commands

```bash
# Import and score reviews from data/reviews.csv
python manage.py import_reviews

# Import only if database is empty (ideal for deploy hooks)
python manage.py import_reviews --if-empty

# Rescore all database reviews without re-importing
python manage.py score_reviews

# Retrain and evaluate ML model
python manage.py train_model

# Create administrator account
python manage.py createsuperuser
```

---

## 📄 License & Attribution

Designed and engineered for transparent consumer trust intelligence. Licensed under the MIT License.
