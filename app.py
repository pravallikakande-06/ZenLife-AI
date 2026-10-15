"""ZenLife AI - home page. Run with: streamlit run app.py"""
import streamlit as st

from utils import database as db, ui

user = ui.setup("Home", "🌿", need_profile=False)
uid = ui.USER_ID

st.title("🌿 ZenLife AI")
st.subheader("Your personal AI health & wellness assistant")
st.write("Track meals, water, exercise, sleep and mood in one calm place, get gentle personalized "
         "suggestions, and see how your habits trend over time. Everything is stored locally in a SQLite file.")

if not user:
    st.info("Welcome! Start by creating your profile. It takes a minute.")
    st.page_link("pages/2_Profile.py", label="Create my profile", icon="👤")
else:
    st.success(f"Welcome back, {user['name']}!")
    ui.show_due()
    try:
        checks = [("Profile saved", True),
                  ("Logged a meal", not db.get_records("meals", uid).empty),
                  ("Logged water", not db.get_records("water", uid).empty),
                  ("Logged exercise", not db.get_records("exercise", uid).empty),
                  ("Logged sleep", not db.get_records("sleep", uid).empty),
                  ("Wrote a mood entry", not db.get_records("mood", uid).empty)]
        st.markdown("**Getting started**  \n" + "  \n".join(("✅ " if ok else "⬜ ") + label for label, ok in checks))
    except db.DatabaseError as e:
        st.error(f"Database problem: {e}")

    st.markdown("#### Jump to")
    links = [("pages/1_Dashboard.py", "Dashboard", "📊"), ("pages/3_Diet_Planner.py", "Diet Planner", "🥗"),
             ("pages/4_Calorie_Tracker.py", "Calorie Tracker", "🍎"), ("pages/5_Hydration.py", "Hydration", "💧"),
             ("pages/6_Exercise.py", "Exercise", "🏃"), ("pages/7_Sleep_Tracker.py", "Sleep Tracker", "😴"),
             ("pages/8_AI_Wellness_Chat.py", "AI Wellness Chat", "💬"), ("pages/9_Mood_Journal.py", "Mood Journal", "📓"),
             ("pages/10_Analytics.py", "Analytics", "📈"), ("pages/11_Settings.py", "Settings", "⚙️")]
    cols = st.columns(3)
    for i, (path, label, icon) in enumerate(links):
        with cols[i % 3]:
            st.page_link(path, label=label, icon=icon)

st.divider()
st.caption("ZenLife AI provides general wellness information only. It is not a medical device and does not diagnose, "
           "treat, or replace professional medical advice. BMI, calorie and nutrition values are estimates.")
