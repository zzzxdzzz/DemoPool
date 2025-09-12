import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .db import init_db
from .routers import auth, locations, posts, comments, sessions, upload

load_dotenv()

app = FastAPI(title=os.getenv("APP_NAME", "MapSocial"))

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploaded images
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
def on_startup():
    init_db()

# Routers
app.include_router(auth.router)
app.include_router(locations.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(sessions.router)
app.include_router(upload.router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
