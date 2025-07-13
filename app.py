import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# 1) Autorefresh jede Sekunde
st_autorefresh(interval=1000, key="ticker")

# 2) Notification-Permission abfragen
components.html("""
<script>
  if (Notification.permission !== 'granted') {
    Notification.requestPermission();
  }
</script>
""", height=0)

# 3) Seite konfigurieren
st.set_page_config(page_title="Mausis Tropftimer", layout="wide")
st.title("💧 Mausi's Tropftimer")

# 4) State init
if 'settings' not in st.session_state:
    st.session_state.settings = {
        'start_time': '07:30',
        'end_time':   '22:30',
        'modes': {
            'Blau': ('interval', 60),
            'Grün': ('count', 4),
            'Rot':  ('count', 4),
        }
    }
if 'done' not in st.session_state:
    st.session_state.done = set()
if 'notified' not in st.session_state:
    st.session_state.notified = set()

# 5) Sidebar-Formular
with st.sidebar.form('settings_form'):
    st.write("## Einstellungen")
    st_time = st.time_input(
        "Startzeit",
        datetime.strptime(st.session_state.settings['start_time'], '%H:%M').time()
    )
    en_time = st.time_input(
        "Endzeit",
        datetime.strptime(st.session_state.settings['end_time'], '%H:%M').time()
    )
    new_modes = {}
    for color, icon in [('Blau','🟦'), ('Grün','🟢'), ('Rot','🔴')]:
        st.write(f"### {icon} {color}")
        default_mode, default_val = st.session_state.settings['modes'][color]
        idx = 0 if default_mode=='count' else 1
        mode = st.radio(
            "Modus",
            ['Anzahl pro Tag','Intervall (Minuten)'],
            index=idx,
            key=f"mode_{color}"
        )
        if mode=='Anzahl pro Tag':
            val = st.number_input(
                'Anzahl', min_value=1, value=default_val, key=f"count_{color}"
            )
            new_modes[color] = ('count', val)
        else:
            val = st.number_input(
                'Intervall (Minuten)', min_value=1, value=default_val, key=f"interval_{color}"
            )
            new_modes[color] = ('interval', val)
    if st.form_submit_button("Plan anwenden"):
        st.session_state.settings = {
            'start_time': st_time.strftime('%H:%M'),
            'end_time':   en_time.strftime('%H:%M'),
            'modes':      new_modes
        }
        st.session_state.done.clear()
        st.session_state.notified.clear()
        st.experimental_rerun()

# 6) Plan-Berechnung mit 30-Min-Abstand
def build_plan(settings):
    tz = ZoneInfo("Europe/Berlin")
    today    = datetime.now(tz).date()
    start_dt = datetime.combine(today, datetime.strptime(settings['start_time'],'%H:%M').time(), tz)
    end_dt   = datetime.combine(today, datetime.strptime(settings['end_time'],  '%H:%M').time(), tz)

    raw = []
    for color,(mode,val) in settings['modes'].items():
        icon = {'Blau':'🟦','Grün':'🟢','Rot':'🔴'}[color]
        if mode=='count':
            if val>1:
                step = (end_dt-start_dt)/(val-1)
                times = [start_dt + i*step for i in range(val)]
            else:
                times = [start_dt]
        else:
            times=[]
            t=start_dt
            while t<=end_dt:
                times.append(t)
                t += timedelta(minutes=val)
        for t in times:
            raw.append((t,color,icon))

    raw.sort(key=lambda x: x[0])
    sched=[]
    for t,color,icon in raw:
        if not sched or (t-sched[-1][0]).total_seconds()>=1800:
            sched.append((t,color,icon))
        else:
            t2 = sched[-1][0] + timedelta(minutes=30)
            if t2<=end_dt: sched.append((t2,color,icon))

    return [(t.strftime('%H:%M'),c,i) for t,c,i in sched]

plan = build_plan(st.session_state.settings)

# 🔧 DEBUG
st.write("DEBUG – now:", datetime.now(ZoneInfo("Europe/Berlin")).strftime("%H:%M:%S"))
st.write("DEBUG – plan:", plan)

# 7) Nächste Tropfung finden
now = datetime.now(ZoneInfo("Europe/Berlin"))
next_item=None
for t_str,color,icon in plan:
    dt  = datetime.strptime(t_str,'%H:%M').replace(
        year=now.year, month=now.month, day=now.day, tzinfo=ZoneInfo("Europe/Berlin")
    )
    rem = int((dt-now).total_seconds())
    key = f"{color}_{t_str}"
    if rem>=0 and key not in st.session_state.done:
        next_item=(t_str,color,icon,rem)
        break

# 8) Ausgabe
st.subheader("Nächste Tropfung")
if next_item:
    t_str,color,icon,rem = next_item
    st.write(f"{icon} **{color}** um **{t_str}**")
    h,r=divmod(rem,3600); m,s=divmod(r,60)
    st.markdown(f"## {h:02}:{m:02}:{s:02}")
else:
    st.markdown("## ✅ Fertig für heute!")

st.write("---")
st.write("### Heute Tropfen")
for t_str,color,icon in plan:
    key=f"{color}_{t_str}"
    if st.checkbox(f"{icon} {t_str}", key=key):
        st.session_state.done.add(key)

# Fortschritt & Pflanze
done=len(st.session_state.done)
total=len(plan)
st.write(f"Fortschritt: **{done}/{total} Tropfen**")
st.markdown(f"# {['🟫','🌱','🌿','🌳','🌼'][min(done*5//max(total,1),4)]")

# Notification
if next_item and next_item[3]<=0:
    notif=f"{next_item[2]} {next_item[1]} tropfen um {next_item[0]}"
    if notif not in st.session_state.notified:
        st.session_state.notified.add(notif)
        components.html(f"""<script>
  new Notification('💧 Tropfzeit!',{{body:'{notif}'}})
</script>""",height=0)

# Reset
if st.button("Reset für heute"):
    st.session_state.done.clear()
    st.session_state.notified.clear()
