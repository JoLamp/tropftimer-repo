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
def init_state():
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
init_state()

# Sidebar: settings form
with st.sidebar.form('settings_form'):
    st.write("## Einstellungen")
    start_time = st.time_input(
        "Startzeit", datetime.strptime(st.session_state.settings['start_time'], '%H:%M').time()
    )
    end_time = st.time_input(
        "Endzeit", datetime.strptime(st.session_state.settings['end_time'], '%H:%M').time()
    )
    modes = {}
    for color, icon in [('Blau', '🟦'), ('Grün', '🟢'), ('Rot', '🔴')]:
        st.write(f"### {icon} {color}")
        mode = st.radio(
            "Modus", ['Anzahl pro Tag', 'Intervall (Minuten)'], key=f"mode_{color}"
        )
        default = st.session_state.settings['modes'][color][1]
        if mode == 'Anzahl pro Tag':
            count = st.number_input(
                'Anzahl', min_value=1, value=default, key=f"count_{color}"
            )
            modes[color] = ('count', count)
        else:
            interval = st.number_input(
                'Intervall', min_value=1, value=default, key=f"interval_{color}"
            )
            modes[color] = ('interval', interval)
    if st.form_submit_button('Plan anwenden'):
        st.session_state.settings = {
            'start_time': start_time.strftime('%H:%M'),
            'end_time': end_time.strftime('%H:%M'),
            'modes': modes
        }
        st.session_state.done.clear()
        st.session_state.notified.clear()

# Build plan with 30-min gaps enforced
def build_plan(settings):
    entries = []
    today = datetime.today()
    start_dt = datetime.combine(today, datetime.strptime(settings['start_time'], '%H:%M').time())
    end_dt = datetime.combine(today, datetime.strptime(settings['end_time'], '%H:%M').time())
    for color, (mode, val) in settings['modes'].items():
        icon = {'Blau': '🟦', 'Grün': '🟢', 'Rot': '🔴'}[color]
        if mode == 'count':
            if val == 1:
                times = [start_dt]
            else:
                step = (end_dt - start_dt) / (val - 1)
                times = [start_dt + i * step for i in range(val)]
            for dt in times:
                entries.append(dt)
        else:
            dt = start_dt
            while dt <= end_dt:
                entries.append(dt)
                dt += timedelta(minutes=val)
    # Sort and enforce 30-minute gap
    entries = sorted(set(entries))
    filtered = []
    prev = None
    for dt in entries:
        if prev is None or (dt - prev).total_seconds() >= 1800:
            filtered.append(dt)
            prev = dt
    # Attach color and icon by matching settings
    plan = []
    for dt in filtered:
        t_str = dt.strftime('%H:%M')
        for color, (mode, val) in settings['modes'].items():
            icon = {'Blau': '🟦', 'Grün': '🟢', 'Rot': '🔴'}[color]
            # regenerate times for this color and check
            if mode == 'count':
                if val == 1:
                    times = [start_dt]
                else:
                    times = [start_dt + i * ((end_dt - start_dt) / (val - 1)) for i in range(val)]
            else:
                times = []
                dt_cursor = start_dt
                while dt_cursor <= end_dt:
                    times.append(dt_cursor)
                    dt_cursor += timedelta(minutes=val)
            if any(dt.strftime('%H:%M') == dt2.strftime('%H:%M') for dt2 in times):
                plan.append((t_str, color, icon))
                break
    return plan

plan_times = build_plan(st.session_state.settings)

# Determine next drop
def get_next(plan):
    now = datetime.now()
    for t, color, icon in plan:
        dt = datetime.strptime(t, '%H:%M').replace(
            year=now.year, month=now.month, day=now.day
        )
        if dt >= now:
            return t, color, icon, int((dt - now).total_seconds())
    return None, None, None, 0

t, color, icon, rem = get_next(plan_times)

# Two-column layout
col1, col2 = st.columns([2, 1])
with col1:
    if t:
        st.subheader(f"{icon} {color} tropfen um {t}")
        h, m_s = divmod(rem, 3600)
        m, s = divmod(m_s, 60)
        st.markdown(f"## {h:02}:{m:02}:{s:02}")
    else:
        st.subheader("✅ Fertig für heute!")
        st.markdown("## --:--:--")
    st.write("### Heute Tropfen")
    for t_str, color, icon in plan_times:
        key = f"{color}_{t_str}"
        if st.checkbox(f"{icon} {t_str}", key=key):
            st.session_state.done.add(key)
    done = len(st.session_state.done)
    total = len(plan_times)
    st.write(f"Fortschritt: {done}/{total} Tropfen")
    stages = ["🟫", "🌱", "🌿", "🌳", "🌼"]
    idx = min(done * len(stages) // total, len(stages) - 1)
    st.markdown(f"# {stages[idx]}")
    if t and rem <= 0 and f"{color}_{t}" not in st.session_state.notified:
        st.session_state.notified.add(f"{color}_{t}")
        components.html(f"""
<script>
  new Notification('💧 Tropfzeit!', {{ body: '{icon} {color} tropfen um {t}' }});
</script>
""", height=0)
with col2:
    if st.button('Reset für heute'):
        st.session_state.done.clear()
        st.session_state.notified.clear()
