#!/usr/bin/env python
from flask import Flask, render_template, flash, request, redirect, url_for
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import datetime, re, requests

app = Flask(__name__)

# Define functions
def geocode_location(location):
    query = re.sub(r'\s+', '\+', location)
    request = f'https://nominatim.openstreetmap.org/search?q={query}&format=json'
    res = requests.get(request)
    if res.status_code == 200:
        lat = float(res.json()[0]['lat'])
        lon = float(res.json()[0]['lon'])
        return (lat, lon)
    else:
        return (None, None)

def calc_nowish():
    now = datetime.datetime.now() + datetime.timedelta(hours=3)
    now = datetime.datetime(now.year, now.month, now.day, now.hour,
                            15*round((float(now.minute) + float(now.second) / 60) // 15))
    now = now.strftime("%m-%d-%Y %H:%M")
    return now
# Define routes
@app.route('/', methods=['GET'])
def index():
    now = calc_nowish()
    return render_template('index.html', now=now)

@app.route('/results', methods=['POST'])
def results():
    if request.method == 'POST':
        input_location = request.form.get('location')
        time = request.form.get('time')
        location = geocode_location(input_location)
        if location[0] is None:
            error = "Whoops, looks like we can't find that location on the map. Pleast try again."
            now = calc_nowish()
            return render_template('index.html', now=now)
        else:
            lat, lon = location
    return render_template('results.html', lat=lat, lon=lon, time=time)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)
