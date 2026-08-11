# Deploying The Kun Algorithm to the cloud

Stack, and why: **Neon** (Postgres) + **Render** (FastAPI backend) + **Vercel**
(Next.js frontend). All three have real free tiers as of August 2026 — no
card required to get started, and nothing here forces a paid plan. Sources
checked while writing this: [Render Postgres pricing](https://kuberns.com/blogs/render-postgres-pricing-setup-limits/),
[Render FastAPI deploy guide](https://render.com/articles/fastapi-deployment-options),
[Neon vs. Supabase free tiers](https://neon.com/faqs/managed-postgres-databases-free-tier).

One thing worth knowing up front: **Render's own free Postgres deletes your
data after 30 days.** That's a dealbreaker for a trading ledger you want to
keep, so this guide uses **Neon** for the database instead — its free tier
has no expiration, it just scales its compute to zero after 5 minutes of
inactivity and wakes up in milliseconds on the next request. Render's free
web service does something similar (spins down when idle, cold-starts on
the next hit) — fine for a dashboard you check a few times a day, not fine
if you later want a background job firing signals while nobody's looking at
it. Keep that in mind as this grows.

---

## 0. Push this project to GitHub

Render and Vercel both deploy by watching a GitHub repo.

```bash
cd the-kun-algorithm
git init
git add .
git commit -m "Initial The Kun Algorithm scaffold"
```

Create an empty repo on GitHub (via github.com/new), then:

```bash
git remote add origin https://github.com/<you>/the-kun-algorithm.git
git branch -M main
git push -u origin main
```

---

## 1. Database — Neon (free, no expiration)

1. Go to [neon.tech](https://neon.tech) and sign up (GitHub login is fastest).
2. Create a new project — name it `the-kun-algorithm`.
3. Neon gives you a connection string immediately, something like:
   `postgresql://<user>:<password>@<host>/<db>?sslmode=require`
4. Copy it — you'll paste it into Render in the next step.

That's it. No manual schema step needed: the backend runs
`Base.metadata.create_all()` on startup and creates every table itself the
first time it boots against this database.

---

## 2. Backend — Render

1. Go to [render.com](https://render.com) and sign up.
2. **New → Blueprint**, connect your GitHub account, and pick the
   `emotionless-executioner` repo. Render will read `render.yaml` at the repo
   root and propose one service: `emotionless-executioner-api`.
3. Before the first deploy, set the environment variable it asks for:
   - `DATABASE_URL` → the Neon connection string from step 1.
   - (leave `CORS_ORIGINS` as-is for now — you'll update it in step 4.)
4. Deploy. Render will run `pip install -r requirements.txt` from
   `backend/`, then start the app with `uvicorn app.main:app --host 0.0.0.0
   --port $PORT`.
5. Once it's live, note the URL Render gives you, e.g.
   `https://emotionless-executioner-api.onrender.com`. Confirm it's up:

   ```bash
   curl https://emotionless-executioner-api.onrender.com/api/health
   # {"status":"ok","system":"The Kun Algorithm"}
   ```

If you'd rather not use the Blueprint file, the equivalent manual setup is:
**New → Web Service** → pick the repo → Root Directory `backend` → Build
Command `pip install -r requirements.txt` → Start Command
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

---

## 3. Frontend — Vercel

1. Go to [vercel.com/new](https://vercel.com/new), connect GitHub, and
   import the same repo.
2. Vercel needs to know the frontend isn't at the repo root: set **Root
   Directory** to `frontend`.
3. Add an environment variable: `NEXT_PUBLIC_API_BASE_URL` →
   your Render URL from step 2 (e.g.
   `https://emotionless-executioner-api.onrender.com`).
4. Deploy. Vercel runs `npm install && npm run build` for you — this is
   also the first real TypeScript/build check this project gets, since the
   sandbox this was built in doesn't have registry access to run that
   locally. If it fails, the Vercel build log will show exactly which file
   and line; send that to me and I'll fix it.
5. You'll get a URL like `https://emotionless-executioner.vercel.app`.

---

## 4. Close the loop — CORS

Right now the backend only allows `http://localhost:3000` to call it. Go
back to Render → your service → **Environment**, and update:

```
CORS_ORIGINS=https://emotionless-executioner.vercel.app
```

(comma-separate multiple origins if you want both local dev and prod
working at once, e.g. `http://localhost:3000,https://emotionless-executioner.vercel.app`).
Redeploy the backend (Render does this automatically on env var save).

---

## 5. First trade

Open your Vercel URL. The Dual-Gate Ledger and Action Feed will be empty —
log your first position through the Trade Execution UI (or `curl`, same as
local dev):

```bash
curl -X POST https://emotionless-executioner-api.onrender.com/api/trades \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AMD","action":"BUY","shares":10,"price":140.00,"tier_name":"GROWTH"}'
```

Refresh the dashboard — it should show up in the ledger with a live signal
within a few seconds.

---

## Ongoing costs

Everything above is free at this scale: Neon's free tier (0.5GB/project),
Render's free web service tier, and Vercel's Hobby tier. You'll want to
upgrade if/when: Neon's compute limit gets tight (more tickers, more
frequent polling), Render's cold-start delay bothers you enough to want an
always-on instance (~$7/mo on Render's cheapest paid web service tier), or
you outgrow Vercel's Hobby usage caps. None of that is needed to get this
running today.
