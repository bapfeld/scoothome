import configparser, argparse
import os, datetime
import psycopg2
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import time

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['postgres'], config['darksky']['key'])
    
def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the .ini file containing the app token",
        required=False,
    )
    parser.add_argument(
        '--start_day',
        help="String representation of when to start requesting daily data. E.g. 2019-01-01",
        required=True,
    )
    parser.add_argument(
        '--end_day',
        help="String representation of when to stop requesting daily data (inclusive). E.g. 2019-12-31",
        required=True,
    )
    return parser.parse_args()

class historicalWeather():
    """Class to get historical weather data and write to postgres database

    """
    def __init__(self, pg, ds_key):
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['host']
        self.pg_db = pg['database']
        self.pg_port = pg['port']
        self.ds_key = ds_key
        self.atx_lat = 30.267151
        self.atx_lon = -97.743057
        self.ds_key = ds_key
        self.init_ds_obj()

    def write_to_sql(self, times, temps, precips, rain_prob, humidities, wind, clouds, uv):
        with psycopg2.connect(dbname=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              host=self.pg_host,
                              port=self.pg_port) as conn:
            with conn.cursor() as curs:
                pg_query = """INSERT INTO weather 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                              ON CONFLICT DO NOTHING"""
                curs.executemany(pg_query, zip(times, temps, precips, rain_prob, humidities, wind, clouds, uv))
                conn.commit()

    def init_ds_obj(self):
        self.ds = DarkSky(self.ds_key)
        
    def fetch_day_history(self, day):
        try:
            hist = self.ds.get_time_machine_forecast(self.atx_lat, self.atx_lon,
                                                     extend=False,
                                                     lang=languages.ENGLISH, units=units.AUTO,
                                                     exclude=[weather.MINUTELY, weather.ALERTS],
                                                     timezone='UTC',
                                                     time=day)
            times = [x.time for x in hist.hourly.data]
            temps = [x.temperature for x in hist.hourly.data]
            precips = [x.precip_intensity for x in hist.hourly.data]
            rain_prob = [x.precip_probability for x in hist.hourly.data]
            humidities = [x.humidity for x in hist.hourly.data]
            wind = [x.wind_speed for x in hist.hourly.data]
            clouds = [x.cloud_cover for x in hist.hourly.data]
            uv = [x.uv_index for x in hist.hourly.data]
            self.write_to_sql(times, temps, precips, rain_prob, humidities, wind, clouds, uv)
        except:
            pass


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + datetime.timedelta(n)
        
def main():    
    args = initialize_params()
    pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))

    # set up the days to request
    start_date = datetime.datetime.strptime(args.start_day, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(args.end_day, "%Y-%m-%d")
    days = [x for x in daterange(start_date, end_date)]

    # create an object and make requests
    w = historicalWeather(pg, ds_key)
    for i, day in enumerate(days):
        # print(i)
        w.fetch_day_history(day)
        time.sleep(1)



if __name__ == "__main__":
    main()
