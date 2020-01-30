#!/usr/bin/env python
from flask import Flask, render_template, flash, request, redirect, url_for
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import datetime, re, requests
import shapefile
from shapely.geometry import Point, Polygon
from scoothome.model import initialize_params, import_secrets
from scoothome.fetch_predictions import tsResults
import pandas as pd
import numpy as np
import configparser, argparse
import os
import psycopg2
import dateparser


app = Flask(__name__)

# Define functions
def geocode_location(location):
    query = re.sub(r'\s+', '\+', location)
    request = f'https://nominatim.openstreetmap.org/search?q={query}&format=json'
    res = requests.get(request)
    if res.status_code == 200:
        try:
            lat = float(res.json()[0]['lat'])
            lon = float(res.json()[0]['lon'])
            return (lat, lon)
        except IndexError:
            return (None, None)
    else:
        return (None, None)

def calc_nowish():
    now = datetime.datetime.now() + datetime.timedelta(hours=3)
    now = datetime.datetime(now.year, now.month, now.day, now.hour,
                            15*round((float(now.minute) + float(now.second) / 60) // 15))
    now = now.strftime("%m-%d-%Y %H:%M")
    return now

def loc_to_area(location):
    lat, lon = location
    p = Point(lat, lon)
    p_rev = Point(lon, lat)
    tract = None
    district = None
    # get census tract
    with shapefile.Reader('/home/bapfeld/scoothome/data/census_tracts/census_tracts') as shp:
        for i, rec in enumerate(shp.records()):
            if rec[1] == '453':
                poly = Polygon(shp.shape(i).points)
                if poly.contains(p_rev):
                    tract = str(shp.record(i)[3])
                    break            
    # get council district
    with shapefile.Reader('/home/bapfeld/scoothome/data/council_districts/council_districts') as shp:
        for i, shape in enumerate(shp.shapes()):
            poly = Polygon(shape.points)
            if poly.contains(p_rev):
                district = str(shp.record(i)[0])
                break
    # construct the area variable
    if (tract is None) or (district is None):
        area = None
    else:
        area = district + '-' + tract
    return area

def reload_after_error(error):
    now = calc_nowish()
    return render_template('index.html', now=now, error=error)

def get_predictions(area, pg, t):
    t = t - datetime.timedelta(minutes=30)
    res = tsResults(pg, area, t)
    scooters = res.fetch_scooters('n')
    used_scooters = res.fetch_scooters('in_use')
    used_scooters.columns = map(lambda x: re.sub(r'^', 'in_use_', x),
                                used_scooters.columns)
    scooters = pd.merge(scooters, used_scooters, how='left', left_on='ds', right_on='in_use_ds')
    scooters.sort_values('ds', inplace=True)
    return scooters
    

def format_time(t):
    return t.strftime("%I:%M")

def format_scoot_num(n):
    n = max([0, n])
    return int(np.round(n))

# Define routes
@app.route('/', methods=['GET'])
def index():
    now = calc_nowish()
    return render_template('index.html', now=now)

@app.route('/results', methods=['POST'])
def results():
    if request.method == 'POST':
        input_location = request.form.get('destination')
        t = request.form.get('time')
        t = dateparser.parse(t)
        if t < datetime.datetime.now():
            return reload_after_error("Whoops, looks like you chose a time that's already happened!")
        if t > datetime.datetime.now() + datetime.timedelta(hours=48):
            return reload_after_error("Whoops, looks like you chose a time that's too far in the future.")
        location = geocode_location(input_location)
        if location[0] is None:
            return reload_after_error("Whoops, looks like we can't find that location on the map. Please try again.")
        area = loc_to_area(location)
        if area is None:
            return reload_after_error("Whoops, looks like that location isn't in Austin! Please try again.")
        rounded_t = datetime.datetime(t.year, t.month, t.day, round(float(t.hour)))
        model_pred = get_predictions(area, pg, rounded_t)
        total_estimates = []
        for i in range(6):
            total_estimates.append({'time': format_time(model_pred.iloc[i, 0]),
                                    'N': format_scoot_num(model_pred.iloc[i, 1]),
                                    'In Use': format_scoot_num(model_pred['in_use_yhat'][i])})

        lat = location[0]
        lon = location[1]
        bbox_1 = lon - 0.0036
        bbox_2 = lat - 0.0036
        bbox_3 = lon + 0.0036
        bbox_4 = lat + 0.0036
        map_url = f"https://www.openstreetmap.org/export/embed.html?bbox={bbox_1}%2C{bbox_2}%2C{bbox_3}%2C{bbox_4}&amp;layer=mapnik&amp;marker={lat}%2C{lon}"

    return render_template('results.html',
                           location=input_location,
                           time=t,
                           estimates=estimates,
                           map_url=map_url)

if __name__ == "__main__":
    args = initialize_params()
    pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))
    app.run(host='0.0.0.0', debug=False)
