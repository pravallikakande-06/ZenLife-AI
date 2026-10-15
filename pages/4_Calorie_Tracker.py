from datetime import date

import plotly.graph_objects as go
import streamlit as st

from utils import calculations as calc, database as db, recommendations as rec, ui

user = ui.setup("Calorie Tracker", "🍎")
uid = ui.USER_ID
goals = db.get_goals(uid)
foods = rec.load_foods()
st.title("🍎 Calorie & Nutrition Tracker")
st.caption("Values from the sample food dataset are approximate estimates, not verified lab data. Manual entries are used as typed.")

tab_log, tab_hist = st.tabs(["Log food", "History & charts"])

with tab_log:
    d = st.date_input("Date", value=date.today(), max_value=date.today())
    meal_type = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])
    mode = st.radio("How do you want to add it?", ["From food dataset", "Manual entry"], horizontal=True)
    if mode == "From food dataset":
        food = st.selectbox("Food (type to search)", list(foods.index))
        grams = st.number_input("Quantity (grams)", 1.0, 5000.0, 100.0, step=5.0)
        n = rec.food_nutrition(food, grams)
        st.info(f"≈ {n['calories']:.0f} kcal · protein {n['protein']} g · carbs {n['carbs']} g · fat {n['fat']} g (estimate)")
        if st.button("Add to log", key="add_ds"):
            try:
                db.add_record("meals", uid, log_date=d.isoformat(), meal_type=meal_type, food=food, quantity_g=grams,
                              calories=n["calories"], protein=n["protein"], carbs=n["carbs"], fat=n["fat"], source="dataset estimate")
                st.success(f"Added {food}.")
                st.rerun()
            except db.DatabaseError as e:
                st.error(f"Could not save: {e}")
    else:
        name = st.text_input("Food / dish name", max_chars=80)
        grams = st.number_input("Quantity (grams, approx.)", 1.0, 5000.0, 100.0, step=5.0, key="man_g")
        kcal = st.number_input("Calories (kcal)", 0.0, 5000.0, 0.0, step=10.0)
        with_macros = st.toggle("I know the macros (optional)")
        p = cb = ft = None
        if with_macros:
            m1, m2, m3 = st.columns(3)
            p, cb, ft = m1.number_input("Protein (g)", 0.0, 500.0, 0.0), m2.number_input("Carbs (g)", 0.0, 800.0, 0.0), m3.number_input("Fat (g)", 0.0, 500.0, 0.0)
        if st.button("Add to log", key="add_man"):
            if not name.strip() or kcal <= 0:
                st.error("Please enter a name and a calorie value above 0.")
            else:
                try:
                    db.add_record("meals", uid, log_date=d.isoformat(), meal_type=meal_type, food=name.strip(), quantity_g=grams,
                                  calories=kcal, protein=p, carbs=cb, fat=ft, source="manual entry")
                    st.success(f"Added {name.strip()}.")
                    st.rerun()
                except db.DatabaseError as e:
                    st.error(f"Could not save: {e}")

    st.divider()
    st.subheader(f"Totals for {d.isoformat()}")
    day = db.get_records("meals", uid, d.isoformat(), d.isoformat())
    cal, prot = day["calories"].sum(), day["protein"].sum()
    m = st.columns(4)
    m[0].metric("Calories", f"{cal:.0f} kcal", f"goal {goals['calories']:.0f}", delta_color="off")
    m[1].metric("Protein", f"{prot:.0f} g", f"goal {goals['protein']:.0f}", delta_color="off")
    m[2].metric("Carbs", f"{day['carbs'].sum():.0f} g")
    m[3].metric("Fat", f"{day['fat'].sum():.0f} g")
    st.progress(calc.pct(cal, goals["calories"]), text=f"Calories: {calc.pct(cal, goals['calories']) * 100:.0f}% of goal")
    st.progress(calc.pct(prot, goals["protein"]), text=f"Protein: {calc.pct(prot, goals['protein']) * 100:.0f}% of goal")
    if day.empty:
        st.caption("Nothing logged for this date yet.")
    else:
        if day[["protein", "carbs", "fat"]].isna().any().any():
            st.caption("Some manual entries have no macro data, so macro totals may be under-counted.")
        ui.table(day[["meal_type", "food", "quantity_g", "calories", "protein", "carbs", "fat", "source"]].rename(columns={
            "meal_type": "Meal", "food": "Food", "quantity_g": "Grams", "calories": "kcal", "protein": "P (g)",
            "carbs": "C (g)", "fat": "F (g)", "source": "Source"}))
        macros = [day["protein"].sum(), day["carbs"].sum(), day["fat"].sum()]
        if sum(macros) > 0:
            fig = go.Figure(go.Pie(labels=["Protein", "Carbs", "Fat"], values=macros, hole=0.5, marker_colors=ui.PALETTE[:3]))
            ui.show_chart(ui.style_fig(fig.update_layout(title="Macro split (grams)"), 280), "cal_pie")
        ui.delete_widget("meals", day, lambda r: f"{r.meal_type}: {r.food} ({r.calories:.0f} kcal)", "meals")

with tab_hist:
    days = st.select_slider("Period (days)", [7, 14, 30, 60], value=14)
    daily = db.daily_summary(uid, days)
    if daily["calories"].sum() == 0:
        st.info("No meals logged in this period.")
    else:
        ui.show_chart(ui.trend_chart(daily, "calories", "Daily calories (kcal)", goals["calories"]), "cal_hist")
        fig = go.Figure()
        for col, name, color in (("protein", "Protein", ui.PALETTE[0]), ("carbs", "Carbs", ui.PALETTE[1]), ("fat", "Fat", ui.PALETTE[3])):
            fig.add_bar(x=daily.index, y=daily[col], name=name, marker_color=color)
        fig.update_layout(barmode="stack", title="Macros per day (g)")
        ui.show_chart(ui.style_fig(fig), "cal_macros")
st.caption(rec.DISCLAIMER)
