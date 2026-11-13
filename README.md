# ReviewGuard — Fake Review Detection & Trust Scoring

A Django web application that estimates fake-review risk using review text and behavioural signals, then calculates a credibility-weighted movie trust score. This is a decision-support prototype: a model prediction is not proof that a reviewer acted fraudulently.

## Features

- Movie dashboard with raw ratings, verified ratings, trust grades and model metrics.
- Review analysis form and JSON prediction endpoint.
- Dual-feature ML model: TF-IDF text probability + behavioural/NLP features.
- Review-level explanations and movie-level trust scores.
- SQLite by default; optional PostgreSQL through environment variables.

## Requirements

- Python 3.10+ (3.11 recommended)
- pip and a virtual environment

## Run locally (Windows PowerShell)

```powershell
cd config
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py import_reviews
python manage.py runserver
```

Open http://127.0.0.1:8000/ . SQLite is used automatically, so PostgreSQL is not needed for the beginner setup. The project reads environment variables from your terminal; Django does not automatically load `.env`. On macOS/Linux, create/activate the environment with `python3 -m venv .venv` and `source .venv/bin/activate`.

The default install intentionally omits optional spaCy and PostgreSQL packages. Install `psycopg2-binary` only if you configure PostgreSQL. If model scoring fails because the bundled model was trained with a different scikit-learn version, retrain it using the included data: `python -m ml.train --csv data/reviews.csv --out models`, then run `python manage.py score_reviews`. Model files created by joblib should only be loaded from trusted sources.

## Useful commands

```bash
python manage.py import_reviews          # import sample data and score it
python manage.py import_reviews --keep   # append sample data without wiping existing reviews
python manage.py score_reviews           # rescore all stored reviews
python manage.py train_model             # train and evaluate model
python manage.py createsuperuser         # optional Django admin login
```

## API

`POST /api/predict/` accepts JSON (Django CSRF protection applies to browser-session requests):

```json
{
  "movie": "M013",
  "user_id": "U_demo",
  "rating": 5,
  "review_text": "A thoughtful film with memorable performances.",
  "account_age_days": 120
}
```

`GET /api/trust/M013/` returns the stored trust summary for a movie.

## Data and model limitations

The included CSVs are sample/demo data. Model metrics are specific to the included dataset and evaluation split; they should not be presented as real-world performance. Behavioural features depend on the history available to the application. For production use, collect consented, representative, correctly labelled data; evaluate by time/user/product to reduce leakage; add authentication, rate limiting, monitoring, privacy controls and human review before enforcement.

## GitHub

Create an empty repository on GitHub. From this `config` directory run:

```bash
git init
git add .
git commit -m "Initial ReviewGuard project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

For future updates: `git add .`, `git commit -m "Describe your changes"`, then `git push`. Never commit `.env`, database files, passwords or private user data.
