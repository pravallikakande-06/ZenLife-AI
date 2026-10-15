import plotly.graph_objects as go
import streamlit as st

from utils import database as db, recommendations as rec, ui

user = ui.setup("Analytics", "📈")
uid = ui.USER_ID
goals = db.get_goals(uid)
st.title("📈 Analytics")
days = st.select_slider("Period (days)", [14, 30, 60, 90], value=30)
daily = db.daily_summary(uid, days)

st.markdown("### This week vs last week")
two = db.daily_summary(uid, 14)
prev, cur = two.iloc[:7], two.iloc[7:]
metrics = [("Calories/day", "calories", "kcal"), ("Water/day", "water_ml", "ml"), ("Exercise/day", "exercise_min", "min"),
           ("Sleep/night", "sleep_hours", "h"), ("Mood", "mood", "/5"), ("Stress", "stress", "/10")]
cols = st.columns(len(metrics))
for col, (label, key, unit) in zip(cols, metrics):
    a, b = cur[key].mean(), prev[key].mean()
    if a != a:  # NaN: nothing logged
        col.metric(label, "—")
    else:
        delta = None if b != b else f"{a - b:+.1f} {unit}"
        col.metric(label, f"{a:.1f} {unit}", delta, delta_color="off")

st.markdown("### Trends")
a1, a2 = st.columns(2)
with a1:
    ui.show_chart(ui.trend_chart(daily, "calories", "Calories (kcal)", goals["calories"]), "a_cal")
    ui.show_chart(ui.trend_chart(daily, "exercise_min", "Exercise (min)", goals["exercise_min"]), "a_ex")
    ui.show_chart(ui.trend_chart(daily, "mood", "Mood (1-5)", kind="line"), "a_mood")
with a2:
    ui.show_chart(ui.trend_chart(daily, "water_ml", "Water (ml)", goals["water_ml"]), "a_water")
    ui.show_chart(ui.trend_chart(daily, "sleep_hours", "Sleep (h)", goals["sleep_hours"], kind="line"), "a_sleep")
    ui.show_chart(ui.trend_chart(daily, "stress", "Stress (1-10)", kind="line"), "a_stress")

st.markdown("### How your habits relate")
st.caption("Correlations describe patterns in your own logs. They do not prove cause and effect.")
cols_c = ["calories", "water_ml", "exercise_min", "sleep_hours", "mood", "stress"]
corr = daily[cols_c].corr(min_periods=7)
if corr.isna().all().all():
    st.info("Log at least a week of varied data to see correlations.")
else:
    fig = go.Figure(go.Heatmap(z=corr.values, x=cols_c, y=cols_c, zmin=-1, zmax=1, colorscale="BrBG", text=corr.round(2).values, texttemplate="%{text}"))
    ui.show_chart(ui.style_fig(fig.update_layout(title="Correlation matrix"), 380), "a_corr")

st.markdown("### Habit clusters (machine learning)")
st.caption(f"K-means clustering (scikit-learn) groups your days by water, exercise, sleep, mood and stress. "
           f"It needs at least {rec.ML_MIN_DAYS} days that have sleep and mood entries; nothing is trained or shown before that.")
res = rec.cluster_habits(daily)
if res["status"] == "insufficient":
    st.info(f"Not enough data yet: {res['n']} usable day(s), need {res['needed']}.")
elif res["status"] == "error":
    st.warning(f"Clustering could not run: {res['message']}")
else:
    st.write(f"Found **{res['k']} clusters** across {res['n']} days. Silhouette score: **{res['silhouette']:.2f}** "
             "(closer to 1 means more distinct groups; low values mean your days don't separate clearly).")
    ui.table(res["profiles"].reset_index().rename(columns={"cluster": "Cluster"}))
    st.caption("The table shows each cluster's average values. Compare them to see which kinds of days go with better mood or sleep.")

st.markdown("### Export your data")
export = daily.reset_index()
st.download_button("⬇️ Download daily summary (CSV)", export.to_csv(index=False).encode("utf-8"), "zenlife_daily_summary.csv", "text/csv")
st.caption(rec.DISCLAIMER)
