from flask import Flask, render_template, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)

# Dynamischer Tropfen-Zeitplan wie im Desktop-Code
# Blau stündlich 08:00–22:00, Grün 07:30/10:30/14:30/18:30, Rot 08:30/12:30/16:30/20:30
plan = {}
for h in range(8, 23):
    plan[f"{h:02}:00"] = ("Blau", f"Blau tropfen", "#3498db")
for t in ["07:30", "10:30", "14:30", "18:30"]:
    plan[t] = ("Grün", f"Grün tropfen", "#2ecc71")
for t in ["08:30", "12:30", "16:30", "20:30"]:
    plan[t] = ("Rot", f"Rot tropfen", "#e74c3c")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fullplan')
def fullplan():
    # Liefert die geordnete Liste aller Zeiten
    return jsonify(fullplan=sorted(plan.keys()))

@app.route('/next')
def next_drop():
    now = datetime.now()
    next_time = None
    remaining = 0
    color = None
    for t in sorted(plan.keys()):
        clr, desc, hexcol = plan[t]
        ziel = datetime.strptime(t, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        if ziel >= now:
            next_time = t
            remaining = int((ziel - now).total_seconds())
            color = clr
            break
    return jsonify(time=next_time, remaining=remaining, color=color)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)