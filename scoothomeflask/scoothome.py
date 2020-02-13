#!/usr/bin/env python
from flask import Flask, render_template, flash, request, redirect, url_for
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import datetime, re, requests
import shapefile
from shapely.geometry import Point, Polygon
import pandas as pd
import numpy as np
import configparser, argparse
import os
import psycopg2
import dateparser
from scoothomeflask import app

# Import secrets from ini file
def import_secrets(ini_path):
    """
    Imports secrets from ini file on disk. 

    Returns list of postgres dictionary, darksky api key string, 
    and mapbox public token string.
    """
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['postgres'], config['darksky']['key'], config['mapbox']['public_token'])


ini_path = os.path.expanduser('~/scoothome/setup.ini')
pg, ds_key, map_pub_token = import_secrets(ini_path)

class tsResults():
    """
    Class to query postgres database and return predictions
    """
    def __init__(self, pg, area, t):
        self.pg = pg
        self.area = area
        self.t = t
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['host']
        self.pg_db = pg['database']
        self.pg_port = pg['port']

    def fetch_scooters(self, var):
        q = f"""SELECT ds, yhat, yhat_lower, yhat_upper FROM predictions
                WHERE area = '{self.area}'
                AND ds >= '{self.t}'
                AND var = '{var}'"""
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            preds = pd.read_sql(q, conn)
            if preds.shape[0] > 0:
                preds = preds.groupby('ds').mean()
            return preds


def geocode_location(location):
    """
    Function to convert location string and return lat/lon coordinates. 

    Geocoding is done via request to nominatim api.

    Returns tuple of (lat, lon) if successful, else tuple of (None, None)
    """
    query = re.sub(r'\s+', '\+', location)
    request = f'https://nominatim.openstreetmap.org/search?q={query}&format=json'
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'}
    res = requests.get(request, headers=header)
    if res.status_code == 200:
        try:
            lat = float(res.json()[0]['lat'])
            lon = float(res.json()[0]['lon'])
            return (lat, lon)
        except IndexError:
            return (None, None)
    else:
        return (None, None)

def calc_nowish(pretty=False):
    """
    Function to calculate approximate time. Rounds current time to nearest quarter hour and returns time three hours in future. Assumes input form server set to UTC +0 and desired timezone US Central (UTC-6).

    Returns formatted string. If pretty=True, time is simplified.
    """
    now = datetime.datetime.now() - datetime.timedelta(hours=3)
    now = datetime.datetime(now.year, now.month, now.day, now.hour,
                            15*round((float(now.minute) + float(now.second) / 60) // 15))
    if pretty:
        now = now.strftime("%b %d, %I:%M%p")
    else:
        now = now.strftime("%m-%d-%Y %H:%M")
    return now

def loc_to_area(location):
    """
    Function takes tuple of (lat, lon) format and returns unique code for project areas. If no match is found returns None.
    """
    lat, lon = location
    p = Point(lat, lon)
    p_rev = Point(lon, lat)
    tract = None
    district = None
    # get census tract
    census_path = os.path.expanduser('~/scoothome/data/census_tracts/census_tracts')
    with shapefile.Reader(census_path) as shp:
        for i, rec in enumerate(shp.records()):
            if rec[1] == '453':
                poly = Polygon(shp.shape(i).points)
                if poly.contains(p_rev):
                    tract = str(shp.record(i)[3])
                    break            
    # get council district
    district_path = os.path.expanduser('~/scoothome/data/council_districts/council_districts')
    with shapefile.Reader(district_path) as shp:
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
    """Thin wrapper for render_template of index with an error message"""
    now = calc_nowish(pretty=True)
    return render_template('index.html', now=now, error=error)

def get_predictions(area, pg, t, transpo='scooter'):
    """Function to fetch scooter predictions. Returns a pd.DataFrame"""
    t = t - datetime.timedelta(minutes=30)
    res = tsResults(pg, area, t)
    if transpo == 'scooter':
        scooters = res.fetch_scooters('n')
    else:
        scooters = res.fetch_scooters('bike_n')
    if scooters.shape[0] > 0:
        if transpo == 'scooter':
            used_scooters = res.fetch_scooters('in_use')
        else:
            used_scooters = res.fetch_scooters('bike_in_use')
        used_scooters.columns = map(lambda x: re.sub(r'^', 'in_use_', x),
                                    used_scooters.columns)
        if used_scooters.shape[0] > 0:
            scooters = pd.merge(scooters, used_scooters, how='left', left_index=True, right_index=True)
        scooters.reset_index(inplace=True)
        scooters.sort_values('ds', inplace=True)
        return scooters
    else:
        return None

def format_time(t):
    """Thin wrapper for strftime. Returns 12 Hour:Minute formatted string."""
    return t.strftime("%I:%M")

def format_scoot_num(n):
    """Simple function to round vehicle numbers. Returns an integer >=0"""
    n = max([0, n])
    return int(np.round(n))

def format_scoot_pct(n, in_use):
    """Simple function to round percent of free vehicles. Returns 0 or float."""
    try:
        pct = (n - in_use) / n
    except ZeroDivisionError:
        pct = 0
    pct = np.round(pct * 100)
    return pct

def make_table_dict(t, n, used):
    """Simple helper function to format predictions for results html page. Returns a dictionary."""
    d = dict()
    d['time'] = format_time(t)
    d['N'] = format_scoot_num(n)
    d['used'] = min([d['N'], format_scoot_num(used)])
    d['pct_avail'] = format_scoot_pct(d['N'], d['used'])
    d['available'] = d['N'] - d['used']
    return d

def make_detailed_dict(t, n, n_low, n_high, used, used_low, used_high):
    """Simple helper function to format predictions for details html page. Returns a dictionary."""
    d = dict()
    d['time'] = format_time(t)
    d['n'] = format_scoot_num(n)
    d['used'] = min([d['n'], format_scoot_num(used)])
    d['free'] = d['n'] - d['used']
    d['n_low'] = format_scoot_num(n_low)
    d['used_low'] = min([d['n'], format_scoot_num(used_low)])
    d['free_low'] = d['n_low'] - d['used_low']
    d['n_high'] = format_scoot_num(n_high)
    d['used_high'] = min([d['n_high'], format_scoot_num(used_high)])
    d['free_high'] = d['n_high'] - d['used_high']
    d['best_case'] = max([0, d['n_high'] - d['used_low']])
    d['worst_case'] = max([0, d['n_low'] - d['used_high']])
    return d

# Define routes
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html')

@app.route('/', methods=['GET'])
def index():
    now = calc_nowish(pretty=True)
    return render_template('index.html', now=now)

@app.route('/details', methods=['POST', 'GET'])
def details():
    if request.method == 'POST':
        area = request.form.get('area')
        rounded_t = dateparser.parse(request.form.get('rounded_t'))
        vehicle_type = request.form.get('vehicle_type').lower()[:-1]
        model_pred = get_predictions(area, pg, rounded_t, vehicle_type)
        full_estimates = []
        for i in range(5):
            full_estimates.append(make_detailed_dict(model_pred['ds'][i],
                                                     model_pred['yhat'][i],
                                                     model_pred['yhat_lower'][i],
                                                     model_pred['yhat_upper'][i],
                                                     model_pred['in_use_yhat'][i],
                                                     model_pred['in_use_yhat_lower'][i],
                                                     model_pred['in_use_yhat_upper'][i]))
        vehicle_type = vehicle_type.title() + 's'
        return render_template('details.html',
                               location=request.form.get('location'),
                               time=request.form.get('time'),
                               estimates=full_estimates,
                               vehicle_type=vehicle_type,
                               test_val=request.form.get('rounded_t'))

@app.route('/results', methods=['POST'])
def results():
    if request.method == 'POST':
        input_location = request.form.get('destination')
        t = request.form.get('time')
        t = dateparser.parse(t)
        if t is None:
            return reload_after_error("Whoops, that's not a date we understand. Please try again.")
        # if t < datetime.datetime.now() - datetime.timedelta(hours=6):
        #     return reload_after_error("Whoops, looks like you chose a time that's already happened!")
        if t > datetime.datetime.now() + datetime.timedelta(days=7):
            return reload_after_error("Whoops, looks like you chose a time that's too far in the future.")
        location = geocode_location(input_location)
        if location[0] is None:
            return reload_after_error("Whoops, looks like we can't find that location on the map. Please try again.")
        area = loc_to_area(location)
        if area is None:
            return reload_after_error("Whoops, looks like that location isn't in Austin! Please try again.")
        rounded_t = datetime.datetime(t.year, t.month, t.day, t.hour,
                            15*round((float(t.minute) + float(t.second) / 60) // 15))
        if request.form.get('transpoType') == 'scooter':
            model_pred = get_predictions(area, pg, rounded_t)
        else:
            model_pred = get_predictions(area, pg, rounded_t, transpo='bike')
        if model_pred is None:
            if request.form.get('transpoType') == 'scooter':
                return reload_after_error("Hmm, looks like we don't have much data on that address. That probably means there won't be any scooters in the area. Please try another location.")
            else:
                return reload_after_error("Hmm, looks like we don't have much data on that address. That probably means there won't be any bikes in the area. Please try another location.")
        total_estimates = []
        for i in range(5):
            total_estimates.append(make_table_dict(model_pred.iloc[i, 0],
                                                   model_pred.iloc[i, 1],
                                                   model_pred['in_use_yhat'][i]))

        lat = np.round(location[0], decimals=14)
        lon = np.round(location[1], decimals=14)
        bbox_1 = lon - 0.0036
        bbox_2 = lat - 0.0036
        bbox_3 = lon + 0.0036
        bbox_4 = lat + 0.0036
        map_url = f"https://www.openstreetmap.org/export/embed.html?bbox={bbox_1}%2C{bbox_2}%2C{bbox_3}%2C{bbox_4}&amp;layer=mapnik&amp;marker={lat}%2C{lon}"
        vehicle_type = request.form.get('transpoType').title() + 's'

    return render_template('results.html',
                           location=input_location.title(),
                           time=t.strftime("%I:%M%p on %A, %B %d"),
                           estimates=total_estimates,
                           lat=lat,
                           lon=lon, 
                           map_url=map_url,
                           accessToken=map_pub_token,
                           raw_time=rounded_t,
                           area=area,
                           vehicle_type=vehicle_type)
