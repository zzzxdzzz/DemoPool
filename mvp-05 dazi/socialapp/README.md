# SocialApp (FastAPI MVP)

## 1) 克隆 & 启动
```bash
cp .env.example .env
# 方式A：本机
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 方式B：Docker Compose
# Docker 构建镜像

docker build -t socialapp:latest .
docker run --rm -it -p 8000:8000 --env-file .env socialapp:latest


Docker Compose（热更新开发）

docker compose up --build

```

接口文档： http://localhost:8000/docs

## 2) 基础流程（用 /docs 调试）
1. 注册：POST /auth/register  { email, username, password } -> 返回 access_token（Bearer Token）
2. 登录：POST /auth/login  { email, password } -> 返回 access_token
3. 带上 Authorization: Bearer <token>
4. 我：GET /users/me
5. 发帖：POST /posts  { content }
6. 关注：POST /social/follow/{user_id}
7. 关注流：GET /social/feed
8. 评论：POST /posts/{post_id}/comments  { content }
9. 点赞：POST /posts/{post_id}/like

## 3) 下一步可扩展
- 媒体上传（本地→MinIO/S3），帖子加图片/视频
- 通知落库 + Celery 异步任务 + WebSocket 推送
- 推荐流：简单 TF-IDF / 协同过滤 / 向量检索
- 搜索：PostgreSQL ILIKE → OpenSearch
- 权限与限流、审计日志、内容审核
- 数据迁移：Alembic（生产必配）
