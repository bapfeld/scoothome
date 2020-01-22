import pandas as pd
import configparser, argparse
import os
import psycopg2
from fbprophet import Prophet

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['postgres'], config['darksky']['key'])

class tsModel():
    """Class to query required underlying data, estimate a model, and forecast.

    """
    def __init__(self, pg):
        self.conn = psycopg2.connect(database=pg['database'],
                                     user=pg['username'],
                                     password=pg['password'],
                                     port=pg['port'],
                                     host=pg['host'])
        
    def get_area_series(self, idx):
        q = f'SELECT * FROM ts WHERE area = {idx}'
        self.area_series = pd.read_sql_query(q, self.conn)

    def get_weather_data(self):
        start_time = self.area_series['time'].min()
        end_time = self.area_series['time'].max()
        q = f'SELECT * FROM weather WHERE (time >= {start_time} & time <= {end_time})'
        self.weather = pd.read_sql_query(q, self.conn)
        self.weather.resample('15T', on='time').pad()

    def prep_model_data(self):
        self.dat = pd.merge(self.area_series, self.weather, how='right', on='time')
        self.dat['n'].fillna(0, inplace=True)
        self.dat.drop(columns=['area'], inplace=True)
        self.dat.rename(columns={'time': 'ds', 'n': 'y'}, inplace=True)

    def build_model(self, scale=0.05, varlist=['temp', 'current_rain',
                                               'rain_prob', 'humidity',
                                               'wind', 'cloud_cover', 'uv']):
        self.model = Prophet(changepoint_prior_scale=scale)
        if len(varlist) > 0:
            for v in varlist:
                self.model.add_regressor(v)

    def train_model(self):
        self.model.fit(self.dat)

    def build_prediction_df(self, periods=72):
        self.get_weather_pred()
        future = self.model.make_future_dataframe(periods=periods, freq='H')
        self.future = pd.merge(future, self.future_weather, how='',
                               left_on='ds', right_on='time')

    def get_weather_pred(self):
        pass

    def predict(self):
        pass

    def plot_results(self):
        pass
        

def main(pg):
    m = tsModel(pg)


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
