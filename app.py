def build_plan(settings):
    tz = ZoneInfo("Europe/Berlin")
    today = datetime.now(tz).date()
    start_dt = datetime.combine(today, datetime.strptime(settings['start_time'], '%H:%M').time(), tzinfo=tz)
    end_dt   = datetime.combine(today, datetime.strptime(settings['end_time'],   '%H:%M').time(), tzinfo=tz)

    raw = []
    for color, (mode, val) in settings['modes'].items():
        icon = {'Blau':'🟦','Grün':'🟢','Rot':'🔴'}[color]
        # GENERATE
        if mode == 'count':
            if val > 1:
                step = (end_dt - start_dt) / (val - 1)
                times = [start_dt + i * step for i in range(val)]
            else:
                times = [start_dt]
        else:
            times = []
            t = start_dt
            while t <= end_dt:
                times.append(t)
                t += timedelta(minutes=val)
        for t in times:
            raw.append((t, color, icon))

    # SORT
    raw.sort(key=lambda x: x[0])
    sched = []

    # SCHEDULE with 30min GAP, but clamp count-events into window
    for t, color, icon in raw:
        if not sched:
            sched.append((t, color, icon))
            continue

        prev_t, *_ = sched[-1]
        if (t - prev_t).total_seconds() >= 1800:
            # no conflict
            sched.append((t, color, icon))
        else:
            # conflict: shift forward
            new_t = prev_t + timedelta(minutes=30)
            # **clamp**: if this was from a count-event (we know by mode),
            # always include: if new_t after end, force to end_dt
            if color in (k for k,m in settings['modes'].items() if m[0]=='count'):
                if new_t > end_dt:
                    new_t = end_dt
            else:
                # for interval-events: only include if within
                if new_t > end_dt:
                    continue
            sched.append((new_t, color, icon))

    # FORMAT
    return [(t.strftime('%H:%M'), c, i) for t,c,i in sched]
