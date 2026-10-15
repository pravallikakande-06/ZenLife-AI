from datetime import date, timedelta

import plotly.express as px
import streamlit as st

from utils import calculations as calc, database as db, recommendations as rec, ui

user = ui.setup("Exercise", "🏃")
uid = ui.USER_ID
goals = db.get_goals(uid)
st.title("🏃 Exercise & Activity Planner")
tab_plan, tab_log, tab_prog = st.tabs(["Weekly plan", "Log activity", "Progress"])

with tab_plan:
    st.caption("General suggestions for healthy adults. Check with a clinician before starting a new program if you have a health condition, injury, or concern. Stop if you feel pain, dizziness or unusual breathlessness.")
    c1, c2 = st.columns(2)
    level = c1.selectbox("Fitness level", ["Beginner", "Intermediate", "Advanced"])
    prefs = c2.multiselect("Activities you like (leave empty for all)", list(rec.EXERCISES), default=["Walking", "Yoga", "Strength"])
    plan = rec.weekly_exercise_plan(level, prefs)
    ui.table(plan)
    st.markdown(f"**Planned active minutes this week:** {sum(p['Minutes'] for p in plan)}")
    with st.expander("Rest-day suggestions"):
        for r in rec.REST_DAY_IDEAS:
            st.markdown(f"- {r}")
    st.markdown("**Warm-up & cool-down:** 3-5 minutes of easy movement before, and gentle stretching after.")

with tab_log:
    d = st.date_input("Date", value=date.today(), max_value=date.today(), key="ex_date")
    c1, c2 = st.columns(2)
    act = c1.selectbox("Activity", list(calc.ACTIVITY_MET))
    mins = c2.number_input("Duration (minutes)", 1, 600, 30)
    est = calc.calories_burned(act, user["weight_kg"], mins)
    st.info(f"Estimated calories burned: ≈ {est} kcal (MET-based estimate using your weight; real values vary).")
    manual = st.checkbox("Enter calories burned manually (e.g. from a fitness watch)")
    kcal = st.number_input("Calories burned (kcal)", 0, 5000, int(est)) if manual else est
    notes = st.text_input("Notes (optional)", max_chars=120)
    if st.button("Save activity"):
        try:
            db.add_record("exercise", uid, log_date=d.isoformat(), activity=act, duration_min=float(mins),
                          calories_burned=float(kcal), notes=notes.strip() or None)
            st.success("Activity saved.")
            st.rerun()
        except db.DatabaseError as e:
            st.error(f"Could not save: {e}")

with tab_prog:
    daily = db.daily_summary(uid, 7)
    wk = daily["exercise_min"].sum()
    m = st.columns(3)
    m[0].metric("Minutes (7 days)", f"{wk:.0f}", f"weekly goal {goals['exercise_week']:.0f}", delta_color="off")
    m[1].metric("Active days", f"{int((daily['exercise_min'] > 0).sum())} / 7")
    m[2].metric("Est. kcal burned", f"{daily['exercise_kcal'].sum():.0f}")
    st.progress(calc.pct(wk, goals["exercise_week"]), text="Progress toward weekly goal")
    ui.show_chart(ui.trend_chart(daily, "exercise_min", "Exercise minutes per day", goals["exercise_min"]), "ex_week")
    recent = db.get_records("exercise", uid, (date.today() - timedelta(days=29)).isoformat())
    if not recent.empty:
        by = recent.groupby("activity")["duration_min"].sum().reset_index()
        fig = px.bar(by, x="activity", y="duration_min", title="Minutes by activity (last 30 days)", color_discrete_sequence=ui.PALETTE)
        ui.show_chart(ui.style_fig(fig), "ex_by")
        ui.table(recent[["log_date", "activity", "duration_min", "calories_burned", "notes"]].rename(columns={
            "log_date": "Date", "activity": "Activity", "duration_min": "Min", "calories_burned": "kcal", "notes": "Notes"}))
        ui.delete_widget("exercise", recent, lambda r: f"{r.log_date}: {r.activity}, {r.duration_min:.0f} min", "ex")
    else:
        st.caption("No activity logged in the last 30 days.")
