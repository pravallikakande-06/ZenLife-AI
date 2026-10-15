"""Quick backend self-test (uses a temporary database; your real data is untouched).
Run:  python selftest.py"""
import os
import tempfile

os.environ["ZENLIFE_DB"] = os.path.join(tempfile.mkdtemp(), "selftest.db")

from datetime import date, timedelta  # noqa: E402

from utils import calculations as calc, database as db, recommendations as rec  # noqa: E402

foods = rec.load_foods()
for t in rec.TEMPLATES:
    for food, _ in t[3]:
        assert food in foods.index, f"Template uses unknown food: {food}"
db.init_db()
db.save_user(1, "Test", 30, "Female", 165, 60, list(calc.ACTIVITY_LEVELS)[0], "Vegan", "Eat healthier")
today = date.today().isoformat()
db.add_record("water", 1, log_date=today, logged_at="09:00", amount_ml=500)
db.add_record("sleep", 1, log_date=today, bedtime="23:00", wake_time="06:30", hours=7.5, quality=4)
assert db.daily_summary(1, 7).iloc[-1]["water_ml"] == 500
assert db.get_records("water", 1, (date.today() - timedelta(days=1)).isoformat()).shape[0] == 1
assert len(rec.generate_meal_plan("Vegan", 2000, "seed")) == 4
assert rec.cluster_habits(db.daily_summary(1, 30))["status"] == "insufficient"
print("All backend checks passed.")
