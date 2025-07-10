import streamlit as st
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# Auto-refresh the page every second
components.html("""
<script>
  setTimeout(() => location.reload(), 1000);
</script>
""", height=0)

# Page config
st.set_page_config(page_title="Mausis Tropftimer", layout="wide")
st.title("💧 Mausi's Tropftimer")

# Initialize session state
if 'settings' not in st.session_state:
    st.session_state.settings = {
        'start_time': '07:30',
        'end_time': '22:30',
        'modes': {'Blau': ('interval', 60), 'Grün': ('count', 4), 'Rot': ('count', 4)}
    }
if 'done' not in st.session_state:
    st.session_state.done = set()
if 'notified' not in st.session_state:
    st.session_state.notified = set()

# Sidebar: settings form
with st.sidebar.form('settings_form'):
    st.write("## Einstellungen")
    start = st.time_input("Startzeit", datetime.strptime(st.session_state.settings['start_time'], '%H:%M').time())
    end = st.time_input("Endzeit", datetime.strptime(st.session_state.settings['end_time'], '%H:%M').time())
    modes = {}
    for color, icon in [('Blau','🟦'), ('Grün','🟢'), ('Rot','🔴')]:
        st.write(f"### {icon} {color}")
        mode = st.radio("Modus", ['Anzahl pro Tag', 'Intervall (Minuten)'], key=f"mode_{color}")
        default = st.session_state.settings['modes'][color][1]
        if mode == 'Anzahl pro Tag':
            val = st.number_input('Anzahl', min_value=1, value=default, key=f"count_{color}")
            modes[color] = ('count', val)
        else:
            val = st.number_input('Intervall', min_value=1, value=default, key=f"interval_{color}")
            modes[color] = ('interval', val)
    if st.form_submit_button('Plan anwenden'):
        st.session_state.settings = {
            'start_time': start.strftime('%H:%M'),
            'end_time': end.strftime('%H:%M'),
            'modes': modes
        }
        st.session_state.done.clear()
        st.session_state.notified.clear()

# Build drop plan enforcing 30min gap across colors
def build_plan(settings):
    entries = []
    today = datetime.today()
    start_dt = datetime.combine(today, datetime.strptime(settings['start_time'], '%H:%M').time())
    end_dt   = datetime.combine(today, datetime.strptime(settings['end_time'], '%H:%M').time())
    # generate per-color times
    for color, (mode, val) in settings['modes'].items():
        icon = {'Blau':'🟦','Grün':'🟢','Rot':'🔴'}[color]
        if mode == 'count':
            interval = (end_dt - start_dt) / val
            for i in range(val):
                dt = start_dt + i * interval
                entries.append((dt, color, icon))
        else:
            dt = start_dt
            step = timedelta(minutes=val)
            while dt <= end_dt:
                entries.append((dt, color, icon))
                dt += step
    # merge and enforce 30-min minimum gap
    entries = sorted(entries, key=lambda x: x[0])
    filtered = []
    prev_dt = None
    for dt, color, icon in entries:
        if prev_dt is None or (dt - prev_dt).total_seconds() >= 30*60:
            filtered.append((dt.strftime('%H:%M'), color, icon))
            prev_dt = dt
    return filtered

# Build plan_times
plan_times = build_plan(st.session_state.settings)
now = datetime.now()
next_drop = None
# determine next drop
for t, color, icon in plan_times:
    key = f"{color}_{t}"
    if key not in st.session_state.done:
        dt = datetime.strptime(t, '%H:%M').replace(year=now.year, month=now.month, day=now.day)
        remaining = (dt - now).total_seconds()
        if remaining >= 0:
            next_drop = (t, color, icon, int(remaining))
            break

# Layout: two columns
col1, col2 = st.columns([2,1])

# Left: status & checkboxes
with col1:
    if next_drop:
        t, color, icon, rem = next_drop
        st.subheader(f"{icon} {color} tropfen um {t}")
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        st.markdown(f"## {h:02}:{m:02}:{s:02}")
    else:
        st.subheader("✅ Fertig für heute!")
        st.markdown("## --:--:--")
    st.write("### Heute Tropfen")
    for t, color, icon in plan_times:
        key = f"{color}_{t}"
        checked = st.checkbox(f"{icon} {t}", key=key)
        if checked:
            st.session_state.done.add(key)
    # progress & plant
    done = len(st.session_state.done)
    total = len(plan_times)
    st.write(f"Fortschritt: {done}/{total} Tropfen")
    stages = ["🟫","🌱","🌿","🌳","🌼"]
    idx = min(done * len(stages) // total, len(stages)-1)
    st.markdown(f"# {stages[idx]}")
    # notifications
    if next_drop:
        t, color, icon, rem = next_drop
        key = f"{color}_{t}"
        if rem <= 0 and key not in st.session_state.notified:
            st.session_state.notified.add(key)
            components.html(f"""
<script>
  new Notification('💧 Tropfzeit!', {{ body: '{icon} {color} tropfen um {t}' }});
</script>
""", height=0)

# Right: reset button
with col2:
    if st.button('Reset für heute'):
        st.session_state.done.clear()
        st.session_state.notified.clear()
