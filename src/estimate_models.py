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
from app.scoothome.model import tsModel, import_secrets
import configparser, argparse
from itertools import product

def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the .ini file containing the app token",
        required=False,
    )
    parser.add_argument(
        '--area_list_file',
        help="Path to a list of areas to run",
        required=True,
    )
    parser.add_argument(
        '--vehicle_type',
        help="Which type of vehicle do you want to process? Options are 'scooter' or 'bicycle'. Default is scooter.",
        required=True,
        default='scooter'
    )
    parser.add_argument(
        '--completed_area_file',
        help="File to write completed areas to",
        required=True
    )
    parser.add_argument(
        '--proc_num',
        help="For a script running multiple processes at once, which number is this?",
        required=False,
    )
    parser.add_argument(
        '--total_processes',
        help="Total number of processes being run at once",
        required=True,
        default=1
    )
    return parser.parse_args()

def generate_models(pg, ds_key, bin_window, hs, cps, area, vehicle_type):
    m = tsModel(pg, ds_key, bin_window, include_weather=False)
    m.get_area_series(area, series=vehicle_type)
    m.transform_area_series(select_var='n')
    m.prep_model_data()
    if m.dat.shape[0] > 9:
        m.build_model(scale=cps, hourly=True, holidays_scale=hs)
        m.train_model()
        n_periods = m.calculate_periods()
        m.build_prediction_df(periods=n_periods)
        m.future.dropna(inplace=True)
        m.predict()
        m.preds_to_sql(var='n')
    m.get_area_series(area, series=vehicle_type)
    m.transform_area_series(select_var='in_use')
    m.prep_model_data()
    if m.dat.shape[0] > 9:
        m.build_model(scale=cps, hourly=True, holidays_scale=hs)
        m.train_model()
        n_periods = m.calculate_periods()
        m.build_prediction_df(periods=n_periods)
        m.future.dropna(inplace=True)
        m.predict()
        m.preds_to_sql(var='in_use')

def main():
    args = initialize_params()
    vehicle_type = args.vehicle_type
    pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))
    bin_window = '15T'
    hs = 50
    cps = 100
    t_processes = int(args.total_processes)
    if args.proc_num is not None:
        proc_num = int(args.proc_num)
    with open(os.path.expanduser(args.area_list_file), 'r') as f_in:
        area_list = [x.strip() for x in f_in.readlines()]
    with open(os.path.expanduser(args.completed_area_file), 'r') as f_in:
        completed_list = [x.strip() for x in f_in.readlines()]
    if t_processes > 1:
        a_lists = np.array_split(area_list, t_processes)
        area_list = [x for x in a_lists[proc_num - 1] if x not in completed_list]
        for i, area in enumerate(area_list):
            if i % proc_num == 0:
                generate_models(pg, ds_key, bin_window, hs, cps, area, vehicle_type)
                with open(os.path.expanduser(args.completed_area_file), 'a') as f_out:
                    f_out.writelines(area)
                    f_out.writelines('\n')
            else:
                pass
    else:
        area_list = [x for x in area_list if x not in completed_list]
        generate_models(pg, ds_key, bin_window, hs, cps, area, vehicle_type)
    

if __name__ == "__main__":
    main()
 
