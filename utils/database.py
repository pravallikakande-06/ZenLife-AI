"""SQLite storage for ZenLife AI.

All SQL uses parameter placeholders. Table names are checked against a whitelist and
column names come from code, never from user input. Every record carries a user_id.
"""
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("ZENLIFE_DB") or ROOT / "data" / "zenlife.db")
LOG_TABLES = ("meals", "water", "exercise", "sleep", "mood")
DEFAULT_GOALS = {"calories": 2000, "protein": 60, "water_ml": 2500, "exercise_min": 30,
                 "exercise_week": 150, "sleep_hours": 8}


class DatabaseError(Exception):
    """Raised for any database problem, with a readable message."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL, sex TEXT,
  height_cm REAL NOT NULL, weight_kg REAL NOT NULL, activity_level TEXT NOT NULL,
  diet_pref TEXT NOT NULL, goals TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS meals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
  meal_type TEXT NOT NULL, food TEXT NOT NULL, quantity_g REAL NOT NULL, calories REAL NOT NULL,
  protein REAL, carbs REAL, fat REAL, source TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS water(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
  logged_at TEXT, amount_ml REAL NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS exercise(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
  activity TEXT NOT NULL, duration_min REAL NOT NULL, calories_burned REAL, notes TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS sleep(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
  bedtime TEXT, wake_time TEXT, hours REAL NOT NULL, quality INTEGER,
  UNIQUE(user_id, log_date),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS mood(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
  mood INTEGER NOT NULL, stress INTEGER NOT NULL, notes TEXT, created_at TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS goals(
  user_id INTEGER NOT NULL, category TEXT NOT NULL, target REAL NOT NULL,
  PRIMARY KEY(user_id, category),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS reminders(
  user_id INTEGER NOT NULL, category TEXT NOT NULL, remind_time TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, category),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS settings(
  user_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT,
  PRIMARY KEY(user_id, key),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
"""


@contextmanager
def _conn():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error as e:
        raise DatabaseError(f"Cannot open the database at {DB_PATH}: {e}") from e
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        log.exception("Database error")
        raise DatabaseError(str(e)) from e
    finally:
        conn.close()


def _exec(sql, params=()):
    with _conn() as c:
        return c.execute(sql, params).lastrowid


def _df(sql, params=()):
    with _conn() as c:
        return pd.read_sql_query(sql, c, params=params)


def _check_table(table):
    if table not in LOG_TABLES:
        raise ValueError(f"Unknown table: {table}")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript(SCHEMA)


# ---------- users ----------
def get_user(user_id=1):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def save_user(user_id, name, age, sex, height_cm, weight_kg, activity_level, diet_pref, goals):
    _exec("""INSERT INTO users(id,name,age,sex,height_cm,weight_kg,activity_level,diet_pref,goals,updated_at)
             VALUES(?,?,?,?,?,?,?,?,?,?)
             ON CONFLICT(id) DO UPDATE SET name=excluded.name, age=excluded.age, sex=excluded.sex,
               height_cm=excluded.height_cm, weight_kg=excluded.weight_kg,
               activity_level=excluded.activity_level, diet_pref=excluded.diet_pref,
               goals=excluded.goals, updated_at=excluded.updated_at""",
          (user_id, name, age, sex, height_cm, weight_kg, activity_level, diet_pref, goals,
           datetime.now().isoformat(timespec="seconds")))


# ---------- generic log records ----------
def add_record(table, user_id, **fields):
    _check_table(table)
    if not all(k.isidentifier() for k in fields):
        raise ValueError("Invalid column name")
    cols = ["user_id", *fields]
    sql = (f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) "
           f"VALUES ({','.join('?' * len(cols))})")
    return _exec(sql, (user_id, *fields.values()))


def get_records(table, user_id, start=None, end=None):
    _check_table(table)
    sql, params = f"SELECT * FROM {table} WHERE user_id=?", [user_id]
    if start:
        sql += " AND log_date>=?"
        params.append(start)
    if end:
        sql += " AND log_date<=?"
        params.append(end)
    return _df(sql + " ORDER BY log_date DESC, id DESC", tuple(params))


def delete_record(table, user_id, record_id):
    _check_table(table)
    _exec(f"DELETE FROM {table} WHERE id=? AND user_id=?", (record_id, user_id))


# ---------- goals / reminders / settings ----------
def get_goals(user_id=1):
    goals = dict(DEFAULT_GOALS)
    with _conn() as c:
        for r in c.execute("SELECT category,target FROM goals WHERE user_id=?", (user_id,)):
            goals[r["category"]] = r["target"]
    return goals


def set_goal(user_id, category, target):
    _exec("""INSERT INTO goals(user_id,category,target) VALUES(?,?,?)
             ON CONFLICT(user_id,category) DO UPDATE SET target=excluded.target""",
          (user_id, category, float(target)))


def get_reminders(user_id=1):
    with _conn() as c:
        rows = c.execute("SELECT category,remind_time,enabled FROM reminders WHERE user_id=?",
                         (user_id,)).fetchall()
    return {r["category"]: {"remind_time": r["remind_time"], "enabled": bool(r["enabled"])} for r in rows}


def set_reminder(user_id, category, remind_time, enabled):
    _exec("""INSERT INTO reminders(user_id,category,remind_time,enabled) VALUES(?,?,?,?)
             ON CONFLICT(user_id,category) DO UPDATE SET remind_time=excluded.remind_time,
               enabled=excluded.enabled""", (user_id, category, remind_time, int(enabled)))


def get_setting(user_id, key, default=None):
    with _conn() as c:
        row = c.execute("SELECT value FROM settings WHERE user_id=? AND key=?", (user_id, key)).fetchone()
    return row["value"] if row and row["value"] is not None else default


def set_setting(user_id, key, value):
    _exec("""INSERT INTO settings(user_id,key,value) VALUES(?,?,?)
             ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value""", (user_id, key, value))


def clear_all(user_id=1):
    """Delete the profile and every record (cascades to all tables)."""
    _exec("DELETE FROM users WHERE id=?", (user_id,))


# ---------- analytics ----------
def daily_summary(user_id=1, days=7):
    """One row per day for the last `days` days (today is the last row)."""
    end = date.today()
    start = end - timedelta(days=days - 1)
    s, e = start.isoformat(), end.isoformat()
    idx = pd.date_range(start, end, name="date")

    def agg(table, cols, how):
        df = get_records(table, user_id, s, e)
        if df.empty:
            return pd.DataFrame(index=idx, columns=cols, dtype=float)
        g = df.groupby("log_date")[cols].agg(how)
        g.index = pd.to_datetime(g.index)
        return g.reindex(idx).astype(float)

    meals = agg("meals", ["calories", "protein", "carbs", "fat"], "sum").fillna(0)
    water = agg("water", ["amount_ml"], "sum").fillna(0).rename(columns={"amount_ml": "water_ml"})
    ex = agg("exercise", ["duration_min", "calories_burned"], "sum").fillna(0).rename(
        columns={"duration_min": "exercise_min", "calories_burned": "exercise_kcal"})
    sl = agg("sleep", ["hours"], "mean").rename(columns={"hours": "sleep_hours"})
    mo = agg("mood", ["mood", "stress"], "mean")
    return pd.concat([meals, water, ex, sl, mo], axis=1)
