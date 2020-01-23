#!/usr/bin/env python
from flask import Flask, render_template, flash, request, redirect, url_for
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import datetime

app = Flask(__name__)

# Define functions
def geocode_location(location):
    pass

# Define routes
@app.route('/', methods=['GET'])
def index():
    now = datetime.datetime.now() + datetime.timedelta(hours=3)
    now = datetime.datetime(now.year, now.month, now.day, now.hour,
                            15*round((float(now.minute) + float(now.second) / 60) // 15))
    now = now.strftime("%m-%d-%Y %H:%M")
    return render_template('index.html', now=now)

@app.route('/results', methods=['POST'])
def results():
    if request.method == 'POST':
        input_location = request.form.get('location')
        time = request.form.get('time')
        location = geocode_location(input_location)
    return render_template('results.html', location=location, time=time)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)
