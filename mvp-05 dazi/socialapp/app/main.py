from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.common.db import init_db
from app.auth.routes import router as auth_router
from app.users.routes import router as users_router
from app.posts.routes import router as posts_router
from app.social.routes import router as social_router
from app.notifications.ws import notify_ws

app = FastAPI(title=settings.APP_NAME)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(posts_router, prefix="/posts", tags=["posts"])
app.include_router(social_router, prefix="/social", tags=["social"])

@app.on_event("startup")
async def startup():
    await init_db()

# WebSocket（简单示例）
@app.websocket("/ws/notify")
async def ws_notify(ws: WebSocket):
    await notify_ws(ws)
