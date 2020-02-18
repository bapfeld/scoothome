import pandas as pd
from sodapy import Socrata
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import configparser, argparse
import os, time, datetime, re
import psycopg2
from sqlalchemy import create_engine
from darksky.api import DarkSky
from darksky.types import languages, units, weather
from collections import Counter
import multiprocessing
import sys
sys.path.append(os.path.expanduser('~/scoothome'))
from src.convert_to_ts import ts_maker

def import_secrets(ini_path):
    """Simple script to parse config file"""
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['socrata']['app_token'],
            config['postgres'],
            config['darksky']['key'])


class historicalWeather():
    """Class to get historical weather data and write to postgres database

    """
    def __init__(self, pg, ds_key, max_date=None):
        self.max_date = max_date
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
            time_check = [x > pd.to_datetime(self.max_date, utc=True) for x in times]
            times = [val for (val, boolean) in zip(times, time_check) if boolean]
            temps = [x.temperature for x in hist.hourly.data]
            temps = [val for (val, boolean) in zip(temps, time_check) if boolean]
            precips = [x.precip_intensity for x in hist.hourly.data]
            precips = [val for (val, boolean) in zip(precips, time_check) if boolean]
            rain_prob = [x.precip_probability for x in hist.hourly.data]
            rain_prob = [val for (val, boolean) in zip(rain_prob, time_check) if boolean]
            humidities = [x.humidity for x in hist.hourly.data]
            humidities = [val for (val, boolean) in zip(humidities, time_check) if boolean]
            wind = [x.wind_speed for x in hist.hourly.data]
            wind = [val for (val, boolean) in zip(wind, time_check) if boolean]
            clouds = [x.cloud_cover for x in hist.hourly.data]
            clouds = [val for (val, boolean) in zip(clouds, time_check) if boolean]
            uv = [x.uv_index for x in hist.hourly.data]
            uv = [val for (val, boolean) in zip(uv, time_check) if boolean]
            # self.new_weather = pd.DataFrame({'time': times, 
            #                                  'temp': temps,
            #                                  'current_rain': precips,
            #                                  'rain_prob': rain_prob,
            #                                  'humidity': humidities,
            #                                  'wind': wind,
            #                                  'cloud_cover': clouds,
            #                                  'uv': uv})
            self.write_to_sql(times, temps, precips, rain_prob, humidities, wind, clouds, uv)
            
        except:
            pass


def daterange(start_date, end_date, inclusive=True):
    """Simple function to return an iterator for a range of dates"""
    if inclusive:
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + datetime.timedelta(n)
    else:
        for n in range(int((end_date - start_date).days)):
            yield start_date + datetime.timedelta(n)

class updateFetch():
    """Class to update the underlying databases. 
       
       Will pull all new data in case script needs to be run after a gap of more than one day.

    """
    def __init__(self, app_token, pg, ds_key):
        self.app_token = app_token
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['host']
        self.pg_db = pg['database']
        self.pg_port = pg['port']
        self.ds_key = ds_key
        self.pg = pg
        self.engine = create_engine(f'postgresql://{self.pg_username}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}')

    def get_new_weather_history(self):
        days = [x for x in daterange(self.max_weather_date, datetime.datetime.today(), inclusive=False)]
        # create an object and make requests
        self.w = historicalWeather(self.pg, self.ds_key, self.max_weather_date)
        for day in days:
            self.w.fetch_day_history(day)
            time.sleep(1)
        
    def get_max_dates(self):
        """Get the maximum dates for both ride and weather tables"""
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            self.max_ride_date = pd.read_sql_query('SELECT MAX(start_time) from rides',
                                                   conn).iloc[0, 0]
            self.max_weather_date = pd.read_sql_query('SELECT MAX(time) from weather',
                                                      conn).iloc[0, 0]
        
            self.max_ts_date = pd.read_sql('SELECT MAX(time) from ts',
                                           conn).iloc[0, 0]

    def basic_clean(self, df):
        # Drop bad observations
        df.dropna(inplace=True)
        df = df[df['census_geoid_start'] != 'OUT_OF_BOUNDS']
        df = df[df['census_geoid_end'] != 'OUT_OF_BOUNDS']

        # Convert time objects
        df['start_time'] = pd.to_datetime(df['start_time'])
        df['end_time'] = pd.to_datetime(df['end_time'])

        # Convert some data typees
        df['council_district_start'] = df['council_district_start'].astype(float).astype(int)
        df['council_district_end'] = df['council_district_end'].astype(float).astype(int)
        df['census_geoid_start'] = df['census_geoid_start'].astype(int)
        df['census_geoid_end'] = df['census_geoid_end'].astype(int)
        df['month'] = df['month'].astype(int)
        df['hour'] = df['hour'].astype(int)
        df['day_of_week'] = df['day_of_week'].astype(int)
        df['year'] = df['year'].astype(int)

        # rename some columns
        df.rename(columns={'trip_duration': 'duration',
                           'trip_distance': 'distance',
                           'census_geoid_start': 'census_tract_start',
                           'census_geoid_end': 'census_tract_end'},
                   inplace=True)
        return df

    def get_new_ride_data(self, identifier="7d8e-dm7r"):
        client = Socrata("data.austintexas.gov", self.app_token)
        t = self.max_ride_date.strftime("%Y-%m-%dT%H:%M:%S")
        query = f'start_time > "{t}"'
        try:
            res = client.get(identifier, where=query, limit=1000000)
            new_rides = pd.DataFrame.from_records(res)
            self.new_rides = self.basic_clean(new_rides)
        except:
            self.new_rides = None

    def write_new_rides(self):
        self.new_rides.to_sql('rides', self.engine, if_exists='append', index=False)


class updateTS(multiprocessing.Process):
    """
    Class to convert rides to time series in a parallel multiprocessing environment.
    """
    def __init__(self, pg, vehicle_id, max_ride_date):
        multiprocessing.Process.__init__(self)
        self.pg = pg
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['host']
        self.pg_db = pg['database']
        self.pg_port = pg['port']
        self.vehicle_id = vehicle_id
        self.mrd = max_ride_date

    def fetch_rides(self):
        q = f"""(SELECT * FROM rides 
                WHERE start_time <= '{self.mrd}'
                AND device_id = '{self.vehicle_id}' 
                ORDER BY start_time DESC
                LIMIT 1)
                UNION ALL
                SELECT * FROM rides 
                WHERE start_time > '{self.mrd}' 
                AND device_id = '{self.vehicle_id}'"""
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            self.rides = pd.read_sql(q, conn)
        if self.rides.vehicle_type[1] == 'scooter':
            self.out_dir = '/tmp/scooter_records/'
        else:
            self.out_dir = '/tmp/bicycle_records/'

    def new_rides_to_ts(self):
        self.rides['location_start_id'] = self.rides['council_district_start'].astype(float).astype(str) + '-' + self.rides['census_tract_start'].astype(str)
        self.rides['location_start_id'] = [re.sub(r'^(\d)-', r'0\1-', x) for x in self.rides['location_start_id']]
        self.rides['location_end_id'] = self.rides['council_district_end'].astype(float).astype(str) + '-' + self.rides['census_tract_end'].astype(str)
        self.rides['location_end_id'] = [re.sub(r'^(\d)-', r'0\1-', x) for x in self.rides['location_end_id']]
        self.rides['date'] = self.rides['start_time'].astype(str).str.extract(r'(\d\d\d\d-\d\d-\d\d)?')

        tsm = ts_maker(self.rides)
        tsm.sql_setup(self.pg)
        tsm.where_am_i(self.vehicle_id)
        tsm.ts_list_to_txt(self.out_dir, self.vehicle_id)
        


def read_device_records(vehicle_type):
    """Function to read device records from a directory as written by ts_maker"""
    if vehicle_type == 'scooter':
        dir_path = '/tmp/scooter_records/'
    else:
        dir_path = '/tmp/bicycle_records/'
    event_list = []
    f_list = [x for x in os.listdir(dir_path) if x.endswith('txt')]
    f_list = [os.path.join(dir_path, x) for x in f_list]
    for f in f_list:
        with open(f, 'r') as f_in:
            event_list.extend(f_in.readlines())
    return event_list

def add_cols(counts):
    """Simple function for adding a few columns to the counts dataframe"""
    counts['area'] = counts['index'].str.extract(r'^(.*?)--')
    counts['time'] = pd.to_datetime(counts['index'].str.extract(r'--(.*?)$'))
    counts['district'] = counts['index'].str.extract(r'(^.*?)-').astype(float).astype(int)
    counts['tract'] = counts['area'].str.extract(r'-(.*?$)').astype(int)
    counts.drop(columns=['index'], inplace=True)
    return counts

def records_to_counts(vehicle_type):
    """Converts vehicle records list to a counds dataframe"""
    if vehicle_type == 'scooter':
        col_name = 'n'
    else:
        col_name = 'bike_n'
    event_list = read_device_records(vehicle_type)
    counts = pd.DataFrame.from_dict(Counter(event_list),
                                        orient='index',
                                        columns=[col_name]).reset_index()
    counts = add_cols(counts)
    return counts
    

def estimate_actual_usage(vehicle_type, dat):
    """Function to estimate actual usage of devices"""
    if vehicle_type == 'scooter':
        col_name = 'in_use'
    else:
        col_name = 'bike_in_use'
    dat = dat[dat['vehicle_type'] == vehicle_type]
    dat['location_start_id'] = dat['council_district_start'].astype(float).astype(str) + '-' + dat['census_tract_start'].astype(str)
    dat['full_index'] = dat['location_start_id'] + '--' + dat['start_time'].astype(str)
    counts = pd.DataFrame.from_dict(Counter(dat['full_index']),
                                    orient='index',
                                    columns=[col_name]).reset_index()
    counts = add_cols(counts)
    return counts
    

def combine_multi_ts(pg, dat):
    """Combines new results from scooters and bikes for both totals and in use estimates"""
    scooters = records_to_counts('scooter')
    bikes = records_to_counts('bicycle')
    df = scooters.merge(bikes, how='outer', on=['area', 'time', 'district', 'tract'])
    scooter_use = estimate_actual_usage('scooter', dat)
    bike_use = estimate_actual_usage('bicycle', dat)
    df = df.merge(scooter_use, how='outer', on=['area', 'time', 'district', 'tract'])
    df = df.merge(bike_use, how='outer', on=['area', 'time', 'district', 'tract'])
    return df

def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the .ini file containing the app token",
        required=False,
    )
    parser.add_argument(
        '--num_proc',
        help="Number of processes to run in parallel",
        required=True,
    )
    return parser.parse_args()
    
def main():    
    args = initialize_params()
    app_token, pg, ds_key = import_secrets(os.path.expanduser(args.ini_path))

    upd = updateFetch(app_token, pg, ds_key)
    upd.get_max_dates()
    upd.get_new_ride_data()
    old_max_date = upd.max_ride_date

    def multi_ts(vehicle_id):
        upd = updateTS(pg, vehicle_id, old_max_date)
        upd.fetch_rides()
        upd.new_rides_to_ts()
    
    if upd.new_rides is not None:
        upd.write_new_rides()
        ids = pd.unique(upd.new_rides['device_id'])
        pool = multiprocessing.Pool(processes=int(args.num_proc))
        pool.imap(multi_ts, ids)
        totals = combine_multi_ts(pg, upd.new_rides)
        totals.to_sql('ts', self.engine, if_exists='append', chunksize=20000)

if __name__ == "__main__":
    main()
