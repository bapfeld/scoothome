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

def initialize_params():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--ini_path',
            help="Path to the .ini file containing the app token",
            required=False,
        )
        # parser.add_argument(
        #     '--log_transform',
        #     help="Should the outcome variable be logged? Defaults to false",
        #     required=False,
        #     action="store_true"
        # )
        parser.add_argument(
            '--changepoint_prior_scale',
            help="What value should be used for the changepoint prior? FB Prophet default is 0.05. Higher values make fitting more flexible.",
            required=True,
            default=0.05
        )
        # parser.add_argument(
        #     '--bin_window',
        #     help="Length of time to use for binning ride data. Default is 15M ('15T')",
        #     required=False,
        #     default='15T'
        # )
        parser.add_argument(
            '--pdf_dir',
            help="Directory path to where to save the pdfs from the changepoint specification",
            required=True,
        )
        return parser.parse_args()

def modeler(pg, ds_key, area, log, bin_window, cps, hs):
    m = tsModel(pg, ds_key, bin_window)
    m.get_area_series(area, log)
    m.get_weather_data()
    m.prep_model_data()
    if cps in ['15T', '1H']:
            m.build_model(scale=cps, hourly=True, holidays_scale=hs)
    else:
            m.build_model(scale=cps, holidays_scale=hs)
    m.train_model()
    m.build_prediction_df(lat = 30.267151, lon = -97.743057, periods=192)
    m.future.dropna(inplace=True)
    m.predict()
    m.cv(initial='365 days', period='90 days', horizon='30 days', log=log)
    return m
    
    
def main():
    args = initialize_params()
    pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))
    dir_out = os.path.expanduser(args.pdf_dir)
    test_area = '9.0-48453001100'
    bin_sizes = ['15T', '1H', '6H', '1D']
    log_transforms = [False]
    holiday_scales = [5.0, 10.0, 20.0]
    opts = [bin_sizes, log_transforms, holiday_scales]
    for c in product(*opts):
        f_out = dir_out + '_'.join(list(map(str, c))) + '_' + str(args.changepoint_prior_scale) + '.pdf'
        if not os.path.exists(f_out):
            m = modeler(pg, ds_key,
                        area=test_area,
                        log=c[1],
                        bin_window=c[0],
                        cps=args.changepoint_prior_scale,
                        hs=c[2])
            with PdfPages(f_out) as pdf:
                fig = m.model.plot(m.fcst)
                pdf.savefig()
                fig2 = m.model.plot_components(m.fcst)
                pdf.savefig()
                fig3 = plot_cross_validation_metric(m.df_cv, metric='rmse')
                pdf.savefig()

if __name__ == "__main__":
    main()

