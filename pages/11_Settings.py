import streamlit as st

from utils import ai_service, calculations as calc, database as db, notifications, ui

user = ui.setup("Settings", "⚙️")
uid = ui.USER_ID
st.title("⚙️ Settings & Goals")
goals = db.get_goals(uid)
tab_goals, tab_rem, tab_ai, tab_data = st.tabs(["Goals", "Reminders & email", "AI status", "Data"])

with tab_goals:
    with st.form("goals_form"):
        c1, c2 = st.columns(2)
        cal = c1.number_input("Daily calories (kcal)", 800, 6000, int(goals["calories"]), step=50)
        prot = c2.number_input("Daily protein (g)", 10, 400, int(goals["protein"]))
        water = c1.number_input("Daily water (ml)", 500, 8000, int(goals["water_ml"]), step=100)
        exd = c2.number_input("Daily active minutes", 0, 600, int(goals["exercise_min"]))
        exw = c1.number_input("Weekly active minutes", 0, 3000, int(goals["exercise_week"]), step=10)
        slp = c2.number_input("Sleep (hours/night)", 4.0, 12.0, min(12.0, max(4.0, float(goals["sleep_hours"]))), step=0.25)
        if st.form_submit_button("Save goals"):
            try:
                for k, v in {"calories": cal, "protein": prot, "water_ml": water, "exercise_min": exd, "exercise_week": exw, "sleep_hours": slp}.items():
                    db.set_goal(uid, k, v)
                st.success("Goals saved.")
            except db.DatabaseError as e:
                st.error(f"Could not save: {e}")
    st.caption("Goals are personal targets, not medical recommendations. Consider checking calorie and activity targets with a professional.")

with tab_rem:
    st.info(ui.REMINDER_NOTE)
    for cat in notifications.DEFAULT_TIMES:
        ui.reminder_editor(cat, "set")
    st.caption("Sleep reminders stay 'due' from the reminder time until midnight. Others clear once you reach the goal or log a meal.")
    st.markdown("#### Optional email")
    email = st.text_input("Your email address", value=db.get_setting(uid, "notify_email", ""), max_chars=120)
    if not notifications.smtp_configured():
        st.warning("SMTP is not configured, so email is unavailable. Add the SMTP_* values to `.env` (see `.env.example`).")
    b1, b2, b3 = st.columns(3)
    if b1.button("Save email"):
        if email and not notifications.EMAIL_RE.match(email):
            st.error("That doesn't look like a valid email address.")
        else:
            db.set_setting(uid, "notify_email", email.strip())
            st.success("Saved.")
    if b2.button("Send test email"):
        ok, msg = notifications.send_email(email, "ZenLife AI test", "Your ZenLife AI email settings work.")
        (st.success if ok else st.error)(msg)
    if b3.button("Email due reminders now"):
        due = notifications.get_due(uid)
        if not due:
            st.info("Nothing is due right now.")
        else:
            ok, msg = notifications.send_email(email, "ZenLife AI reminders", "\n".join(d["message"] for d in due))
            (st.success if ok else st.error)(msg)

with tab_ai:
    s = ai_service.status()
    if s["configured"]:
        st.success(f"AI enabled: {s['provider']} · {s['model']}")
    else:
        st.info("AI is not configured. The app uses offline rule-based guidance instead. To enable AI, copy `.env.example` to `.env`, add a key, and restart.")
    st.caption("API keys are read from environment variables, `.env` or Streamlit secrets, never stored in the database or source code. "
               "Only general profile facts and your chat messages are sent to the provider; journal notes are never sent.")

with tab_data:
    st.markdown("#### Export")
    for table, label in [("meals", "Meals"), ("water", "Water"), ("exercise", "Exercise"), ("sleep", "Sleep"), ("mood", "Mood journal")]:
        df = db.get_records(table, uid)
        st.download_button(f"⬇️ {label} (CSV, {len(df)} rows)", df.to_csv(index=False).encode("utf-8"), f"zenlife_{table}.csv", "text/csv", key=f"dl_{table}")
    st.markdown("#### Delete everything")
    st.warning("This permanently deletes your profile and all records from the local database.")
    confirm = st.text_input("Type DELETE to confirm")
    if st.button("Delete all my data", type="primary"):
        if confirm == "DELETE":
            try:
                db.clear_all(uid)
                st.session_state.clear()
                st.success("All data deleted.")
                st.rerun()
            except db.DatabaseError as e:
                st.error(str(e))
        else:
            st.error("Type DELETE exactly to confirm.")
