import streamlit as st
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# Auto-refresh page every second
components.html("""
<script>
  setTimeout(() => location.reload(), 1000);
</script>
""", height=0)

# Page config
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
        # default index for radio
        idx = 0 if st.session_state.settings['modes'][color][0]=='count' else 1
        mode = st.radio(
            "Modus", ['Anzahl pro Tag', 'Intervall (Minuten)'], index=idx, key=f"mode_{color}"
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
    submitted = st.form_submit_button('Plan anwenden')
    if submitted:
        st.session_state.settings = {
            'start_time': start_time.strftime('%H:%M'),
            'end_time': end_time.strftime('%H:%M'),
            'modes': modes
        }
        st.session_state.done.clear()
        st.session_state.notified.clear()
        st.experimental_rerun()

# Build plan per settings
def build_plan(settings):
    plan = []
    today = datetime.today()
    start_dt = datetime.combine(today, datetime.strptime(settings['start_time'], '%H:%M').time())
    end_dt   = datetime.combine(today, datetime.strptime(settings['end_time'], '%H:%M').time())
    for color, (mode, val) in settings['modes'].items():
        icon = {'Blau':'🟦','Grün':'🟢','Rot':'🔴'}[color]
        if mode=='count':
            if val>1:
                step=(end_dt-start_dt)/(val-1)
                times=[start_dt+i*step for i in range(val)]
            else:
                times=[start_dt]
        else:
            times=[]
            cur=start_dt
            while cur<=end_dt:
                times.append(cur)
                cur+=timedelta(minutes=val)
        for dt in times:
            plan.append((dt.strftime('%H:%M'), color, icon))
    plan.sort(key=lambda x:x[0])
    return plan

plan_times = build_plan(st.session_state.settings)

# Find next drop
now = datetime.now()
next_drop=None
for t_str, color, icon in plan_times:
    dt=datetime.strptime(t_str,'%H:%M').replace(year=now.year,month=now.month,day=now.day)
    rem=int((dt-now).total_seconds())
    if rem>=0 and f"{color}_{t_str}" not in st.session_state.done:
        next_drop=(t_str,color,icon,rem)
        break

col1,col2=st.columns([2,1])
with col1:
    if next_drop:
        t_str,color,icon,rem=next_drop
        st.subheader(f"{icon} {color} tropfen um {t_str}")
        h,rem2=divmod(rem,3600)
        m,s=divmod(rem2,60)
        st.markdown(f"## {h:02}:{m:02}:{s:02}")
    else:
        st.subheader("✅ Fertig für heute!")
        st.markdown("## --:--:--")
    st.write("### Heute Tropfen")
    for t_str,color,icon in plan_times:
        key=f"{color}_{t_str}"
        checked=st.checkbox(f"{icon} {t_str}",key=key)
        if checked:
            st.session_state.done.add(key)
    done=len(st.session_state.done)
    total=len(plan_times)
    st.write(f"Fortschritt: {done}/{total} Tropfen")
    stages=["🟫","🌱","🌿","🌳","🌼"]
    idx=min(done*len(stages)//max(total,1),len(stages)-1)
    st.markdown(f"# {stages[idx]}")
    if next_drop:
        t_str,color,icon,rem=next_drop
        key=f"{color}_{t_str}"
        if rem<=0 and key not in st.session_state.notified:
            st.session_state.notified.add(key)
            components.html(f"""
<script>
 new Notification('💧 Tropfzeit!',{{body:'{icon} {color} tropfen um {t_str}'}});
</script>
""",height=0)

with col2:
    if st.button('Reset für heute'):
        st.session_state.done.clear()
        st.session_state.notified.clear()
