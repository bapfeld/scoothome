import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import psycopg2
import sys, re, os
import configparser, argparse
from pandas.plotting import autocorrelation_plot
import statsmodels.api as sm
from statsmodels.graphics.api import qqplot
from statsmodels.tsa.stattools import adfuller

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
        
        
def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return config['postgres']

ini_path = '/home/bapfeld/scoothome/setup.ini'
pg = import_secrets(ini_path)
test_area = '9.0-48453001100'

m = tsFetch(pg)
m.get_area_series(test_area)

dat = m.area_series.copy()
dat.sort_values(['time'], inplace=True)

train = dat[dat['time'] < pd.to_datetime('2019-9-13')].copy()
train.set_index('time', inplace=True)
test = dat[dat['time'] >= pd.to_datetime('2019-9-13')].copy()
test.set_index('time', inplace=True)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12,8))
sm.graphics.tsa.plot_acf(train['n'].values.squeeze(), lags=300, ax=ax1)
sm.graphics.tsa.plot_pacf(train['n'], lags=40, ax=ax2)
plt.show()
plt.close()

# this is just the first flavor of adf test...can also set the regression parameter
adf_results = adfuller(dat['n'])
print(f'ADF Statistic: {adf_results[0]}')
print(f'p-value: {adf_results[1]}')
print('Critical Values:')
for key, value in adf_results[4].items():
    print(f'\t{key}: {value:.3f}')

adf_results = adfuller(dat['n'], regression='ct')
print(f'ADF Statistic: {adf_results[0]}')
print(f'p-value: {adf_results[1]}')
print('Critical Values:')
for key, value in adf_results[4].items():
    print(f'\t{key}: {value:.3f}')

adf_results = adfuller(dat['n'], regression='nc')
print(f'ADF Statistic: {adf_results[0]}')
print(f'p-value: {adf_results[1]}')
print('Critical Values:')
for key, value in adf_results[4].items():
    print(f'\t{key}: {value:.3f}')

from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
timeseries = dat['n']
fig = plt.figure(figsize=(10, 15))
ax1 = fig.add_subplot(511)
fig = plot_acf(timeseries, ax=ax1,
               title="Autocorrelation on Original Series") 
ax2 = fig.add_subplot(512)
fig = plot_acf(timeseries.diff().dropna(), ax=ax2, 
               title="1st Order Differencing")
ax3 = fig.add_subplot(513)
fig = plot_acf(timeseries.diff().diff().dropna(), ax=ax3, 
               title="2nd Order Differencing")
ax4 = fig.add_subplot(514)
fig = plot_acf(timeseries.diff().diff().diff().dropna(), ax=ax4, 
               title="3rd Order Differencing")
ax5 = fig.add_subplot(515)
fig = plot_acf(timeseries.diff().diff().diff().dropna(), ax=ax5, 
               title="4th Order Differencing")
fig.show()
plt.close()

fig = plot_pacf(timeseries.diff().dropna(), lags=40)
fig.show()
plt.close()

# maybe this says 3rd order?

# let's run some models and compare the AC
arma_mod10 = sm.tsa.ARMA(train['n'].values, (1, 0)).fit(disp=False)
arma_mod20 = sm.tsa.ARMA(train['n'].values, (2, 0)).fit(disp=False)
arma_mod30 = sm.tsa.ARMA(train['n'].values, (3, 0)).fit(disp=False)
arma_mod40 = sm.tsa.ARMA(train['n'], (4, 0)).fit(disp=False)
arma_mod50 = sm.tsa.ARMA(train['n'].values, (5, 0)).fit(disp=False)
arma_mod100 = sm.tsa.ARMA(train['n'].values, (10, 0)).fit(disp=False)
# arma_mod11 = sm.tsa.ARMA(train['n'].values, (1, 1)).fit(disp=False)
# arma_mod21 = sm.tsa.ARMA(train['n'].values, (2, 1)).fit(disp=False)

print(arma_mod10.aic, arma_mod20.aic, arma_mod30.aic, arma_mod40.aic, arma_mod50.aic, arma_mod100.aic)

# arma_mod31 = sm.tsa.ARMA(train['n'].values, (3, 1)).fit(disp=False)
# print(arma_mod31.aic)

# arma_mod22 = sm.tsa.ARMA(train['n'].values, (2, 2)).fit(disp=False)
# print(arma_mod22.aic)

# arma_21 appears to be best
print(arma_mod100.params)
sm.stats.durbin_watson(arma_mod100.resid)

r, q, p = sm.tsa.acf(arma_mod100.resid.squeeze(), fft=True, qstat=True)
data = np.c_[range(1,41), r[1:], q, p]
table = pd.DataFrame(data, columns=['lag', "AC", "Q", "Prob(>Q)"])
print(table.set_index('lag'))

# Here's an approach using pmdarima
import pmdarima as pm

def arimamodel(timeseries):
    automodel = pm.auto_arima(timeseries, 
                              start_p=1, 
                              start_q=1,
                              test="adf",
                              seasonal=False,
                              trace=True)
    return automodel

def plotarima(n_periods, timeseries, automodel, futureseries=None):
    # Forecast
    fc, confint = automodel.predict(n_periods=n_periods, 
                                    return_conf_int=True)
    # Weekly index
    fc_ind = pd.date_range(timeseries.index[timeseries.shape[0]-1], 
                           periods=n_periods, freq="W")
    # Forecast series
    fc_series = pd.Series(fc, index=fc_ind)    # Upper and lower confidence bounds
    lower_series = pd.Series(confint[:, 0], index=fc_ind)
    upper_series = pd.Series(confint[:, 1], index=fc_ind)    # Create plot
    plt.figure(figsize=(10, 6))
    plt.plot(timeseries)
    if futureseries is not None:
        plt.plot(futureseries, color="orange")
    plt.plot(fc_series, color="red")
    plt.xlabel("date")
    plt.ylabel(timeseries.name)
    plt.fill_between(lower_series.index, 
                     lower_series, 
                     upper_series, 
                     color="k", 
                     alpha=0.25)
    if futureseries is None:
        plt.legend(("past", "forecast", "95% confidence interval"),  
                   loc="upper left")
    else:
        plt.legend(("past", "real", "forecast", "95% confidence interval"),  
                   loc="upper left")
    plt.show()

automodel = arimamodel(train['n'])
plotarima(20, train['n'], automodel, test['n'])
plt.close()
