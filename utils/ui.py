"""Shared Streamlit helpers: page setup, light styling, charts and small widgets."""
import hmac
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from utils import calculations as calc, config, database as db, notifications

USER_ID = 1  # ZenLife AI is a single-profile, local-first app (see README, "Privacy").
PALETTE = ["#6B8F71", "#C9B79C", "#8FB996", "#A68A64", "#4F6F52", "#D9CBB0"]
CSS = """
<style>
[data-testid="stMetric"]{background:#FFFFFF;border:1px solid #DCE5DC;border-radius:12px;
  padding:12px 16px;box-shadow:0 1px 2px rgba(79,111,82,.08);}
h1,h2,h3{color:#3F5A43;}
.stButton>button,.stFormSubmitButton>button{border-radius:10px;}
@media (max-width:640px){[data-testid="stMetric"]{padding:8px 10px;}}
</style>
"""


@st.cache_resource
def _init_db():
    db.init_db()
    return True


def _passcode_gate():
    code = config.get("APP_PASSCODE")
    if not code or st.session_state.get("auth_ok"):
        return
    st.title("🔒 ZenLife AI")
    entered = st.text_input("Passcode", type="password")
    if entered:
        if hmac.compare_digest(entered.encode(), code.encode()):
            st.session_state["auth_ok"] = True
            st.rerun()
        st.error("Incorrect passcode.")
    st.stop()


def setup(title, icon="🌿", need_profile=True):
    """Call first on every page. Returns the user profile dict (or None)."""
    st.set_page_config(page_title=f"{title} · ZenLife AI", page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    _passcode_gate()
    try:
        _init_db()
        user = db.get_user(USER_ID)
    except db.DatabaseError as e:
        st.error(f"Database problem: {e}. See the README debugging section.")
        st.stop()
    with st.sidebar:
        st.markdown("### 🌿 ZenLife AI")
        if user:
            st.caption(f"Profile: **{user['name']}**")
            try:
                for d in notifications.get_due(USER_ID):
                    st.warning(d["message"], icon="🔔")
            except db.DatabaseError:
                pass
        st.caption("General wellness info only. Not medical advice.")
    if need_profile and not user:
        st.title(f"{icon} {title}")
        st.info("Create your profile first so ZenLife can personalize things.")
        st.page_link("pages/2_Profile.py", label="Go to Profile", icon="👤")
        st.stop()
    return user


def show_due():
    try:
        for d in notifications.get_due(USER_ID):
            st.warning(d["message"], icon="🔔")
    except db.DatabaseError:
        pass


def style_fig(fig, height=300):
    fig.update_layout(template="simple_white", height=height, margin=dict(l=10, r=10, t=45, b=10),
                      colorway=PALETTE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.2))
    return fig


def show_chart(fig, key=None):
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except Exception:  # older Streamlit versions don't accept width="stretch"
        st.plotly_chart(fig, use_container_width=True, key=key)


def table(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except Exception:  # older Streamlit versions
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def trend_chart(daily, col, title, goal=None, unit="", kind="bar", height=280):
    fig = go.Figure()
    if kind == "bar":
        fig.add_bar(x=daily.index, y=daily[col], marker_color=PALETTE[0], name=title)
    else:
        fig.add_scatter(x=daily.index, y=daily[col], mode="lines+markers", line=dict(color=PALETTE[0]),
                        connectgaps=False, name=title)
    if goal:
        fig.add_hline(y=goal, line_dash="dash", line_color=PALETTE[3],
                      annotation_text=f"Goal {goal:g}{unit}", annotation_position="top left")
    fig.update_layout(title=title, showlegend=False)
    fig.update_xaxes(tickformat="%b %d")
    return style_fig(fig, height)


def delete_widget(table_name, df, describe, key):
    if df.empty:
        return
    with st.expander("🗑️ Delete a record"):
        opts = {int(r.id): describe(r) for r in df.itertuples()}
        sel = st.selectbox("Choose a record", list(opts), format_func=lambda i: opts[i], key=f"{key}_sel")
        if st.button("Delete selected record", key=f"{key}_del"):
            try:
                db.delete_record(table_name, USER_ID, sel)
            except db.DatabaseError as e:
                st.error(f"Could not delete: {e}")
            else:
                st.toast("Record deleted.")
                st.rerun()


def reminder_editor(category, key_prefix):
    label = notifications.LABELS[category]
    cur = db.get_reminders(USER_ID).get(category, {"remind_time": notifications.DEFAULT_TIMES[category], "enabled": False})
    c1, c2, c3 = st.columns([2, 2, 1])
    on = c1.toggle(f"{label} reminder", value=cur["enabled"], key=f"{key_prefix}_{category}_on")
    t = c2.time_input("Remind me at", value=calc.parse_hhmm(cur["remind_time"]), key=f"{key_prefix}_{category}_t")
    c3.write("")
    if c3.button("Save", key=f"{key_prefix}_{category}_save"):
        try:
            db.set_reminder(USER_ID, category, t.strftime("%H:%M"), on)
            st.success(f"{label} reminder saved.")
        except db.DatabaseError as e:
            st.error(f"Could not save: {e}")


REMINDER_NOTE = ("Reminders appear in the sidebar and on the Dashboard **while the app is open** (they refresh when you "
                 "interact with or reload a page). ZenLife does not send browser or background notifications; optional "
                 "email reminders are sent only when you press the send button in Settings.")


def today_str():
    return datetime.now().date().isoformat()
