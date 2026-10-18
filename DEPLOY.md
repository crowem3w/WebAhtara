# Test and deploy without a laptop

## A. Test on your phone (Termux + proot Ubuntu), SQLite, no database server needed
In Termux:
```bash
pkg update && pkg install proot-distro unzip
termux-setup-storage                       # allow storage access once
proot-distro install ubuntu
proot-distro login ubuntu --bind ~/storage/downloads:/mnt/dl
```
Inside Ubuntu:
```bash
apt update && apt install -y python3 python3-venv python3-pip unzip
cd ~ && unzip /mnt/dl/ahtara-backend.zip && cd ahtara-backend
./setup.sh                                  # venv, install, migrations, demo data, tests
python manage.py createsuperuser
uvicorn api.main:app --host 127.0.0.1 --port 8000
```
Open Chrome on the phone: http://127.0.0.1:8000/docs (API) and http://127.0.0.1:8000/admin/ (admin).

## B. Put the public API on Vercel (Hobby, free)
Vercel has no persistent disk, so it needs an external Postgres. Free options: Neon (Vercel Marketplace) or Supabase.
1. Create a Neon database and copy its **pooled** connection string (ends `?sslmode=require`).
2. From Termux/Ubuntu, create the tables in that database (once, and after every model change):
   ```bash
   export DATABASE_URL='postgres://...neon...?sslmode=require'
   python manage.py migrate && python manage.py createsuperuser && python manage.py seed_demo
   ```
3. Commit the project (including `listings/migrations/`) to a GitHub repo.
4. vercel.com → Add New Project → import the repo. Framework is detected as FastAPI. Set environment variables:
   `DATABASE_URL`, `DJANGO_SECRET_KEY` (long random), `DJANGO_DEBUG=0`,
   `DJANGO_ALLOWED_HOSTS=your-project.vercel.app`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-project.vercel.app`,
   `CORS_ORIGINS=https://your-site.vercel.app`.
5. Deploy. Check `https://your-project.vercel.app/docs` and `/v1/listings`.

## Admin: where to run it
The admin is mounted in the same app, so it also works at `/admin/` on Vercel, but that is the part I'm least sure about on serverless.
The safe route: run the admin and all imports from Termux with `DATABASE_URL` pointing at the same Neon database,
and let Vercel serve only the public API.
