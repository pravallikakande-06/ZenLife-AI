import streamlit as st

from utils import calculations as calc, database as db, ui

user = ui.setup("Profile", "👤", need_profile=False)
uid = ui.USER_ID
st.title("👤 Profile")
st.caption("Used for BMI, calorie estimates and personalization. Stored only in your local SQLite database. "
           "ZenLife is designed for adults (18+).")
u = user or {}
levels = list(calc.ACTIVITY_LEVELS)

with st.form("profile_form"):
    name = st.text_input("Name", value=u.get("name", ""), max_chars=60)
    c1, c2, c3 = st.columns(3)
    age = c1.number_input("Age", 18, 100, int(u.get("age", 30)))
    height = c2.number_input("Height (cm)", 100.0, 250.0, float(u.get("height_cm", 170.0)), step=0.5)
    weight = c3.number_input("Weight (kg)", 30.0, 300.0, float(u.get("weight_kg", 70.0)), step=0.1)
    c4, c5 = st.columns(2)
    sex = c4.selectbox("Sex (only used for the calorie-needs estimate)", calc.SEX_OPTIONS,
                       index=calc.SEX_OPTIONS.index(u["sex"]) if u.get("sex") in calc.SEX_OPTIONS else 0)
    activity = c5.selectbox("Activity level", levels,
                            index=levels.index(u["activity_level"]) if u.get("activity_level") in levels else 0)
    diet = st.radio("Dietary preference", calc.DIET_PREFS, horizontal=True,
                    index=calc.DIET_PREFS.index(u["diet_pref"]) if u.get("diet_pref") in calc.DIET_PREFS else 0)
    saved_goals = [g for g in (u.get("goals") or "").split(", ") if g in calc.GOALS]
    goals = st.multiselect("Wellness goals", calc.GOALS, default=saved_goals)
    submitted = st.form_submit_button("Save profile")

if submitted:
    if not name.strip():
        st.error("Please enter your name.")
    else:
        try:
            db.save_user(uid, name.strip(), int(age), sex, float(height), float(weight), activity, diet, ", ".join(goals))
            st.success("Profile saved.")
            user = db.get_user(uid)
        except db.DatabaseError as e:
            st.error(f"Could not save profile: {e}")

if user:
    b = calc.bmi(user["weight_kg"], user["height_cm"])
    cat, msg = calc.bmi_interpretation(b)
    bm = calc.bmr(user["weight_kg"], user["height_cm"], user["age"], user["sex"])
    td = calc.tdee(bm, user["activity_level"])
    sug_cal = calc.suggested_calories(td, user["goals"] or "")
    sug_water = calc.suggested_water_ml(user["weight_kg"])
    st.divider()
    m = st.columns(3)
    m[0].metric("BMI", f"{b:.1f}")
    m[1].metric("Estimated daily energy use", f"{td:.0f} kcal")
    m[2].metric("Water rule of thumb", f"{sug_water} ml")
    st.markdown(f"**{cat}.** {msg}")
    st.caption("Energy use is a Mifflin-St Jeor estimate multiplied by an activity factor, so real needs can differ by several hundred kcal.")
    st.markdown(f"Suggested starting calorie goal for your selected goals: **{sug_cal} kcal/day** (never below 1,200). "
                "If you have a medical condition or want to lose weight substantially, ask a doctor or registered dietitian.")
    b1, b2 = st.columns(2)
    if b1.button(f"Use {sug_cal} kcal as my calorie goal"):
        db.set_goal(uid, "calories", sug_cal)
        st.success("Calorie goal updated.")
    if b2.button(f"Use {sug_water} ml as my water goal"):
        db.set_goal(uid, "water_ml", sug_water)
        st.success("Water goal updated.")
