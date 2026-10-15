"""In-app reminders (shown while the app is open) and optional email via SMTP.
There are no background or browser push notifications: nothing runs when the app is closed."""
import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from utils import config, database as db

DEFAULT_TIMES = {"hydration": "11:00", "exercise": "18:00", "meal": "12:30", "sleep": "22:00"}
LABELS = {"hydration": "💧 Hydration", "exercise": "🏃 Exercise", "meal": "🍽️ Meals", "sleep": "😴 Sleep"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_due(user_id, now=None):
    now = now or datetime.now()
    today, hhmm = now.date().isoformat(), now.strftime("%H:%M")
    goals, due = db.get_goals(user_id), []
    for cat, r in db.get_reminders(user_id).items():
        if not r["enabled"] or hhmm < r["remind_time"]:
            continue
        if cat == "hydration":
            total = db.get_records("water", user_id, today, today)["amount_ml"].sum()
            if total < goals["water_ml"]:
                due.append({"category": cat, "message": f"💧 Hydration reminder: {total:.0f} of {goals['water_ml']:.0f} ml so far today."})
        elif cat == "exercise":
            mins = db.get_records("exercise", user_id, today, today)["duration_min"].sum()
            if mins < goals["exercise_min"]:
                due.append({"category": cat, "message": f"🏃 Exercise reminder: {mins:.0f} of {goals['exercise_min']:.0f} active minutes today."})
        elif cat == "meal":
            if db.get_records("meals", user_id, today, today).empty:
                due.append({"category": cat, "message": "🍽️ Meal reminder: no meals logged yet today."})
        elif cat == "sleep":
            due.append({"category": cat, "message": f"😴 Wind-down reminder: your reminder time ({r['remind_time']}) has passed. Time to prepare for sleep."})
    return due


def smtp_configured():
    return all(config.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def send_email(to, subject, body):
    if not smtp_configured():
        return False, "SMTP is not configured (see .env.example)."
    if not EMAIL_RE.match(to or ""):
        return False, "Please enter a valid email address."
    host, user = config.get("SMTP_HOST"), config.get("SMTP_USER")
    try:
        port = int(config.get("SMTP_PORT", "587"))
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = config.get("SMTP_FROM") or user, to, subject
        msg.set_content(body)
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
                s.login(user, config.get("SMTP_PASSWORD"))
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls(context=ctx)
                s.login(user, config.get("SMTP_PASSWORD"))
                s.send_message(msg)
    except (OSError, smtplib.SMTPException, ValueError) as e:
        return False, f"Email failed: {e}"
    return True, "Email sent."
