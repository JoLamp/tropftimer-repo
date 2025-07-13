import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import requests

# ============ OneSignal-Push Wrapper ============
ONESIGNAL_APP_ID   = "caff8cc9-9a98-4172-8e7b-ef8393a70a3b"    # ← hier eintragen
ONESIGNAL_REST_KEY = "os_v2_app_zl7yzsm2tbaxfdt356bzhjykhopokxb5elzuh2euqiezkzvg4p6nvsiik3iyzlc4kkv672bjwmstsji6435xt3u7he7icqjag4pm4bq"  # ← hier eintragen

def send_onesignal_push(message: str):
    """Sendet eine Push-Nachricht an alle angemeldeten Web-Push-Abonnenten."""
    url = "https://onesignal.com/api/v1/notifications"
    headers = {
        "Authorization": f"Basic {ONESIGNAL_REST_KEY}",
        "Content-Type":  "application/json; charset=utf-8"
    }
    payload = {
        "app_id":            ONESIGNAL_APP_ID,
        "included_segments": ["Subscribed Users"],
        "contents": {"en": message}
    }
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        st.error(f"OneSignal-Fehler: {resp.status_code} {resp.text}")

# ============ Auto-Refresh & Browser-Permission ============
st_autorefresh(interval=1000, key="ticker")
components.html("""
<script src="https://cdn.onesignal.com/sdks/OneSignalSDK.js" async=""></script>
<script>
  // OneSignal Web-Push initialisieren
  window.OneSignal = window.OneSignal || [];
  OneSignal.push(function() {
    OneSignal.init({ appId: "YOUR_ONESIGNAL_APP_ID" });
  });
  // Browser Notification Permission
  if (Notification.permission !== 'granted') {
    Notification.requestPermission();
  }
</script>
""".replace("YOUR_ONESIGNAL_APP_ID", ONESIGNAL_APP_ID), height=0)

# ============ Page Config ============
st.set_page_config(page_title="Mausis Tropftimer", layout="wide")
st.title("💧 Mausis Tropftimer")

# ============ State Init ============
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

# ============ Sidebar Settings ============
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
        idx = 0 if default_mode == 'count' else 1
        mode = st.radio(
            "Modus",
            ['Anzahl pro Tag','Intervall (Minuten)'],
            index=idx,
            key=f"mode_{color}"
        )
        if mode == 'Anzahl pro Tag':
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

# ============ Plan-Building ============
def build_plan(settings):
    tz = ZoneInfo("Europe/Berlin")
    today = datetime.now(tz).date()
    start_dt = datetime.combine(today, datetime.strptime(settings['start_time'], '%H:%M').time(), tzinfo=tz)
    end_dt   = datetime.combine(today, datetime.strptime(settings['end_time'],   '%H:%M').time(), tzinfo=tz)

    raw = []
    for color, (mode, val) in settings['modes'].items():
        icon = {'Blau':'🟦','Grün':'🟢','Rot':'🔴'}[color]
        if mode == 'count':
            step = (end_dt - start_dt) / (val - 1) if val > 1 else timedelta(0)
            times = [start_dt + i * step for i in range(val)]
        else:
            times = []
            t = start_dt
            while t <= end_dt:
                times.append(t)
                t += timedelta(minutes=val)
        for t in times:
            raw.append((t, color, icon))

    raw.sort(key=lambda x: x[0])
    sched = []
    for t, color, icon in raw:
        if not sched or (t - sched[-1][0]).total_seconds() >= 1800:
            sched.append((t, color, icon))
        else:
            new_t = sched[-1][0] + timedelta(minutes=30)
            if settings['modes'][color][0] == 'count':
                new_t = min(new_t, end_dt)
                sched.append((new_t, color, icon))
            elif new_t <= end_dt:
                sched.append((new_t, color, icon))

    return [(t.strftime('%H:%M'), c, i) for t, c, i in sched]

plan = build_plan(st.session_state.settings)

# ============ Next Drop ============
tz = ZoneInfo("Europe/Berlin")
now = datetime.now(tz)
next_item = None
for t_str, color, icon in plan:
    dt = datetime.strptime(t_str, '%H:%M').replace(year=now.year, month=now.month, day=now.day, tzinfo=tz)
    rem = int((dt - now).total_seconds())
    key = f"{color}_{t_str}"
    if rem >= 0 and key not in st.session_state.done:
        next_item = (t_str, color, icon, rem)
        break

# ============ UI Rendering ============
st.subheader("Nächste Tropfung")
if next_item:
    t_str, color, icon, rem = next_item
    st.write(f"{icon} **{color}** um **{t_str}**")
    h, r = divmod(rem, 3600); m, s = divmod(r, 60)
    st.markdown(f"## {h:02}:{m:02}:{s:02}")
else:
    st.markdown("## ✅ Fertig für heute!")

st.write("---")
st.write("### Heute Tropfen")
for t_str, color, icon in plan:
    key = f"{color}_{t_str}"
    if st.checkbox(f"{icon} {t_str}", key=key):
        st.session_state.done.add(key)

done  = len(st.session_state.done)
total = len(plan)
st.write(f"Fortschritt: **{done}/{total} Tropfen**")
stages = ["🟫","🌱","🌿","🌳","🌼"]
stage_icon = stages[min(done * len(stages) // max(total,1), len(stages)-1)]
st.markdown(f"# {stage_icon}")

# ============ Notifications ============
if next_item and next_item[3] <= 0:
    notif_key = f"{next_item[1]}_{next_item[0]}"
    if notif_key not in st.session_state.notified:
        st.session_state.notified.add(notif_key)

        # 1) Browser Notification
        components.html(f"""
<script>
  new Notification('💧 Tropfzeit!', {{ body: '{next_item[2]} {next_item[1]} tropfen um {next_item[0]}' }});
</script>
""", height=0)

        # 2) OneSignal Push
        send_onesignal_push(f"💧 Tropfzeit: {next_item[2]} {next_item[1]} um {next_item[0]}")

# ============ Reset ============
if st.button("Reset für heute"):
    st.session_state.done.clear()
    st.session_state.notified.clear()
