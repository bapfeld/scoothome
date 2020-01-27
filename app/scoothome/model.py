import pandas as pd
import configparser, argparse
import os, datetime
import psycopg2
from fbprophet import Prophet
from darksky.api import DarkSky
from darksky.types import languages, units, weather

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['postgres'], config['darksky']['key'])

class tsModel():
    """Class to query required underlying data, estimate a model, and forecast.

    """
    def __init__(self, pg, ds_key):
        self.conn = psycopg2.connect(database=pg['database'],
                                     user=pg['username'],
                                     password=pg['password'],
                                     port=pg['port'],
                                     host=pg['host'])
        self.ds_key = ds_key
        self.init_ds_obj()
        
    def init_ds_obj(self):
        self.ds = DarkSky(self.ds_key)
        
    def get_area_series(self, idx):
        q = f"SELECT * FROM ts WHERE area = '{idx}'"
        self.area_series = pd.read_sql_query(q, self.conn)

    def get_weather_data(self):
        start_time = self.area_series['time'].min()
        end_time = self.area_series['time'].max()
        q = f"SELECT * FROM weather WHERE time >= '{start_time}' AND time <= '{end_time}'"
        self.weather = pd.read_sql_query(q, self.conn)
        self.weather = self.weather.set_index('time').resample('15T').pad()

    def prep_model_data(self):
        self.dat = pd.merge(self.area_series, self.weather, how='right', on='time')
        self.dat['n'].fillna(0, inplace=True)
        self.dat.drop(columns=['area', 'district', 'tract'], inplace=True)
        self.dat.rename(columns={'time': 'ds', 'n': 'y'}, inplace=True)

    def make_special_events(self):
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
        

    def build_model(self, scale=0.05, varlist=['temp', 'wind', 'cloud_cover', 'humidity']):
        self.make_special_events()
        self.model = Prophet(changepoint_prior_scale=scale, holidays=self.holidays)
        if len(varlist) > 0:
            for v in varlist:
                self.model.add_regressor(v)

    def train_model(self):
        self.model.fit(self.dat)

    def build_prediction_df(self, lat, lon, periods=192, get_forecast=True):
        if get_forecast:
            self.get_weather_pred(lat, lon)
        future = self.model.make_future_dataframe(periods=periods, freq='15T')
        self.future = pd.merge(future, self.weather, how='left', left_on='ds', right_on='time')
        self.future.update(self.future_weather)

    def get_weather_pred(self, lat, lon):
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
        self.future_weather = self.future_weather.set_index('time').resample('15T').pad()
        self.future_weather = self.future_weather.tz_convert(None)

    def predict(self):
        self.fcst = self.model.predict(self.future)

    def plot_results(self):
        self.fig = self.model.plot(self.fcst)
        #fig.savefig(outflow)

    def run(self,
            area_key,
            lat,
            lon,
            varlist=['temp', 'wind', 'cloud_cover', 'humidity']):
        self.get_area_series(area_key)
        self.get_weather_data()
        self.prep_model_data()
        self.build_model(varlist=varlist)
        self.train_model()
        t_diff = datetime.datetime.now() + datetime.timedelta(days=2) - self.area_series['time'].max()
        hours_diff = (t_diff.days * 24) + (t_diff.seconds / 3600)
        periods = max([192, int(hours_diff) * 4])
        self.build_prediction_df(lat, lon, periods)
        self.predict()
        # self.plot_results()

    def save_results(self, save_path):
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
