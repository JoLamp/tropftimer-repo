import streamlit as st
from datetime import datetime, timedelta
import time
from typing import List, Tuple
import streamlit.components.v1 as components

# Setup page
st.set_page_config(page_title="Mausis Tropftimer", layout="wide")
st.title("💧 Mausi's Tropftimer")

# Initialize session state
if 'settings' not in st.session_state:
    st.session_state.settings = {
        'start_time': datetime.strptime('07:30', '%H:%M').time(),
        'end_time': datetime.strptime('22:30', '%H:%M').time(),
        'modes': { 'Blau': ('interval', 60), 'Grün': ('count', 4), 'Rot': ('count', 4) }
    }
if 'plan_times' not in st.session_state:
    st.session_state.plan_times: List[Tuple[str, str, str]] = []  # list of (time, color, icon)
if 'done' not in st.session_state:
    st.session_state.done = set()
if 'notified' not in st.session_state:
    st.session_state.notified = set()

# Sidebar: Settings
with st.sidebar.form('settings_form'):
    st.write("## Einstellungen")
    start = st.time_input("Startzeit", st.session_state.settings['start_time'])
    end = st.time_input("Endzeit", st.session_state.settings['end_time'])
    modes = {}
    for color, icon in [('Blau','🟦'), ('Grün','🟢'), ('Rot','🔴')]:
        st.write(f"### {icon} {color}")
        mode = st.radio("Modus", ['Anzahl pro Tag', 'Intervall (Minuten)'], key=color)
        if mode=='Anzahl pro Tag':
            val = st.number_input('Anzahl', min_value=1, value=st.session_state.settings['modes'][color][1], key=color+'_count')
            modes[color] = ('count', val)
        else:
            val = st.number_input('Intervall', min_value=1, value=st.session_state.settings['modes'][color][1], key=color+'_interval')
            modes[color] = ('interval', val)
    submitted = st.form_submit_button('Plan anwenden')
    if submitted:
        st.session_state.settings = {'start_time': start, 'end_time': end, 'modes': modes}
        # Rebuild plan times
        plan = []
        start_dt = datetime.combine(datetime.today(), start)
        end_dt = datetime.combine(datetime.today(), end)
        for color, (mode, value) in modes.items():
            icon = '🟦' if color=='Blau' else ('🟢' if color=='Grün' else '🔴')
            if mode=='count':
                interval = (end_dt - start_dt) / value
                for i in range(value):
                    t = (start_dt + i*interval).time().strftime('%H:%M')
                    plan.append((t, color, icon))
            else:
                cur = start_dt
                delta = timedelta(minutes=value)
                while cur <= end_dt:
                    plan.append((cur.time().strftime('%H:%M'), color, icon))
                    cur += delta
        plan.sort(key=lambda x: x[0])
        st.session_state.plan_times = plan
        st.session_state.done.clear()
        st.session_state.notified.clear()

# If no plan yet, trigger initial apply
if not st.session_state.plan_times:
    st.experimental_rerun()

# Request Notification permission once
components.html("""
<script>
if (Notification.permission !== 'granted') {
    Notification.requestPermission();
}
</script>
""", height=0)

# Main display with auto-update
placeholder = st.empty()
while True:
    with placeholder.container():
        now = datetime.now()
        next_drop = None
        for t, color, icon in st.session_state.plan_times:
            if t not in st.session_state.done:
                dt = datetime.strptime(t, '%H:%M').replace(year=now.year, month=now.month, day=now.day)
                diff = (dt - now).total_seconds()
                if diff >= 0:
                    next_drop = (t, color, icon, int(diff))
                    break
        cols = st.columns([2,1])
        with cols[0]:
            if next_drop:
                t, color, icon, rem = next_drop
                st.subheader(f"{icon} {color} tropfen um {t}")
                st.markdown(f"## {rem//3600:02}:{(rem%3600)//60:02}:{rem%60:02}")
            else:
                st.subheader("✅ Fertig für heute!")
                st.markdown("## --:--:--")
            st.write("### Heute Tropfen")
            for t, color, icon in st.session_state.plan_times:
                if st.checkbox(f"{icon} {t}", key=t):
                    st.session_state.done.add(t)
            # Progress and plant
            done = len(st.session_state.done)
            total = len(st.session_state.plan_times)
            st.write(f"Fortschritt: {done}/{total} Tropfen")
            stages = ["🟫","🌱","🌿","🌳","🌼"]
            idx = min(done * len(stages) // total, len(stages)-1)
            st.markdown(f"# {stages[idx]}")
            # Browser Notification on drop
            if next_drop:
                t, color, icon, rem = next_drop
                if rem == 0 and t not in st.session_state.notified:
                    st.session_state.notified.add(t)
                    # Trigger browser notification
                    components.html(f"""
<script>
new Notification('💧 Tropfzeit!', {{ body: '{icon} {color} tropfen um {t}' }});
</script>
""", height=0)
        with cols[1]:
            if st.button('Reset für heute'):
                st.session_state.done.clear()
    time.sleep(1)
    placeholder.empty()
