#!/usr/bin/env python
from flask import Flask, render_template, flash, request, redirect, url_for
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import datetime, re, requests
import shapefile
from shapely.geometry import Point, Polygon
from scoothome.model import tsModel, initialize_params, import_secrets
import pandas as pd
import configparser, argparse
import os
import psycopg2
from fbprophet import Prophet
from darksky.api import DarkSky
from darksky.types import languages, units, weather



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

def make_prediction(area, pg, ds_key, lat, lon):
    m = tsModel(pg, ds_key)
    m.run(area, lat, lon)
    plot_res = m.fig

# Define routes
@app.route('/', methods=['GET'])
def index():
    now = calc_nowish()
    return render_template('index.html', now=now)

@app.route('/results', methods=['POST'])
def results():
    if request.method == 'POST':
        input_location = request.form.get('destination')
        time = request.form.get('time')
        location = geocode_location(input_location)
        if location[0] is None:
            reload_after_error("Whoops, looks like we can't find that location on the map. Pleast try again.")
        area = loc_to_area(location)
        pred = make_prediction(area, pg, ds_key, location[0], location[1])
        if area is None:
            reload_after_error("Whoops, looks like that location isn't in Austin! Please try again.")

    return render_template('results.html', lat=lat, lon=lon, time=time)

if __name__ == "__main__":
    args = initialize_params()
    pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))
    app.run(host='0.0.0.0', debug=False)
