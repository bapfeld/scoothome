import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import psycopg2
import sys, re, os
sys.path.append('/home/bapfeld/scoothome')
from app.scoothome.model import tsModel, import_secrets
import configparser, argparse
from pandas.plotting import autocorrelation_plot
import statsmodels.api as sm
from statsmodels.graphics.api import qqplot
from statsmodels.tsa.stattools import adfuller

ini_path = '/home/bapfeld/scoothome/setup.ini'
pg, ds_key = import_secrets(ini_path)
test_area = '9.0-48453001100'

m = tsModel(pg, ds_key)
m.get_area_series(test_area)

dat = m.area_series
dta = dat[['time', 'n']]
autocorrelation_plot(dta)
plt.show()
plt.close()

fig, ax1, ax2 = plt.subplots(2, 1, figsize=(12,8))
sm.graphics.tsa.plot_acf(dta.values.squeeze(), lags=40, ax=ax1)
sm.graphics.tsa.plot_pacf(dta, lags=40, ax=ax2)
plt.show()
plt.close()

# this is just the first flavor of adf test...can also set the regression parameter
adf_results = adfuller(dat['n'])
print(f'ADF Statistic: {adf_results[0]}')
print(f'p-value: {adf_results[1]}')
print('Critical Values:')
for key, value in result[4].items():
    print(f'\t{key}: {value:.3f}')

adf_results = adfuller(np.log(dat['n'] + 1))
print(f'ADF Statistic: {adf_results[0]}')
print(f'p-value: {adf_results[1]}')
print('Critical Values:')
for key, value in result[4].items():
    print(f'\t{key}: {value:.3f}')

