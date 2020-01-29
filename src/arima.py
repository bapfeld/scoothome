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
            q = f"SELECT n, in_use FROM ts WHERE area = '{idx}'"
        else:
            q = f"SELECT bike_n, bike_in_use FROM ts WHERE area = '{idx}'"
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
# dat.set_index('time').resample('15T').sum().fillna(0).reset_index(inplace=True)
dta = dat[['time', 'n']]

train = dat[dat['time'] < pd.to_datetime('2019-9-13')].copy()
train.set_index('time', inplace=True)
test = dat[dat['time'] >= pd.to_datetime('2019-9-13')].copy()
test.set_index('time', inplace=True)
# dta.set_index('time', inplace=True)
# autocorrelation_plot(dta)
# plt.show()
# plt.close()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12,8))
sm.graphics.tsa.plot_acf(dta.values.squeeze(), lags=300, ax=ax1)
sm.graphics.tsa.plot_pacf(dta, lags=40, ax=ax2)
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

# let's run some models and compare the AC
arma_mod10 = sm.tsa.ARMA(train['n'].values, (1, 0)).fit(disp=False)
arma_mod20 = sm.tsa.ARMA(train['n'].values, (2, 0)).fit(disp=False)
arma_mod30 = sm.tsa.ARMA(train['n'].values, (3, 0)).fit(disp=False)
arma_mod40 = sm.tsa.ARMA(train['n'].values, (4, 0)).fit(disp=False)
arma_mod50 = sm.tsa.ARMA(train['n'].values, (5, 0)).fit(disp=False)
arma_mod100 = sm.tsa.ARMA(train['n'].values, (10, 0)).fit(disp=False)
# arma_mod11 = sm.tsa.ARMA(train['n'].values, (1, 1)).fit(disp=False)
# arma_mod21 = sm.tsa.ARMA(train['n'].values, (2, 1)).fit(disp=False)

print(arma_mod10.aic, arma_mod20.aic, arma_mod30.aic, arma_mod40.aic)

arma_mod31 = sm.tsa.ARMA(train['n'].values, (3, 1)).fit(disp=False)
print(arma_mod31.aic)

arma_mod22 = sm.tsa.ARMA(train['n'].values, (2, 2)).fit(disp=False)
print(arma_mod22.aic)

# arma_21 appears to be best
print(arma_mod100.params)
sm.stats.durbin_watson(arma_mod100.resid)

r, q, p = sm.tsa.acf(arma_mod100.resid.squeeze(), fft=True, qstat=True)
data = np.c_[range(1,41), r[1:], q, p]
table = pd.DataFrame(data, columns=['lag', "AC", "Q", "Prob(>Q)"])
print(table.set_index('lag'))

# predictions?
pred = arma_mod100.predict(47000, 100000, dynamic=True)

fig, ax = plt.subplots(figsize=(12, 8))
ax = train.loc['2019-06-01 00:00:00':]['n'].plot(ax=ax)
fig = arma_mod100.plot_predict(pd.to_datetime('2019-08-01'), pd.to_datetime('2020-01-20'),
                               dynamic=True, ax=ax, plot_insample=False)
