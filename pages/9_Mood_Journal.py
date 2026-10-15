import random
from datetime import date, datetime

import plotly.graph_objects as go
import streamlit as st

from utils import calculations as calc, database as db, recommendations as rec, ui

user = ui.setup("Mood Journal", "📓")
uid = ui.USER_ID
st.title("📓 Mood & Wellness Journal")
st.caption("Entries are stored only in your local SQLite database and are never sent to the AI service.")
tab_new, tab_trend, tab_relax = st.tabs(["New entry", "Trends & history", "Relaxation"])

with tab_new:
    if "prompt" not in st.session_state:
        st.session_state.prompt = random.choice(rec.JOURNAL_PROMPTS)
    st.markdown(f"💡 *Prompt:* {st.session_state.prompt}")
    if st.button("Another prompt"):
        st.session_state.prompt = random.choice(rec.JOURNAL_PROMPTS)
        st.rerun()
    d = st.date_input("Date", value=date.today(), max_value=date.today())
    mood = st.select_slider("Mood", options=list(calc.MOODS), value=3, format_func=lambda k: calc.MOODS[k])
    stress = st.slider("Stress level (1 = calm, 10 = very stressed)", 1, 10, 4)
    notes = st.text_area("Notes (optional)", max_chars=2000, height=140)
    if st.button("Save entry"):
        try:
            db.add_record("mood", uid, log_date=d.isoformat(), mood=int(mood), stress=int(stress),
                          notes=notes.strip() or None, created_at=datetime.now().isoformat(timespec="seconds"))
            st.success("Entry saved.")
            if stress >= 8 or mood == 1:
                st.info("That sounds like a tough stretch. The Relaxation tab may help. If this feels heavy or lasts, please reach out to someone you trust or a mental-health professional.")
        except db.DatabaseError as e:
            st.error(f"Could not save: {e}")

with tab_trend:
    days = st.select_slider("Period (days)", [14, 30, 60, 90], value=30)
    daily = db.daily_summary(uid, days)
    if daily["mood"].dropna().empty:
        st.info("No entries in this period.")
    else:
        fig = go.Figure()
        fig.add_scatter(x=daily.index, y=daily["mood"], mode="lines+markers", name="Mood (1-5)", line=dict(color=ui.PALETTE[0]), connectgaps=False)
        fig.add_scatter(x=daily.index, y=daily["stress"], mode="lines+markers", name="Stress (1-10)", line=dict(color=ui.PALETTE[3]), connectgaps=False)
        fig.update_layout(title="Mood and stress over time")
        ui.show_chart(ui.style_fig(fig, 320), "mood_trend")
    entries = db.get_records("mood", uid, daily.index[0].date().isoformat())
    show_notes = st.checkbox("Show my journal notes on screen", value=False)
    if not entries.empty:
        view = entries[["log_date", "mood", "stress"] + (["notes"] if show_notes else [])].copy()
        view["mood"] = view["mood"].map(calc.MOODS)
        ui.table(view.rename(columns={"log_date": "Date", "mood": "Mood", "stress": "Stress", "notes": "Notes"}))
        ui.delete_widget("mood", entries, lambda r: f"{r.log_date}: {calc.MOODS.get(r.mood, r.mood)}, stress {r.stress}", "mood")

with tab_relax:
    for title, text in rec.RELAXATION.items():
        with st.expander(title):
            st.write(text)
    st.caption("These are general relaxation techniques, not treatment. If you feel persistently low or anxious, consider talking to a professional.")
