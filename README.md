# Ahtara listings backend

Django owns the schema, migrations and admin. FastAPI serves the public API. One process: `uvicorn api.main:app`.

## First run
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations listings     # initial migration (not committed yet; commit it afterwards)
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo                   # optional demo data
uvicorn api.main:app --reload
```
- API docs: http://localhost:8000/docs  ·  Admin: http://localhost:8000/admin/
- Tests: `pytest`
- Phone-only testing and Vercel deploy: see DEPLOY.md
- Self-hosting: `cp .env.example .env`, edit it, then `docker compose up -d --build`
  (run `makemigrations` once locally first and commit `listings/migrations/0001_initial.py`).

## Trust model
| Tier | Meaning | Who sets it |
|---|---|---|
| 0 unverified | entered but unvetted | manual |
| 1 source_listed | found in a named source (e.g. OSM) | importer |
| 2 registry_checked | matched to DOT / DTI / SEC record | reviewer, in admin |
| 3 owner_verified | owner proved control of the site | claim flow |

- Public API shows only `published` listings at or above `PUBLIC_MIN_TIER` (default 1).
- Phone and email are returned only for tier 3.
- Imports (`listings.services.upsert_listing`) never overwrite owner-verified data or lower a tier.
- Each listing returns its sources' attribution/licence text. The website must display it (OSM requires it).

## Claim flow
1. `POST /v1/listings/{slug}/claims {claimant_email}` returns a token + instructions.
2. Owner adds `<meta name="ahtara-site-verification" content="TOKEN">` to their home page.
3. `POST /v1/claims/{id}/verify {token}` fetches the page (SSRF-guarded) and promotes the listing to tier 3.
4. `method=manual` claims wait in the admin (Claims → Approve) after you've checked documents.

## Not built yet (next steps)
- Importers: OSM/Overpass for the Philippines, DOT/LGU list CSVs (call `upsert_listing`).
- Rate limiting on the public POST endpoints (put it in the reverse proxy or add slowapi).
- Email sending for outreach and claim confirmation; staleness re-check job; PostGIS for radius search.
- Auth for owner edits after verification.
# WebAhtara
