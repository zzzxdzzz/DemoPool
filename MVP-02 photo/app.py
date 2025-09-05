## app.py（Flask 主程序）

from flask import Flask, render_template, request, send_file
from processor import process_passport_photo
from io import BytesIO
from PIL import Image
import os
from datetime import datetime

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    if "photo" not in request.files:
        return "No file uploaded", 400
    file = request.files["photo"]
    if file.filename == "":
        return "Empty filename", 400

    img = Image.open(file.stream).convert("RGB")
    out_img = process_passport_photo(img)

    # 嵌入 300 DPI（2x2 英寸 @ 600 px/英寸；我们导出 1200x1200 px）
    buf = BytesIO()
    out_img.save(buf, format="JPEG", quality=95, dpi=(300, 300))
    buf.seek(0)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"us_passport_{stamp}.jpg"
    return send_file(
        buf,
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=fname
    )

if __name__ == "__main__":
    # 仅开发用途：不要用于生产
    app.run(debug=True)
