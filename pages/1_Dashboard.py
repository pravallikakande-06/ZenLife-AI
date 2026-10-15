import streamlit as st

from utils import ai_service, calculations as calc, database as db, recommendations as rec, ui

user = ui.setup("Dashboard", "📊")
uid = ui.USER_ID
st.title(f"📊 {user['name']}'s Dashboard")
ui.show_due()

try:
    goals = db.get_goals(uid)
    daily = db.daily_summary(uid, 7)
    mood_df = db.get_records("mood", uid).head(5)
except db.DatabaseError as e:
    st.error(f"Could not load data: {e}")
    st.stop()

today = daily.iloc[-1]
sleep_logged = daily["sleep_hours"].dropna()
mood_logged = daily["mood"].dropna()

c = st.columns(5)
c[0].metric("Calories today", f"{today.calories:.0f} kcal", f"goal {goals['calories']:.0f}", delta_color="off")
c[0].progress(calc.pct(today.calories, goals["calories"]))
c[1].metric("Water today", f"{today.water_ml:.0f} ml", f"goal {goals['water_ml']:.0f}", delta_color="off")
c[1].progress(calc.pct(today.water_ml, goals["water_ml"]))
c[2].metric("Exercise today", f"{today.exercise_min:.0f} min", f"goal {goals['exercise_min']:.0f}", delta_color="off")
c[2].progress(calc.pct(today.exercise_min, goals["exercise_min"]))
if len(sleep_logged):
    c[3].metric("Last sleep", f"{sleep_logged.iloc[-1]:.1f} h", f"goal {goals['sleep_hours']:.1f}", delta_color="off")
    c[3].progress(calc.pct(sleep_logged.iloc[-1], goals["sleep_hours"]))
else:
    c[3].metric("Last sleep", "—", "no data yet", delta_color="off")
if len(mood_logged):
    c[4].metric("Latest mood (7d avg)", f"{mood_logged.mean():.1f} / 5")
else:
    c[4].metric("Latest mood", "—", "no data yet", delta_color="off")

st.markdown("### This week")
r1 = st.columns(2)
with r1[0]:
    ui.show_chart(ui.trend_chart(daily, "calories", "Calories (kcal)", goals["calories"]), "d_cal")
with r1[1]:
    ui.show_chart(ui.trend_chart(daily, "water_ml", "Water (ml)", goals["water_ml"]), "d_water")
r2 = st.columns(2)
with r2[0]:
    ui.show_chart(ui.trend_chart(daily, "exercise_min", "Exercise (min)", goals["exercise_min"]), "d_ex")
with r2[1]:
    ui.show_chart(ui.trend_chart(daily, "sleep_hours", "Sleep (hours)", goals["sleep_hours"], kind="line"), "d_sleep")

left, right = st.columns(2)
with left:
    st.markdown("### Recent mood entries")
    if mood_df.empty:
        st.caption("No mood entries yet. Add one in the Mood Journal.")
    else:
        view = mood_df[["log_date", "mood", "stress"]].copy()
        view["mood"] = view["mood"].map(calc.MOODS)
        view.columns = ["Date", "Mood", "Stress (1-10)"]
        ui.table(view)
        st.caption("Journal notes are hidden here for privacy; open the Mood Journal to read them.")
with right:
    st.markdown("### Weekly progress summary")
    for line in rec.progress_summary(daily, goals):
        st.markdown(f"- {line}")

st.markdown("### Suggestions")
for tip in rec.fallback_recommendations(daily, goals):
    st.markdown(f"- {tip}")

with st.expander("✨ Ask the AI for a personalized weekly note"):
    if not ai_service.status()["configured"]:
        st.info("No AI provider configured. Add a key to `.env` (see `.env.example`) to enable this. The rule-based suggestions above always work.")
    elif st.button("Generate AI note"):
        stats = "\n".join(rec.progress_summary(daily, goals))
        ctx = f"Age {user['age']}, activity: {user['activity_level']}, diet: {user['diet_pref']}, goals: {user['goals']}."
        with st.spinner("Thinking..."):
            text, err = ai_service.ask([{"role": "user", "content": f"Here is my last 7 days:\n{stats}\nGive 3 short, gentle, general suggestions."}], ctx)
        if text:
            st.markdown(text)
            st.caption("AI-generated, general guidance. Not medical advice.")
        else:
            st.warning(f"{err} The rule-based suggestions above still apply.")
