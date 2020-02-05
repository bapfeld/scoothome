import pandas as pd
import numpy as np
from fbprophet import Prophet
from fbprophet.diagnostics import cross_validation, performance_metrics
from fbprophet.plot import plot_cross_validation_metric
import psycopg2
from matplotlib.backends.backend_pdf import PdfPages
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import sys, re, os
sys.path.append('/home/bapfeld/scoothome')
from src.model import tsModel, import_secrets
import configparser, argparse
from itertools import product
import matplotlib.pyplot as plt

class tsFetch():
    """Simple class to fetch appropriate time series data

    """
    def __init__(self, pg):
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['host']
        self.pg_db = pg['database']
        self.pg_port = pg['port']

    def get_area_series(self, idx, series='scooter', window_start=None, window_end=None):
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

pg, ds_key = import_secrets('/home/bapfeld/scoothome/setup.ini')
with open('/home/bapfeld/scoothome/data/area_id_list.txt', 'r') as f_in:
    area_list = [x.strip() for x in f_in.readlines()]

with PdfPages('/home/bapfeld/scoothome/figures/time_series_by_area.pdf') as pdf:
    for area in area_list:
        m = tsFetch(pg)
        m.get_area_series(area, 'scooter')
        m.area_series.dropna(inplace=True)
        m.area_series.sort_values('time').reset_index(inplace=True)
        plt.figure(figsize=(11, 5))
        plt.plot(m.area_series['n'], color="blue")
        plt.plot(m.area_series['in_use'], color='red')
        plt.title(area)
        pdf.savefig()
        plt.close()

# FB Prophet is throwing weird errors, so let's try to modify source plotting functions
from matplotlib.dates import (
        MonthLocator,
        num2date,
        AutoDateLocator,
        AutoDateFormatter,
    )
def fb_plot(
    m, fcst, ax=None, uncertainty=True, plot_cap=True, xlabel='ds', ylabel='y',
    figsize=(10, 6)
):
    """Plot the Prophet forecast.
    Parameters
    ----------
    m: Prophet model.
    fcst: pd.DataFrame output of m.predict.
    ax: Optional matplotlib axes on which to plot.
    uncertainty: Optional boolean to plot uncertainty intervals, which will
        only be done if m.uncertainty_samples > 0.
    plot_cap: Optional boolean indicating if the capacity should be shown
        in the figure, if available.
    xlabel: Optional label name on X-axis
    ylabel: Optional label name on Y-axis
    figsize: Optional tuple width, height in inches.
    Returns
    -------
    A matplotlib figure.
    """
    if ax is None:
        fig = plt.figure(facecolor='w', figsize=figsize)
        ax = fig.add_subplot(111)
    else:
        fig = ax.get_figure()
    fcst_t = fcst['ds'].dt.to_pydatetime()
    ax.plot(m.history['ds'].dt.to_pydatetime(), m.history['y'], 'k.')
    ax.plot(fcst_t, fcst['yhat'], ls='-', c='#0072B2')
    if 'cap' in fcst and plot_cap:
        ax.plot(fcst_t, fcst['cap'], ls='--', c='k')
    if m.logistic_floor and 'floor' in fcst and plot_cap:
        ax.plot(fcst_t, fcst['floor'], ls='--', c='k')
    if uncertainty and m.uncertainty_samples:
        ax.fill_between(fcst_t, fcst['yhat_lower'], fcst['yhat_upper'],
                        color='#0072B2', alpha=0.2)
    # Specify formatting to workaround matplotlib issue #12925
    locator = AutoDateLocator(interval_multiples=False)
    formatter = AutoDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.grid(True, which='major', c='gray', ls='-', lw=1, alpha=0.2)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig
    
# Plot results for one area
area = '1.0-48453000804'
m = tsModel(pg, ds_key, '15T', include_weather=False)
m.get_area_series(area, series='scooter')
m.transform_area_series(select_var='n')
m.prep_model_data()
m.build_model(scale=100, hourly=True, holidays_scale=50)
m.train_model()
n_periods = m.calculate_periods()
m.build_prediction_df(periods=n_periods)
m.future.dropna(inplace=True)
m.predict()
m.cv(initial='365 days', period='30 days', horizon='30 days', log=False)
total_preds = m.fcst

# generate and save figs here
fig = fb_plot(m.model, m.fcst, xlabel='Time', ylabel='N Scooters', figsize=(15, 6))
# fig.show()
fig.savefig('/home/bapfeld/scoothome/figures/prophet_example.png')
fig2 = m.model.plot_components(m.fcst)
fig2.savefig('/home/bapfeld/scoothome/figures/prophet_example_components.png')
fig3 = plot_cross_validation_metric(m.df_cv, metric='rmse')
fig3.savefig('/home/bapfeld/scoothome/figures/prophet_example_rmse.png')

# do the same for the in use
m2 = tsModel(pg, ds_key, '15T', include_weather=False)
m2.get_area_series(area, series='scooter')
m2.transform_area_series(select_var='n')
m2.prep_model_data()
m2.build_model(scale=100, hourly=True, holidays_scale=50)
m2.train_model()
n_periods = m2.calculate_periods()
m2.build_prediction_df(periods=n_periods)
m2.future.dropna(inplace=True)
m2.predict()
m2.cv(initial='365 days', period='30 days', horizon='30 days', log=False)
in_use_preds = m2.fcst

# generate and save figs here
fig = m2.model.plot(m2.fcst)
fig.savefig('/home/bapfeld/scoothome/figures/prophet_in_use_example.png')
fig2 = m2.model.plot_components(m2.fcst)
fig2.savefig('/home/bapfeld/scoothome/figures/prophet_in_use_example_components.png')
fig3 = plot_cross_validation_metric(m2.df_cv, metric='rmse')
fig3.savefig('/home/bapfeld/scoothome/figures/prophet_in_use_example_rmse.png')

# and combine both:
