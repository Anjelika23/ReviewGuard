# 🛡️ ReviewGuard — AI Trust Analytics & Fake Review Detection

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Django 5.0+](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-orange.svg)](https://scikit-learn.org/)
[![Vercel Ready](https://img.shields.io/badge/Vercel-Ready-black.svg)](https://vercel.com)

**ReviewGuard** is an end-to-end machine learning web application that detects coordinated bot spam, incentivized 5★ campaigns, and competitor-sabotage 1★ reviews. It computes a **Verified Trust Score** that counteracts rating distortion and restores consumer confidence in online reviews.

---

## 🌟 Key Features

- **Dual-Feature Stacking ML Architecture**: Combines TF-IDF NLP n-gram stylometry with 19 behavioral velocity indicators (account maturity, review frequency, consensus deviation, text duplication, and sentiment-rating contradiction).
- **Bayesian Verified Trust Scores**: Calculates credibility-weighted star ratings shrunken toward consensus, stripping out artificial rating inflation and malicious downvoting.
- **Real-Time Interactive Playground**: Test and evaluate individual reviews with 1-click attack simulation presets (Bot Farm Spam, Competitor Sabotage, Genuine Nuanced).
- **Modern Responsive UI**: Dark & Light theme switcher, interactive rating distribution bars, live filtering/sorting, search toolbar, and risk badges.
- **Production-Ready REST API**: Complete with `/health/` orchestration probes, stateless `/api/predict/` risk scoring, and `/api/trust/<id>/` trust summaries.
- **Zero-Friction Vercel Deployment**: Pre-configured with `vercel.json`, WhiteNoise static file serving, and automatic `/tmp` SQLite handling for serverless runtimes.

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

## ☁️ Vercel Deployment

ReviewGuard is pre-configured for Vercel Serverless Functions:

1. Push your changes to GitHub:
   ```bash
   git push origin main
   ```
2. In your Vercel Dashboard, import or connect the repository.
3. Vercel automatically detects `vercel.json` and builds the serverless WSGI application.
4. Your live app is available at `https://your-project.vercel.app`.

---

## 🔌 REST API Reference

### 1. Health Probe
- **Endpoint**: `GET /health/`
- **Description**: Verifies service status, database connectivity, and ML model loading.
```bash
curl -X GET https://your-project.vercel.app/health/
```

### 2. Predict Review Authenticity
- **Endpoint**: `POST /api/predict/`
- **Description**: Real-time fake-review classification with risk probability and explainability reasons.
```bash
curl -X POST https://your-project.vercel.app/api/predict/ \
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
    "fake_probability": 0.9286,
    "fake_percentage": 92.9,
    "is_fake": true,
    "risk_level": "Critical Risk",
    "label": "Likely fake",
    "reasons": [
      "Very new account (1 day old)",
      "Generic, templated superlative language",
      "Short extreme rating with no specifics"
    ]
  }
}
```

### 3. Movie Trust Score Summary
- **Endpoint**: `GET /api/trust/<product_id>/`
- **Description**: Returns verified trust score, raw rating, verified rating, and manipulation flag.
```bash
curl -X GET https://your-project.vercel.app/api/trust/M001/
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
