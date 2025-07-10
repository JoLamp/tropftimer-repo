import streamlit as st
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# Auto-refresh the page every second via JS
components.html("""
<script>
  setTimeout(() => location.reload(), 1000);
</script>
""", height=0)

# Page configuration
st.set_page_config(page_title="Mausis Tropftimer", layout="wide")
st.title("💧 Mausi's Tropftimer")

# Initialize session state defaults
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

# Sidebar: configuration form
with st.sidebar.form('settings_form'):
    st.write("## Einstellungen")
    start_time = st.time_input(
        "Startzeit", datetime.strptime(st.session_state.settings['start_time'], '%H:%M').time()
    )
    end_time = st.time_input(
        "Endzeit", datetime.strptime(st.session_state.settings['end_time'], '%H:%M').time()
    )
    modes = {}
    for color, icon in [('Blau','🟦'), ('Grün','🟢'), ('Rot','🔴')]:
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
                'Intervall (Minuten)', min_value=1, value=default, key=f"interval_{color}"
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

# Build combined plan ensuring 30-min minimum gap
def build_plan(settings):
    # Generate all candidate events per color
    entries = []
    today = datetime.today()
    start_dt = datetime.combine(today, datetime.strptime(settings['start_time'], '%H:%M').time())
    end_dt   = datetime.combine(today, datetime.strptime(settings['end_time'], '%H:%M').time())
    for color, (mode, val) in settings['modes'].items():
        icon = {'Blau':'🟦','Grün':'🟢','Rot':'🔴'}[color]
        # produce list of datetimes
        if mode == 'count':
            if val > 1:
                step = (end_dt - start_dt) / (val - 1)
                dt_list = [start_dt + i * step for i in range(val)]
            else:
                dt_list = [start_dt]
        else:  # interval mode
            dt_list = []
            cur = start_dt
            while cur <= end_dt:
                dt_list.append(cur)
                cur += timedelta(minutes=val)
        for dt in dt_list:
            entries.append((dt, color, icon))
    # sort by time
    entries.sort(key=lambda x: x[0])
    # enforce 30-minute minimum gap
    filtered = []
    for dt, color, icon in entries:
        if not filtered or (dt - filtered[-1][0]).total_seconds() >= 1800:
            filtered.append((dt, color, icon))
    # convert to plan of (HH:MM, color, icon)
    plan = [(dt.strftime('%H:%M'), color, icon) for dt, color, icon in filtered]
    return plan

plan_times = build_plan(st.session_state.settings)

# Determine next drop based on current time
def get_next(plan):
    now = datetime.now()
    for t_str, color, icon in plan:
        dt = datetime.strptime(t_str, '%H:%M').replace(
            year=now.year, month=now.month, day=now.day
        )
        if dt >= now:
            return t_str, color, icon, int((dt - now).total_seconds())
    return None, None, None, 0

next_t, next_color, next_icon, rem = get_next(plan_times)

# Layout: two columns
col1, col2 = st.columns([2, 1])
with col1:
    # Display next drop
    if next_t:
        st.subheader(f"{next_icon} {next_color} tropfen um {next_t}")
        h, rem2 = divmod(rem, 3600)
        m, s = divmod(rem2, 60)
        st.markdown(f"## {h:02}:{m:02}:{s:02}")
    else:
        st.subheader("✅ Fertig für heute!")
        st.markdown("## --:--:--")
    # Checkbox list
    st.write("### Heute Tropfen")
    for t_str, color, icon in plan_times:
        key = f"{color}_{t_str}"
        if st.checkbox(f"{icon} {t_str}", key=key):
            st.session_state.done.add(key)
    # Progress and plant
    done = len(st.session_state.done)
    total = len(plan_times)
    st.write(f"Fortschritt: {done}/{total} Tropfen")
    stages = ["🟫","🌱","🌿","🌳","🌼"]
    idx = min(done * len(stages) // max(total,1), len(stages)-1)
    st.markdown(f"# {stages[idx]}")
    # Browser notification when time arrives
    if next_t and rem <= 0 and f"{next_color}_{next_t}" not in st.session_state.notified:
        st.session_state.notified.add(f"{next_color}_{next_t}")
        components.html(f"""
<script>
  new Notification('💧 Tropfzeit!', {{ body: '{next_icon} {next_color} tropfen um {next_t}' }});
</script>
""", height=0)

with col2:
    if st.button('Reset für heute'):
        st.session_state.done.clear()
        st.session_state.notified.clear()
