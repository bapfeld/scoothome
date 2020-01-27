import pandas as pd
from fbprophet import Prophet
import psycopg2
from matplotlib.backends.backend_pdf import PdfPages
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import sys
sys.path.append('/home/bapfeld/scoothome')
from app.scoothome.model import tsModel, import_secrets
import configparser


with open('/home/bapfeld/scoothome/data/area_id_list.txt', 'r') as f:
    area_list = f.readlines()
area_list = [x.strip() for x in area_list]

pg, ds_key = import_secrets('/home/bapfeld/scoothome/setup.ini')

# let's just fetch the weather forecast a single time...
weather_only = tsModel(pg, ds_key)
weather_only.get_weather_pred(lat = 30.267151, lon = -97.743057)


for area in area_list:
    f_out = f'/home/bapfeld/scoothome/figures/ts/{area}.pdf'
    m = tsModel(pg, ds_key)
    m.get_area_series(area)
    if m.area_series.shape[0] > 100:
        m.get_weather_data()
        m.prep_model_data()
        m.build_model() # potential to change weather stuff here
        m.train_model()
        m.future_weather = weather_only.future_weather
        m.build_prediction_df(lat = 30.267151, lon = -97.743057, periods=192, get_forecast=False)
        m.future.dropna(inplace=True)
        m.predict()
        with PdfPages(f_out) as pdf:
            fig = m.model.plot(m.fcst)
            pdf.savefig()
            fig2 = m.model.plot_components(m.fcst)
            pdf.savefig()
            fig.close()
            fig2.close()
    

# with PdfPages('/home/bapfeld/scoothome/figures/estimation_by_area_jan.pdf') as pdf:
#     for area in area_list:
#         test_dat = dat[dat['area'] == area].copy().reset_index(drop=True)
#         test_dat.drop(columns=['area'], inplace=True)
#         test_dat.rename(columns={'time': 'ds', 'n': 'y'}, inplace=True)

#         model = Prophet(changepoint_prior_scale=0.05)
#         model.fit(test_dat)
#         future = model.make_future_dataframe(periods=300, freq='H')
#         fcst = model.predict(future)
#         fig = model.plot(fcst)
#         # fig.show()
#         pdf.savefig()

#         fig2 = model.plot_components(fcst)
#         # fig2.show()
#         pdf.savefig()

