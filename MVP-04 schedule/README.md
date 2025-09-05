# Orchestra Schedule-from-Image (Flask MVP)

This MVP lets you:
1) Upload a rehearsal schedule screenshot.
2) Brush over the dates/times you *want to keep*.
3) The app masks the image to only your brush strokes.
4) The masked image is parsed by an OpenAI Vision-capable model.
5) Review & edit extracted events.
6) Download a Google Calendar `.ics` file and import it into Google Calendar.

## Quick Start

```bash
cd flask_schedule_mvp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # then edit .env to add your OpenAI key
python app.py
# visit http://127.0.0.1:5000
```

## Notes

- Default model is `gpt-4o-mini`. If you have access to a newer model (e.g., `gpt-5-thinking`), set `OPENAI_MODEL` in `.env`.
- The `.ics` is timezone-aware via `TZID:America/New_York`. Edit the constant in `app.py` if needed.
- Files are saved under `uploads/` and `processed/` (git-ignored by default).
