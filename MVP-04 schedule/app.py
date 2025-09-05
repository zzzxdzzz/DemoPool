\
import os
import io
import base64
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from flask import (
    Flask, render_template, request, redirect, url_for, send_file, jsonify, session, flash
)
from werkzeug.utils import secure_filename

from dotenv import load_dotenv
from PIL import Image

# --- Load env & config ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())
TIMEZONE = "America/New_York"

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set. Add it to your .env")

# OpenAI (Responses API)
try:
    from openai import OpenAI
    oai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception as e:
    print("OpenAI SDK import error:", e)
    oai_client = None

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = SECRET_KEY

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Simple event container ---
@dataclass
class EventItem:
    title: str
    date: str         # YYYY-MM-DD
    start_time: str   # HH:MM (24h)
    end_time: str     # HH:MM (24h)
    location: str = ""
    notes: str = ""

# --- Routes ---

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            flash("Please choose an image file.", "error")
            return redirect(url_for("index"))
        if not allowed_file(file.filename):
            flash("Unsupported file type.", "error")
            return redirect(url_for("index"))
        image_id = str(uuid4())
        ext = os.path.splitext(secure_filename(file.filename))[1].lower()
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")
        file.save(save_path)
        session["image_ext"] = ext
        return redirect(url_for("annotate", image_id=image_id))
    return render_template("index.html")

@app.route("/annotate/<image_id>")
def annotate(image_id):
    ext = session.get("image_ext", ".png")
    filename = f"{image_id}{ext}"
    image_url = url_for("uploaded_file", filename=filename)
    return render_template("annotate.html", image_id=image_id, image_url=image_url)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_file(os.path.join(UPLOAD_DIR, filename))

@app.route("/submit_mask/<image_id>", methods=["POST"])
def submit_mask(image_id):
    data = request.get_json(silent=True) or {}
    mask_data_url = data.get("mask")
    if not mask_data_url:
        return jsonify({"error": "No mask received"}), 400

    # Load original
    ext = session.get("image_ext", ".png")
    orig_path = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")
    if not os.path.exists(orig_path):
        return jsonify({"error": "Original image not found"}), 404

    # Decode mask
    try:
        header, b64data = mask_data_url.split(",", 1)
        mask_bytes = base64.b64decode(b64data)
        mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")
    except Exception as e:
        return jsonify({"error": f"Mask decode error: {e}"}), 400

    # Open original, apply mask (keep only brushed parts)
    orig = Image.open(orig_path).convert("RGBA")
    if mask_img.size != orig.size:
        mask_img = mask_img.resize(orig.size)

    # Binarize mask
    mask_bin = mask_img.point(lambda p: 255 if p > 8 else 0).convert("L")

    # Compose result
    result = Image.new("RGBA", orig.size, (255, 255, 255, 0))
    result.paste(orig, (0, 0), mask_bin)

    masked_path = os.path.join(PROCESSED_DIR, f"{image_id}_masked.png")
    result.save(masked_path)

    return jsonify({"ok": True, "masked_url": url_for("processed_file", filename=f"{image_id}_masked.png")})

@app.route("/processed/<path:filename>")
def processed_file(filename):
    return send_file(os.path.join(PROCESSED_DIR, filename))

@app.route("/extract/<image_id>", methods=["POST"])
def extract(image_id):
    # Use OpenAI Vision-capable model to parse the masked image into events
    ext = session.get("image_ext", ".png")
    masked_path = os.path.join(PROCESSED_DIR, f"{image_id}_masked.png")
    if not os.path.exists(masked_path):
        flash("No masked image found. Please annotate first.", "error")
        return redirect(url_for("annotate", image_id=image_id))

    # Encode masked image
    with open(masked_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    system_prompt = (
        "You are an expert scheduler. Extract **only** rehearsal/performance events that are visible in the image. "
        "Ignore unrelated rows or text outside the brushed region. "
        "Return each event with: title, date (YYYY-MM-DD), start_time (24h HH:MM), end_time (24h HH:MM), "
        "location (if present), notes (free text if present). If end time is missing, infer a reasonable end by "
        "adding 90 minutes. If date has no year, infer the most likely upcoming year based on today's date. "
        f"Default timezone is {TIMEZONE}. Output must strictly follow the provided JSON schema."
    )

    # JSON schema for responses API
    json_schema = {
        "name": "events_schema",
        "schema": {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                            "start_time": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
                            "end_time": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
                            "location": {"type": "string"},
                            "notes": {"type": "string"}
                        },
                        "required": ["title", "date", "start_time", "end_time"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["events"],
            "additionalProperties": False
        }
    }

    events_json = {"events": []}

    if oai_client and OPENAI_API_KEY:
        try:
            resp = oai_client.responses.create(
                model=OPENAI_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Extract the rehearsal events from this image."},
                            {"type": "input_image", "image_data": b64, "mime_type": "image/png"},
                        ],
                    },
                ],
                response_format={"type": "json_schema", "json_schema": json_schema},
            )
            # Responses API returns structured output under output[0].content[0].
            content_blocks = resp.output[0].content if hasattr(resp, "output") else []
            raw_json = None
            for block in content_blocks:
                if block.get("type") == "output_text":
                    raw_json = block.get("text")
                elif block.get("type") == "json":
                    raw_json = block.get("json")
            if raw_json is None:
                # Fallback: try 'output_text' top-level
                raw_json = getattr(resp, "output_text", None)

            if isinstance(raw_json, str):
                events_json = json.loads(raw_json)
            elif isinstance(raw_json, dict):
                events_json = raw_json
        except Exception as e:
            print("OpenAI error:", e)
            flash(f"OpenAI error: {e}", "error")
    else:
        flash("OpenAI client not configured; using empty result.", "warning")

    # Persist and go to review
    session[f"events_{image_id}"] = events_json
    return redirect(url_for("review", image_id=image_id))

@app.route("/review/<image_id>", methods=["GET", "POST"])
def review(image_id):
    key = f"events_{image_id}"
    if request.method == "POST":
        # collect rows from form
        rows = []
        count = int(request.form.get("row_count", "0"))
        for i in range(count):
            prefix = f"rows[{i}]"
            title = request.form.get(f"{prefix}[title]", "").strip()
            date = request.form.get(f"{prefix}[date]", "").strip()
            start_time = request.form.get(f"{prefix}[start_time]", "").strip()
            end_time = request.form.get(f"{prefix}[end_time]", "").strip()
            location = request.form.get(f"{prefix}[location]", "").strip()
            notes = request.form.get(f"{prefix}[notes]", "").strip()
            if title and date and start_time and end_time:
                rows.append(EventItem(title, date, start_time, end_time, location, notes))
        session[key] = {"events": [asdict(r) for r in rows]}
        flash("Events updated.", "success")
        return redirect(url_for("review", image_id=image_id))

    events_json = session.get(key, {"events": []})
    return render_template("review.html", image_id=image_id, events=events_json.get("events", []), timezone=TIMEZONE)

def fold_ical_line(line: str, limit: int = 75) -> str:
    # iCalendar folding (CRLF + space)
    out = []
    while len(line) > limit:
        out.append(line[:limit])
        line = " " + line[limit:]
    out.append(line)
    return "\r\n".join(out)

def make_ics(events: List[Dict[str, Any]], calendar_name: str = "Orchestra Rehearsal (from image)") -> bytes:
    # Build a minimal but valid ICS (RFC5545). Google Calendar accepts TZID without VTIMEZONE.
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Image2Cal MVP//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{calendar_name}",
        f"X-WR-TIMEZONE:{TIMEZONE}",
    ]

    for ev in events:
        # Parse local times
        try:
            dt_local_start = datetime.fromisoformat(f"{ev['date']}T{ev['start_time']}:00")
            dt_local_end = datetime.fromisoformat(f"{ev['date']}T{ev['end_time']}:00")
        except Exception:
            # Skip bad rows
            continue

        dtstart_str = dt_local_start.strftime("%Y%m%dT%H%M%S")
        dtend_str = dt_local_end.strftime("%Y%m%dT%H%M%S")

        uid = f"{uuid4()}@image2cal"
        title = ev.get("title", "Rehearsal").replace("\n", " ").strip() or "Rehearsal"
        location = ev.get("location", "").replace("\n", " ")
        description = ev.get("notes", "").replace("\n", "\\n")

        vevent = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID={TIMEZONE}:{dtstart_str}",
            f"DTEND;TZID={TIMEZONE}:{dtend_str}",
            f"SUMMARY:{title}",
        ]
        if location:
            vevent.append(f"LOCATION:{location}")
        if description:
            vevent.append(f"DESCRIPTION:{description}")
        vevent.append("END:VEVENT")

        # Fold lines to spec
        for v in vevent:
            lines.append(fold_ical_line(v))

    lines.append("END:VCALENDAR")
    ics_text = "\r\n".join(lines) + "\r\n"
    return ics_text.encode("utf-8")

@app.route("/download/<image_id>")
def download(image_id):
    events_json = session.get(f"events_{image_id}", {"events": []})
    ics_bytes = make_ics(events_json.get("events", []))
    return send_file(
        io.BytesIO(ics_bytes),
        mimetype="text/calendar",
        as_attachment=True,
        download_name=f"schedule_{image_id}.ics",
    )

if __name__ == "__main__":
    app.run(debug=True)
