import streamlit as st

from utils import ai_service, calculations as calc, database as db, recommendations as rec, ui

user = ui.setup("Diet Planner", "🥗")
uid = ui.USER_ID
goals = db.get_goals(uid)
st.title("🥗 Diet Planner")
st.caption("Sample day built from a template library and the food dataset (approximate values per 100 g). "
           "These are general suggestions, not a prescription or exact nutrition data.")

c1, c2, c3 = st.columns([2, 2, 1])
diet = c1.selectbox("Dietary preference", calc.DIET_PREFS, index=calc.DIET_PREFS.index(user["diet_pref"]))
target = c2.number_input("Daily calorie target (kcal)", 800, 6000, int(min(6000, max(800, goals["calories"]))), step=50)
c3.write("")
if c3.button("🔀 Shuffle"):
    st.session_state["plan_offset"] = st.session_state.get("plan_offset", 0) + 1
plan = rec.generate_meal_plan(diet, target, f"{ui.today_str()}-{st.session_state.get('plan_offset', 0)}")

tot = {k: sum(m[k] for m in plan) for k in ("calories", "protein", "carbs", "fat")}
mc = st.columns(4)
mc[0].metric("Plan calories", f"≈ {tot['calories']} kcal")
mc[1].metric("Protein", f"≈ {tot['protein']} g")
mc[2].metric("Carbs", f"≈ {tot['carbs']} g")
mc[3].metric("Fat", f"≈ {tot['fat']} g")

ICONS = {"Breakfast": "🌅", "Lunch": "☀️", "Dinner": "🌙", "Snack": "🍏"}
for i, meal in enumerate(plan):
    with st.container(border=True):
        st.markdown(f"#### {ICONS[meal['meal']]} {meal['meal']}: {meal['name']}")
        ui.table([{"Food": f, "Grams": g} for f, g in meal["items"]])
        st.caption(f"≈ {meal['calories']} kcal · protein {meal['protein']} g · carbs {meal['carbs']} g · fat {meal['fat']} g (estimates)")
        with st.expander("Alternatives"):
            for alt in meal["alternatives"]:
                foods = ", ".join(f"{f} {g} g" for f, g in alt["items"])
                st.markdown(f"**{alt['name']}** (≈ {alt['calories']} kcal): {foods}")
        if st.button("➕ Log this meal to today", key=f"log_{i}"):
            try:
                for f, g in meal["items"]:
                    n = rec.food_nutrition(f, g)
                    db.add_record("meals", uid, log_date=ui.today_str(), meal_type=meal["meal"], food=f, quantity_g=g,
                                  calories=n["calories"], protein=n["protein"], carbs=n["carbs"], fat=n["fat"],
                                  source="meal plan (estimate)")
                st.success("Logged. See it in the Calorie Tracker.")
            except db.DatabaseError as e:
                st.error(f"Could not log: {e}")

with st.expander("✨ AI tips for this plan"):
    if not ai_service.status()["configured"]:
        st.info("No AI provider configured. The plan above does not need one.")
    elif st.button("Get AI tips"):
        summary = "; ".join(f"{m['meal']}: {m['name']} (~{m['calories']} kcal)" for m in plan)
        ctx = f"Diet preference: {diet}. Goals: {user['goals']}. Age {user['age']}."
        with st.spinner("Thinking..."):
            text, err = ai_service.ask([{"role": "user", "content": f"Give 3 brief general tips to make this day of meals fit my goals: {summary}"}], ctx)
        st.markdown(text) if text else st.warning(err)
        if text:
            st.caption("AI-generated, general guidance. Not medical advice.")
st.caption(rec.DISCLAIMER)
