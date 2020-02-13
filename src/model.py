#!/usr/bin/env python

import pandas as pd
import numpy as np
import configparser, argparse
import os, datetime
import psycopg2
from sqlalchemy import create_engine
from fbprophet import Prophet
from fbprophet.diagnostics import cross_validation, performance_metrics
from fbprophet.plot import plot_cross_validation_metric
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import multiprocessing

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['postgres'], config['darksky']['key'])

class tsModel(multiprocessing.Process):
    """
    Fundamental class definition for estimating a model. 

    Required initialization: 
    pg: dictionary of postgres values for username, password, host, database, and port
    ds_key: DarkSky API key

    Optional initialization:
    bin_window: The size of the time window to model. Specify any valid Pandas offset string. 
        All data will be resampled accordingly. Default is '15T', i.e. 15 minute windows.
    include_weather: Boolean to indicate if the model should use weather covariates for building and predicting.
        Defaults to True.
    """
    def __init__(self, pg, ds_key, bin_window='15T', include_weather=True):
        multiprocessing.Process.__init__(self)
        self.ds_key = ds_key
        self.include_weather = include_weather
        if include_weather:
            self.init_ds_obj()
        self.bin_window = bin_window
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['host']
        self.pg_db = pg['database']
        self.pg_port = pg['port']
        self.ds_key = ds_key
        self.engine = create_engine(f'postgresql://{self.pg_username}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}')
        
    def init_ds_obj(self):
        """Thin wrapper to initialize DarkSky object"""
        self.ds = DarkSky(self.ds_key)
        
    def get_area_series(self, idx, series='scooter', log_transform=False, window_start=None, window_end=None):
        """
        Function to query postgres for time series data.

        Parameters:
        idx: area identifier
        series: which series to query - options are 'scooter' or 'bicycle'
        log_transform: Boolean for whether the usage numbers should be logged. Defaults to False.
        window_start: Arbitrary date for starting the time series. Can pair with window_end 
            for any arbitrary, logical window.Default is None (i.e. use the full time series.)
        window_end: See window_start.
        """
        self.idx = idx
        self.series = series
        if self.series == 'scooter':
            q = f"SELECT n, in_use, area, district, tract, time FROM ts WHERE area = '{idx}'"
        else:
            q = f"SELECT bike_n, bike_in_use, area, district, tract, time FROM ts WHERE area = '{idx}'"
        if window_start is not None:
            q = q + f" AND time >= '{window_start}' AND time <= '{window_end}'"
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            self.area_series = pd.read_sql_query(q, conn)
        if self.bin_window != "15T":
            self.area_series = self.area_series.set_index('time').resample(self.bin_window).sum()
            self.area_series.reset_index(inplace=True)
        if log_transform:
            if series == 'scooter':
                self.area_series['n'] = np.log(self.area_series['n'] + 1)
                self.area_series['in'] = np.log(self.area_series['in_use'] + 1)
            else:
                self.area_series['bike_n'] = np.log(self.area_series['bike_n'] + 1)
                self.area_series['bike_in'] = np.log(self.area_series['bike_in_use'] + 1)

    def transform_area_series(self, select_var='n'):
        """Simple function to select only required variable from time series data."""
        if self.series == 'scooter':
            if select_var == 'n':
                self.area_series.drop(columns=['in_use'], inplace=True)
            elif select_var == 'in_use':
                self.area_series.drop(columns=['n'], inplace=True)
            elif select_var == 'diff':
                self.area_series['available'] = self.area_series.apply(lambda x: max([0, x['n'] - x['in_use']]),
                                                                       axis=1)
                self.area_series.drop(columns=['n', 'in_use'], inplace=True)
        else:
            if select_var == 'bike_n':
                self.area_series.drop(columns=['bike_in_use'], inplace=True)
            elif select_var == 'bike_in_use':
                self.area_series.drop(columns=['bike_n'], inplace=True)
            elif select_var == 'diff':
                self.area_series['available'] = self.area_series.apply(lambda x: max([0, x['bike_n'] - x['bike_in_use']]),
                                                                       axis=1)
                self.area_series.drop(columns=['bike_n', 'bike_in_use'], inplace=True)

    def get_weather_data(self):
        """Simple function to query weather data from postgres"""
        start_time = self.area_series['time'].min()
        end_time = self.area_series['time'].max()
        q = f"SELECT * FROM weather WHERE time >= '{start_time}' AND time <= '{end_time}'"
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            self.weather = pd.read_sql_query(q, conn)
        if self.bin_window == '15T':
            self.weather = self.weather.set_index('time').resample('15T').pad()
        elif self.bin_window == '1H':
            pass
        else:
            self.weather = self.weather.set_index('time').resample(self.bin_window).mean()

    def prep_model_data(self):
        """Simple function to prepare guarantee time series data is in correct format for prophet model"""
        if self.include_weather:
            self.dat = pd.merge(self.area_series, self.weather, how='right', on='time')
        else:
            self.dat = self.area_series
        self.dat.fillna(0, inplace=True)
        if self.bin_window != '15T':
            self.dat.drop(columns=['district', 'tract'], inplace=True)
        else:
            self.dat.drop(columns=['area', 'district', 'tract'], inplace=True)
        self.dat.rename(columns={'time': 'ds', 'n': 'y', 'in_use': 'y',
                                 'bike_n': 'y', 'bike_in_use': 'y', 'available': 'y'},
                        inplace=True)

    def make_special_events(self):
        """Simple function to prepare holiday dataframes for model"""
        sxsw = pd.DataFrame({
            'holiday': 'sxsw',
            'ds': pd.to_datetime(['2018-03-09', '2018-03-10', '2018-03-11',
                                  '2018-03-12', '2018-03-13', '2018-03-14',
                                  '2018-03-15', '2018-03-16', '2018-03-17',
                                  '2018-03-18', '2018-03-19', '2019-03-08',
                                  '2019-03-09', '2019-03-10', '2019-03-11',
                                  '2019-03-12', '2019-03-13', '2019-03-14',
                                  '2019-03-15', '2019-03-16', '2019-03-17',
                                  '2020-03-13', '2020-03-14', '2020-03-15',
                                  '2020-03-16', '2020-03-17', '2020-03-18',
                                  '2020-03-19', '2020-03-20', '2020-03-21',
                                  '2020-03-22'])})
        acl = pd.DataFrame({
            'holiday': 'sxsw',
            'ds': pd.to_datetime(['2018-10-05', '2018-10-06', '2018-10-07',
                                  '2018-10-12', '2018-10-13', '2018-10-14',
                                  '2019-10-04', '2019-10-05', '2019-10-06',
                                  '2019-10-11', '2019-10-12', '2019-10-13', 
                                  '2020-10-02', '2020-10-03', '2020-10-04',
                                  '2020-10-09', '2020-10-10', '2020-10-11'])})
        self.holidays = pd.concat((sxsw, acl))
        

    def build_model(self, scale=0.05, hourly=False, holidays_scale=10.0):
        """Simple function to build model. Allows for specification of model parameters."""
        self.make_special_events()
        self.model = Prophet(changepoint_prior_scale=scale,
                             holidays=self.holidays,
                             holidays_prior_scale=holidays_scale)
        if self.include_weather:
            for v in ['temp', 'wind', 'cloud_cover', 'humidity']:
                self.model.add_regressor(v)
        if hourly:
            self.model.add_seasonality(name='hourly', period=0.04167, fourier_order=1)

    def train_model(self):
        """Thin wrapper to train model"""
        self.model.fit(self.dat)

    def calculate_periods(self):
        """Determine number of prediction periods required to reach 4 week forecast"""
        max_d = self.area_series['ds'].max()
        two_weeks = datetime.datetime.now() + datetime.timedelta(weeks=4)
        t_diff = two_weeks - max_d
        return int(t_diff.total_seconds() / 3600 * 4)

    def build_prediction_df(self, lat = 30.267151, lon = -97.743057, periods=192):
        """
        Simple function to build the prediction dataframe.

        Lat and lon only required if using weather data. Defaults to center of Austin.
        """
        self.future = self.model.make_future_dataframe(periods=periods, freq='15T')
        if self.include_weather:
            self.get_weather_pred(lat, lon)
            self.future = pd.merge(self.future, self.weather, how='left', left_on='ds', right_on='time')
            self.future.update(self.future_weather)

    def get_weather_pred(self, lat, lon):
        """Fetch forecast from DarkSky"""
        w_pred = self.ds.get_forecast(lat, lon,
                                      extend=False,
                                      lang=languages.ENGLISH,
                                      units=units.AUTO,
                                      exclude=[weather.MINUTELY, weather.ALERTS],
                                      timezone='UTC')
        times = [x.time for x in w_pred.hourly.data]
        temps = [x.temperature for x in w_pred.hourly.data]
        precips = [x.precip_intensity for x in w_pred.hourly.data]
        rain_prob = [x.precip_probability for x in w_pred.hourly.data]
        humidities = [x.humidity for x in w_pred.hourly.data]
        wind = [x.wind_speed for x in w_pred.hourly.data]
        clouds = [x.cloud_cover for x in w_pred.hourly.data]
        uv = [x.uv_index for x in w_pred.hourly.data]
        self.future_weather = pd.DataFrame({'time': times,
                                            'temp': temps,
                                            'current_rain': precips,
                                            'rain_prob': rain_prob,
                                            'humidity': humidities,
                                            'wind': wind,
                                            'cloud_cover': clouds,
                                            'uv': uv})
        if self.bin_window == '15T':
            self.future_weather = self.future_weather.set_index('time').resample('15T').pad()
        elif self.bin_window == '1H':
            self.future_weather.set_index('time', inplace=True)
        else:
            self.future_weather = self.future_weather.set_index('time').resample(self.bin_window).mean()
        self.future_weather = self.future_weather.tz_convert(None)

    def predict(self):
        """Thin wrapper to produce predictions"""
        self.fcst = self.model.predict(self.future)

    def preds_to_sql(self, var):
        """Simple function to write predictions to postgres table"""
        fcst_out = self.fcst[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
        fcst_out.columns = map(lambda x: x.lower(), fcst_out.columns)
        fcst_out['area'] = self.idx
        fcst_out['var'] = var
        fcst_out['modified_date'] = pd.to_datetime(datetime.datetime.today().strftime("%Y-%m-%d"))
        time_cutoff = pd.to_datetime(datetime.datetime.today() - datetime.timedelta(days=1))
        fcst_out = fcst_out[fcst_out['ds'] >= time_cutoff]
        fcst_out.to_sql('predictions', self.engine, if_exists='append', index=False)

    def query_preds(self, time_stamp):
        """Simple function for querying previous predictions"""
        q = f"SELECT * FROM predictions WHERE area = '{self.idx}' AND ds >= '{time_stamp}'"
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            self.old_preds = pd.read_sql(q, conn)

    def plot_results(self):
        """
        Thin wrapper to plot results. 

        Usually it is preferable to use object model and fcst dataframe to plot separately.
        """
        self.fig = self.model.plot(self.fcst)

    def cv(self, initial, period, horizon, log=False):
        """
        Simple function to do walk forward validation. 

        Parameters:
        Initial: length of time to train original model
        Period: frequency with which to test beyond the original training period
        Horizon: Length of predictions
        Log: Was the model trained on logged data? Defaults to False.
        """
        self.df_cv = cross_validation(self.model, initial=initial, period=period, horizon=horizon)
        if log:
            self.df_cv = self.df_cv.apply(lambda x: np.exp(x) if x.name not in ['ds', 'cutoff'] else x)
        self.df_p = performance_metrics(self.df_cv)

    def save_results(self, save_path):
        """Thin wrapper to save forecast dataframe to pickle object"""
        self.fcst.to_pickle(save_path)

def main(pg, ds_key):
    m = tsModel(pg, ds_key)


def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the .ini file containing the app token",
        required=False,
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = initialize_params()
    pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))
    main(pg)
