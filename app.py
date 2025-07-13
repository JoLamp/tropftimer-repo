import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import requests

# ── HEAD INJECTION ─────────────────────────────────────────────────────────────
components.html("""
<link rel="manifest" href="/manifest.json">
<script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
<script>
  window.OneSignalDeferred = window.OneSignalDeferred || [];
  OneSignalDeferred.push(async function(OneSignal) {
    await OneSignal.init({
      appId: "caff8cc9-9a98-4172-8e7b-ef8393a70a3b",
      serviceWorkerPath: "OneSignalSDKWorker.js",
      promptOptions: {
        slidedown: {
          enabled: true,
          actionMessage: "Erlaube Push, damit du Tropf-Erinnerungen erhältst.",
          acceptButtonText: "Erlauben",
          cancelButtonText: "Später"
        }
      }
    });
  });
</script>
""", height=0)

# ── OneSignal-Push Wrapper ─────────────────────────────────────────────────────
ONESIGNAL_APP_ID   = "caff8cc9-9a98-4172-8e7b-ef8393a70a3b"
ONESIGNAL_REST_KEY = "os_v2_app_zl7yzsm2tbaxfdt356bzhjykhopokxb5elzuh2euqiezkzvg4p6nvsiik3iyzlc4kkv672bjwmstsji6435xt3u7he7icqjag4pm4bq"

def send_onesignal_push(message: str):
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
        st.error(f"OneSignal-Fehler {resp.status_code}: {resp.text}")

# ── Auto-Refresh & Page Config ────────────────────────────────────────────────
st_autorefresh(interval=1000, key="ticker")
st.set_page_config(page_title="Mausis Tropftimer", layout="wide")
st.title("💧 Mausis Tropftimer")

# ── Session State Init ────────────────────────────────────────────────────────
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

# ── Sidebar: Einstellungen ────────────────────────────────────────────────────
with st.sidebar.form('settings_form'):
    st.write("## Einstellungen")
    start_time = st.time_input(
        "Startzeit",
        datetime.strptime(st.session_state.settings['start_time'], '%H:%M').time()
    )
    end_time = st.time_input(
        "Endzeit",
        datetime.strptime(st.session_state.settings['end_time'], '%H:%M').time()
    )
    new_modes = {}
    for color, icon in [('Blau','🟦'), ('Grün','🟢'), ('Rot','🔴')]:
        st.write(f"### {icon} {color}")
        mode, val = st.session_state.settings['modes'][color]
        idx = 0 if mode=='count' else 1
        choice = st.radio("Modus", ['Anzahl pro Tag','Intervall (Minuten)'], index=idx, key=f"mode_{color}")
        if choice=='Anzahl pro Tag':
            cnt = st.number_input('Anzahl', min_value=1, value=val, key=f"count_{color}")
            new_modes[color] = ('count', cnt)
        else:
            iv = st.number_input('Intervall (Minuten)', min_value=1, value=val, key=f"interval_{color}")
            new_modes[color] = ('interval', iv)
    if st.form_submit_button("Plan anwenden"):
        st.session_state.settings = {
            'start_time': start_time.strftime('%H:%M'),
            'end_time':   end_time.strftime('%H:%M'),
            'modes':      new_modes
        }
        st.session_state.done.clear()
        st.session_state.notified.clear()
        st.experimental_rerun()

# ── Plan-Building mit 30-Min-Gap ───────────────────────────────────────────────
def build_plan(settings):
    tz = ZoneInfo("Europe/Berlin")
    today = datetime.now(tz).date()
    s = datetime.combine(today, datetime.strptime(settings['start_time'],'%H:%M').time(), tz)
    e = datetime.combine(today, datetime.strptime(settings['end_time'],  '%H:%M').time(), tz)

    raw = []
    for color,(mode,val) in settings['modes'].items():
        icon = {'Blau':'🟦','Grün':'🟢','Rot':'🔴'}[color]
        if mode=='count':
            if val>1:
                step = (e-s)/(val-1)
                times = [s + i*step for i in range(val)]
            else:
                times = [s]
        else:
            times = []
            t=s
            while t<=e:
                times.append(t)
                t+=timedelta(minutes=val)
        for t in times:
            raw.append((t,color,icon))

    raw.sort(key=lambda x:x[0])
    sched=[]
    for t,c,ic in raw:
        if not sched or (t-sched[-1][0]).total_seconds()>=1800:
            sched.append((t,c,ic))
        else:
            nt = sched[-1][0]+timedelta(minutes=30)
            if settings['modes'][c][0]=='count':
                nt = min(nt,e)
                sched.append((nt,c,ic))
            elif nt<=e:
                sched.append((nt,c,ic))
    return [(t.strftime('%H:%M'),c,ic) for t,c,ic in sched]

plan = build_plan(st.session_state.settings)

# ── Next Drop ────────────────────────────────────────────────────────────────
tz = ZoneInfo("Europe/Berlin")
now= datetime.now(tz)
next_item=None
for t_str,c,ic in plan:
    dt = datetime.strptime(t_str,'%H:%M').replace(year=now.year,month=now.month,day=now.day,tzinfo=tz)
    rem = int((dt-now).total_seconds())
    key = f"{c}_{t_str}"
    if rem>=0 and key not in st.session_state.done:
        next_item=(t_str,c,ic,rem)
        break

# ── Anzeige ─────────────────────────────────────────────────────────────────
st.subheader("Nächste Tropfung")
if next_item:
    t_str,c,ic,rem = next_item
    st.write(f"{ic} **{c}** um **{t_str}**")
    h,r = divmod(rem,3600); m,s = divmod(r,60)
    st.markdown(f"## {h:02}:{m:02}:{s:02}")
else:
    st.markdown("## ✅ Fertig für heute!")

st.write("---")
st.write("### Heute Tropfen")
for t_str,c,ic in plan:
    key=f"{c}_{t_str}"
    if st.checkbox(f"{ic} {t_str}", key=key):
        st.session_state.done.add(key)

done = len(st.session_state.done)
total= len(plan)
st.write(f"Fortschritt: **{done}/{total} Tropfen**")
icons=["🟫","🌱","🌿","🌳","🌼"]
stage= icons[min(done*len(icons)//max(total,1),len(icons)-1)]
st.markdown(f"# {stage}")

# ── Notifications ─────────────────────────────────────────────────────────────
if next_item and next_item[3]<=0:
    notif_key=f"{next_item[1]}_{next_item[0]}"
    if notif_key not in st.session_state.notified:
        st.session_state.notified.add(notif_key)

        # Browser
        components.html(f"""
<script>
  new Notification('💧 Tropfzeit!', {{ body: '{next_item[2]} {next_item[1]} tropfen um {next_item[0]}' }});
</script>
""", height=0)

        # OneSignal
        send_onesignal_push(f"💧 Tropfzeit: {next_item[2]} {next_item[1]} um {next_item[0]}")

# ── Reset ───────────────────────────────────────────────────────────────────
if st.button("Reset für heute"):
    st.session_state.done.clear()
    st.session_state.notified.clear()
