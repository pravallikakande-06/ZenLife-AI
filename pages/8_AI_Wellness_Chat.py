import streamlit as st

from utils import ai_service, database as db, recommendations as rec, ui

user = ui.setup("AI Wellness Chat", "💬")
uid = ui.USER_ID
st.title("💬 AI Wellness Chat")
st.warning("I'm an AI wellness assistant, **not a doctor**. I can't diagnose illnesses or replace professional medical care. "
           "For symptoms, emergencies, or a mental-health crisis, contact a qualified professional or local emergency services.", icon="⚠️")

status = ai_service.status()
if status["configured"]:
    st.caption(f"AI provider: {status['provider']} · model: {status['model']}")
else:
    st.caption("No AI provider configured, so replies use offline rule-based guidance. See `.env.example` to enable AI.")

if "chat" not in st.session_state:
    st.session_state.chat = []
if st.sidebar.button("🧹 Clear conversation"):
    st.session_state.chat = []
    st.rerun()

goals = db.get_goals(uid)
context = (f"Adult aged {user['age']}, activity: {user['activity_level']}, diet preference: {user['diet_pref']}, "
           f"wellness goals: {user['goals'] or 'not set'}. Daily targets: {goals['calories']:.0f} kcal, "
           f"{goals['water_ml']:.0f} ml water, {goals['sleep_hours']:.1f} h sleep.")

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("source"):
            st.caption(m["source"])

prompt = st.chat_input("Ask about nutrition, exercise, hydration, sleep or healthy habits…", max_chars=1000)
if prompt:
    st.session_state.chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat[-10:]]
            text, err = ai_service.ask(history, context)
            if text:
                source = f"AI-generated · {status['provider']}/{status['model']}"
            else:
                text = rec.fallback_chat_reply(prompt, user)
                source = "Offline rule-based guidance" + (f" · {err}" if status["configured"] and err else "")
            if rec.red_flag(prompt):
                text = rec.EMERGENCY_NOTE + text
        st.markdown(text)
        st.caption(source)
    st.session_state.chat.append({"role": "assistant", "content": text, "source": source})
