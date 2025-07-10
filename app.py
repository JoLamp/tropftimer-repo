import streamlit as st
from datetime import datetime
import time

# Tropfen-Plan: Blau stündlich, Grün/Rot feste Zeiten
plan = []
for h in range(8, 23):
    plan.append((f"{h:02}:00", "Blau", "🟦"))
for t in ["07:30", "10:30", "14:30", "18:30"]:
    plan.append((t, "Grün", "🟢"))
for t in ["08:30", "12:30", "16:30", "20:30"]:
    plan.append((t, "Rot", "🔴"))
plan.sort()

def format_countdown(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"

st.set_page_config(page_title="Mausis Tropftimer", layout="wide")
st.title("💧 Mausi's Tropftimer")

# State für abgehakte Tropfzeiten
if "done" not in st.session_state:
    st.session_state.done = set()

placeholder = st.empty()
while True:
    with placeholder.container():
        now = datetime.now()
        next_drop = None
        for t, color, icon in plan:
            if t not in st.session_state.done:
                dt = datetime.strptime(t, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                if dt >= now:
                    next_drop = (t, color, icon, int((dt - now).total_seconds()))
                    break

        cols = st.columns([2, 1])
        with cols[0]:
            if next_drop:
                t, color, icon, rem = next_drop
                st.subheader(f"{icon} {color} tropfen um {t}")
                st.markdown(f"## {format_countdown(rem)}")
            else:
                st.subheader("✅ Fertig für heute!")
                st.markdown("## --:--:--")

            st.write("### Heute Tropfen")
            for t, color, icon in plan:
                if st.checkbox(f"{icon} {t}", key=t):
                    st.session_state.done.add(t)

            done = len(st.session_state.done)
            total = len(plan)
            st.write(f"Fortschritt: {done}/{total} Tropfen")
            stages = ["🟫", "🌱", "🌿", "🌳", "🌼"]
            idx = min(done * len(stages) // total, len(stages) - 1)
            st.markdown(f"# {stages[idx]}")

        with cols[1]:
            if st.button("Reset für heute"):
                st.session_state.done.clear()

    time.sleep(1)
    placeholder.empty()
