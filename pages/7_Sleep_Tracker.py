from datetime import date, time

import streamlit as st

from utils import calculations as calc, database as db, recommendations as rec, ui

user = ui.setup("Sleep Tracker", "😴")
uid = ui.USER_ID
goals = db.get_goals(uid)
st.title("😴 Sleep Tracker")
tab_log, tab_trend, tab_sched, tab_tips = st.tabs(["Log sleep", "Trends", "Target schedule", "Sleep hygiene"])

with tab_log:
    wake_date = st.date_input("Morning you woke up", value=date.today(), max_value=date.today())
    method = st.radio("Record by", ["Bedtime & wake-up time", "Total duration"], horizontal=True)
    bed = wake = None
    if method == "Bedtime & wake-up time":
        c1, c2 = st.columns(2)
        bed = c1.time_input("Bedtime", value=calc.parse_hhmm(db.get_setting(uid, "sleep_bedtime", "22:30")))
        wake = c2.time_input("Wake-up time", value=calc.parse_hhmm(db.get_setting(uid, "sleep_wake", "06:30")))
        hours = calc.duration_hours(bed, wake)
        st.info(f"Sleep duration: **{hours:.2f} h**")
    else:
        hours = st.number_input("Hours slept", 0.5, 16.0, 7.0, step=0.25)
    quality = st.slider("How rested do you feel? (1-5)", 1, 5, 3)
    if st.button("Save sleep"):
        if not 0.5 <= hours <= 16:
            st.error("Sleep duration must be between 0.5 and 16 hours.")
        else:
            try:
                db.add_record("sleep", uid, log_date=wake_date.isoformat(), bedtime=bed.strftime("%H:%M") if bed else None,
                              wake_time=wake.strftime("%H:%M") if wake else None, hours=float(hours), quality=int(quality))
                st.success("Saved (an existing entry for that date is replaced).")
                st.rerun()
            except db.DatabaseError as e:
                st.error(f"Could not save: {e}")

with tab_trend:
    days = st.select_slider("Period (days)", [7, 14, 30], value=14)
    daily = db.daily_summary(uid, days)
    logged = daily["sleep_hours"].dropna()
    if logged.empty:
        st.info("No sleep logged in this period.")
    else:
        m = st.columns(3)
        m[0].metric("Average", f"{logged.mean():.1f} h", f"goal {goals['sleep_hours']:.1f}", delta_color="off")
        m[1].metric("Nights at goal", f"{int((logged >= goals['sleep_hours']).sum())} / {len(logged)}")
        recs = db.get_records("sleep", uid, daily.index[0].date().isoformat())
        beds = [calc.parse_hhmm(b) for b in recs["bedtime"].dropna()]
        if len(beds) >= 3:
            shifted = [((b.hour * 60 + b.minute) - 720) % 1440 for b in beds]
            mean = sum(shifted) / len(shifted)
            sd = (sum((x - mean) ** 2 for x in shifted) / len(shifted)) ** 0.5
            m[2].metric("Bedtime variation", f"±{sd:.0f} min")
        ui.show_chart(ui.trend_chart(daily, "sleep_hours", "Sleep (hours)", goals["sleep_hours"], kind="line"), "s_trend")
        ui.table(recs[["log_date", "bedtime", "wake_time", "hours", "quality"]].rename(columns={
            "log_date": "Date", "bedtime": "Bedtime", "wake_time": "Wake", "hours": "Hours", "quality": "Rested (1-5)"}))
        ui.delete_widget("sleep", recs, lambda r: f"{r.log_date}: {r.hours:.1f} h", "sleep")

with tab_sched:
    st.caption("Your target schedule sets your sleep-hours goal and your sleep reminder.")
    c1, c2 = st.columns(2)
    tb = c1.time_input("Target bedtime", value=calc.parse_hhmm(db.get_setting(uid, "sleep_bedtime", "22:30")), key="tb")
    tw = c2.time_input("Target wake-up", value=calc.parse_hhmm(db.get_setting(uid, "sleep_wake", "06:30")), key="tw")
    target = calc.duration_hours(tb, tw)
    st.info(f"Target sleep: **{target:.1f} h**" + ("" if 6 <= target <= 10 else " (outside the usual 7-9 h adult range)"))
    if st.button("Save schedule"):
        if not 4 <= target <= 12:
            st.error("Target sleep must be between 4 and 12 hours. Adjust the times.")
            st.stop()
        try:
            db.set_setting(uid, "sleep_bedtime", tb.strftime("%H:%M"))
            db.set_setting(uid, "sleep_wake", tw.strftime("%H:%M"))
            db.set_goal(uid, "sleep_hours", target)
            st.success("Schedule saved.")
        except db.DatabaseError as e:
            st.error(str(e))
    ui.reminder_editor("sleep", "slp")
    st.caption(ui.REMINDER_NOTE)

with tab_tips:
    for t in rec.SLEEP_TIPS:
        st.markdown(f"- {t}")
    st.caption("Most adults do well with 7-9 hours. If you often struggle to sleep, snore loudly, or feel very sleepy in the day, talk to a healthcare professional.")
