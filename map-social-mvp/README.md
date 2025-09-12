# Map Social MVP

A full‑stack starter for a location‑based social app where users meet at real places (restaurants, climbing gyms, ski resorts, cities, running routes, hiking trails) and coordinate sessions.

## Stack

- **Backend**: FastAPI + SQLModel (SQLite), JWT auth, file uploads (local), simple search by bbox/radius.
- **Frontend**: React + Vite + TypeScript + Leaflet (OpenStreetMap tiles).
- **Auth**: Email + password (demo), JWT stored in localStorage.
- **MVP Features**:
  - Sign up / Sign in
  - Map with markers for **Locations**
  - Location drawer with **Posts** (threads) + **Comments**
  - Create **Sessions** (meetups) with time window & activity tag
  - Photo uploads (local folder) for posts
  - Basic search (by map viewport) and activity filters

> ⚠️ This MVP uses **OpenStreetMap tile server** for development only.
For production, use a proper tiles provider (MapTiler/Mapbox/self-hosted) per their ToS.

## Quickstart

### 1) Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 2) Frontend
```bash
cd frontend
npm i
npm run dev
```
App: http://localhost:5173

### Seed demo data
```bash
cd backend && source .venv/bin/activate
python -m app.seeds
```

## Project Structure

```
backend/
  app/
    main.py
    db.py
    models.py
    schemas.py
    auth.py
    deps.py
    seeds.py
    routers/
      auth.py
      locations.py
      posts.py
      comments.py
      sessions.py
      upload.py
    static/uploads/
  requirements.txt
  .env.example

frontend/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  tailwind.config.js
  postcss.config.js
  public/
  src/
    main.tsx
    index.css
    App.tsx
    lib/api.ts
    lib/auth.ts
    components/
      MapView.tsx
      LocationDrawer.tsx
      PostFeed.tsx
      NewPostModal.tsx
      SessionPanel.tsx
      AuthGate.tsx
```

## Notes
- This is a teaching/starter template, not a production system.
- Add rate limiting, CSRF protections, email verification, image moderation, observability before launch.
- Consider Postgres + PostGIS and a managed object storage for images in production.
