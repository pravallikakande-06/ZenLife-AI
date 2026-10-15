from datetime import datetime

import streamlit as st

from utils import calculations as calc, database as db, ui

user = ui.setup("Hydration", "💧")
uid = ui.USER_ID
st.title("💧 Hydration Tracker")


def add_water(ml):
    now = datetime.now()
    try:
        db.add_record("water", uid, log_date=now.date().isoformat(), logged_at=now.strftime("%H:%M"), amount_ml=float(ml))
    except db.DatabaseError as e:
        st.error(f"Could not save: {e}")
        return
    st.toast(f"+{ml:.0f} ml logged")
    st.rerun()


q = st.columns(4)
for col, ml in zip(q, (150, 250, 500, 750)):
    if col.button(f"+{ml} ml", key=f"q{ml}"):
        add_water(ml)
c1, c2 = st.columns([3, 1])
custom = c1.number_input("Custom amount (ml)", 10, 3000, 300, step=10)
c2.write("")
if c2.button("Add"):
    add_water(custom)

goals = db.get_goals(uid)
today = ui.today_str()
log = db.get_records("water", uid, today, today)
total = log["amount_ml"].sum()
st.markdown("### Today")
st.metric("Water so far", f"{total:.0f} ml", f"goal {goals['water_ml']:.0f} ml", delta_color="off")
st.progress(calc.pct(total, goals["water_ml"]), text=f"{calc.pct(total, goals['water_ml']) * 100:.0f}% of today's goal")
if total >= goals["water_ml"]:
    st.success("Goal reached. Nice work! 🎉")
if not log.empty:
    ui.table(log[["logged_at", "amount_ml"]].rename(columns={"logged_at": "Time", "amount_ml": "ml"}))
    ui.delete_widget("water", log, lambda r: f"{r.logged_at}: {r.amount_ml:.0f} ml", "water")

st.markdown("### Last 7 days")
daily = db.daily_summary(uid, 7)
ui.show_chart(ui.trend_chart(daily, "water_ml", "Water (ml)", goals["water_ml"]), "h_week")
m = st.columns(2)
m[0].metric("Average per day", f"{daily['water_ml'].mean():.0f} ml")
m[1].metric("Days goal met", f"{int((daily['water_ml'] >= goals['water_ml']).sum())} / 7")

with st.expander("🎯 Hydration goal"):
    sug = calc.suggested_water_ml(user["weight_kg"])
    st.caption(f"A common rule of thumb is about 30-35 ml per kg of body weight (≈ {sug} ml for you). "
               "Needs vary with climate, activity and health conditions; follow your doctor's advice if you have any fluid restrictions.")
    new = st.number_input("Daily goal (ml)", 500, 8000, int(goals["water_ml"]), step=100)
    if st.button("Save goal"):
        try:
            db.set_goal(uid, "water_ml", new)
            st.success("Goal saved.")
            st.rerun()
        except db.DatabaseError as e:
            st.error(str(e))
with st.expander("🔔 Reminder (optional)"):
    ui.reminder_editor("hydration", "hyd")
    st.caption(ui.REMINDER_NOTE)
