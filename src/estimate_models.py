import pandas as pd
import numpy as np
from fbprophet import Prophet
from fbprophet.diagnostics import cross_validation, performance_metrics
from fbprophet.plot import plot_cross_validation_metric
import psycopg2
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import sys, re, os
sys.path.append(os.path.expanduser('~/scoothome'))
from src.model import tsModel, import_secrets
import configparser, argparse
from itertools import product
import multiprocessing as mp

def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the .ini file containing the app token",
        required=False,
    )
    parser.add_argument(
        '--vehicle_type',
        help="Which type of vehicle do you want to process? Options are 'scooter' or 'bicycle'. Default is scooter.",
        required=True,
        default='scooter'
    )
    parser.add_argument(
        '--num_proc',
        help="Number of processes to run in parallel",
        required=True,
    )
    return parser.parse_args()

def generate_models(pg, ds_key, bin_window, hs, cps, area, vehicle_type):
    m = tsModel(pg, ds_key, bin_window, include_weather=False)
    m.get_area_series(area, series=vehicle_type)
    if vehicle_type == 'scooter':
        m.transform_area_series(select_var='n')
    else:
        m.transform_area_series(select_var='bike_n')
    m.prep_model_data()
    if m.dat.shape[0] > 9:
        m.build_model(scale=cps, hourly=True, holidays_scale=hs)
        m.train_model()
        n_periods = m.calculate_periods()
        m.build_prediction_df(periods=n_periods)
        m.future.dropna(inplace=True)
        m.predict()
        if vehicle_type == 'scooter':
            m.preds_to_sql(var='n')
        else:
            m.preds_to_sql(var='bike_n')
    m.get_area_series(area, series=vehicle_type)
    if vehicle_type == 'scooter':
        m.transform_area_series(select_var='in_use')
    else:
        m.transform_area_series(select_var='bike_in_use')
    m.prep_model_data()
    if m.dat.shape[0] > 9:
        m.build_model(scale=cps, hourly=True, holidays_scale=hs)
        m.train_model()
        n_periods = m.calculate_periods()
        m.build_prediction_df(periods=n_periods)
        m.future.dropna(inplace=True)
        m.predict()
        if vehicle_type == 'scooter':
            m.preds_to_sql(var='in_use')
        else:
            m.preds_to_sql(var='bike_in_use')

def gen_modeler(a, pg, ds_key, bin_window, hs, cps, vehicle_type):
    generate_models(pg, ds_key, bin_window, hs, cps, a, vehicle_type)
        
def main():
    args = initialize_params()
    vehicle_type = args.vehicle_type
    pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))
    bin_window = '15T'
    hs = 50
    cps = 100
    n_processes = int(args.num_proc)
    with psycopg2.connect(database=pg['database'],
                              user=pg['username'],
                              password=pg['password'],
                              port=pg['port'],
                              host=pg['host']) as conn:
        area_df = pd.read_sql('SELECT DISTINCT(area) FROM ts', conn)


    pool = mp.Pool(processes=n_processes)
    pool.map(gen_modeler, product(area_df['area'], [pg], [ds_key],
                                  [bin_window], [hs], [cps],
                                  [vehicle_type]))


if __name__ == "__main__":
    main()
 
