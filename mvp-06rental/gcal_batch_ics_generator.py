#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import uuid
import os

OUTPUT_ICS = os.environ.get("OUTPUT_ICS", "reminders.ics")
TIMEZONE = os.environ.get("TZID", "America/New_York")

EVENTS = [
    {
        "title": "Check Rent Received",
        "start": "2025-11-01 09:00",
        "all_day": False,
        "duration_minutes": 20,
        "rrule": "FREQ=MONTHLY;BYMONTHDAY=1",
        "description": "Monthly rent check for all units. Verify bank deposits & receipts.",
        "alarms": [60, 1440]
    },
    {
        "title": "License Renewal – Professional",
        "start": "2026-05-15",
        "all_day": True,
        "rrule": "FREQ=YEARLY;BYMONTH=5;BYMONTHDAY=15",
        "description": "Renew professional license; prepare documents and payment 2 weeks prior.",
        "alarms": [7*24*60, 2*24*60]
    },
    {
        "title": "Insurance Policy Renewal",
        "start": "2026-10-01",
        "all_day": True,
        "rrule": "FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=1",
        "description": "Home/auto/umbrella insurance renewal. Compare quotes.",
        "alarms": [30*24*60, 7*24*60, 24*60]
    }
]

def ics_escape(text: str) -> str:
    if text is None:
        return ""
    return (text.replace("\\", "\\\\")
                .replace("\\n", "\n")
                .replace("\n", "\\n")
                .replace(",", "\\,")
                .replace(";", "\\;"))

def dt_to_ics_local(dt: datetime, tzid: str) -> str:
    return f";TZID={tzid}:{dt.strftime('%Y%m%dT%H%M%S')}"

def date_to_ics(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.strftime("%Y%m%d")

def make_uid() -> str:
    return f"{uuid.uuid4()}@localgen"

def fold_lines(s: str, limit: int = 73) -> str:
    out = []
    for line in s.splitlines():
        while len(line) > limit:
            out.append(line[:limit])
            line = " " + line[limit:]
        out.append(line)
    return "\r\n".join(out)

def build_vtimezone(tzid: str) -> str:
    return f"""BEGIN:VTIMEZONE
TZID:{tzid}
X-LIC-LOCATION:{tzid}
BEGIN:STANDARD
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
TZNAME:EST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
BEGIN:DAYLIGHT
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
TZNAME:EDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
END:VTIMEZONE"""

def event_to_ics(ev: dict, tzid: str) -> str:
    title = ics_escape(ev.get("title", "Untitled"))
    description = ics_escape(ev.get("description", ""))
    location = ics_escape(ev.get("location", ""))
    uid = ev.get("uid") or make_uid()
    rrule = ev.get("rrule")
    alarms = ev.get("alarms", []) or []
    all_day = bool(ev.get("all_day", False))

    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"SUMMARY:{title}"]

    if description:
        lines.append(f"DESCRIPTION:{description}")
    if location:
        lines.append(f"LOCATION:{location}")

    if all_day:
        start_date = ev["start"]
        dtstart = date_to_ics(start_date)
        next_day = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
        lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
        lines.append(f"DTEND;VALUE=DATE:{next_day}")
    else:
        start = datetime.strptime(ev["start"], "%Y-%m-%d %H:%M")
        duration = int(ev.get("duration_minutes", 30))
        end = start + timedelta(minutes=duration)
        lines.append(f"DTSTART{dt_to_ics_local(start, tzid)}")
        lines.append(f"DTEND{dt_to_ics_local(end, tzid)}")

    if rrule:
        lines.append(f"RRULE:{rrule}")

    for mins in alarms:
        try:
            mins = int(mins)
        except Exception:
            continue
        trigger = f"-PT{abs(mins)}M"
        lines.extend([
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"TRIGGER:{trigger}",
            f"DESCRIPTION:Reminder - {title}",
            "END:VALARM"
        ])

    lines.append("END:VEVENT")
    return fold_lines("\r\n".join(lines))

def build_calendar(events: list, tzid: str) -> str:
    header = [
        "BEGIN:VCALENDAR",
        "PRODID:-//LocalGen//Batch Reminders//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"X-WR-TIMEZONE:{tzid}",
    ]
    vtz = build_vtimezone(tzid)
    body = [event_to_ics(ev, tzid) for ev in events]
    footer = ["END:VCALENDAR"]
    ics = "\r\n".join(header + [vtz] + body + footer) + "\r\n"
    return ics

def save_ics(path: str, events: list, tzid: str):
    ics = build_calendar(events, tzid)
    with open(path, "w", encoding="utf-8") as f:
        f.write(ics)
    print(f"Wrote ICS → {path}")

if __name__ == "__main__":
    save_ics(OUTPUT_ICS, EVENTS, TIMEZONE)
    print("Done.")
