import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from PIL import Image
import aiofiles

from ..deps import get_current_user

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads"))

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/image")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only images allowed")
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    fname = f"{ts}{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)

    # Save to disk
    async with aiofiles.open(fpath, "wb") as out:
        content = await file.read()
        await out.write(content)

    # Try to open and make a modest thumbnail to ensure valid image
    try:
        im = Image.open(fpath)
        im.thumbnail((1600, 1600))
        im.save(fpath)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")

    return {"url": f"/static/uploads/{fname}"}
