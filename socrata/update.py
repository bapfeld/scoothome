import pandas as pd
from sodapy import Socrata
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import configparser, argparse
import os, time, datetime
import psycopg2
from get_past_weather import historicalWeather, daterange

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['socrata']['app_token'],
            config['postgres'],
            config['openweather']['key'])

class updater():
    """Class to update the underlying databases. 
       
       Will pull all new data in case script needs to be run after a gap of more than one day.

    """
    def __init__(self, pg, ds_key):
        self.conn = psycopg2.connect(database=pg['database'],
                                     user=pg['username'],
                                     password=pg['password'],
                                     port=pg['port'],
                                     host=pg['host'])
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['localhost']
        self.pg_db = pg['database']
        self.pg_port = pg['port']
        self.ds_key = ds_key
        self.engine = create_engine(f'postgresql://{self.pg_username}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}')

    def get_new_weather_history(self):
        days = [x for x in daterange(self.max_weather_date, datetime.date.today(), inclusive=False)]
        # create an object and make requests
        self.w = historicalWeather(pg, ds_key)
        for day in days:
            self.w.fetch_day_history(day)
            time.sleep(1)
        
    def get_max_dates(self):
        """Get the maximum dates for both ride and weather tables"""
        self.max_ride_date = pd.read_sql_query('SELECT MAX(start_time) from rides', self.conn).iloc[0, 0]
        self.max_weather_date = pd.read_sql_query('SELECT MAX(start_time) from weather', self.conn).iloc[0, 0]

    def basic_clean(self, df):
        # Drop bad observations
        df.dropna(inplace=True)
        df = df[df['census_geoid_start'] != 'OUT_OF_BOUNDS']
        df = df[df['census_geoid_end'] != 'OUT_OF_BOUNDS']

        # Convert time objects
        df['start_time'] = pd.to_datetime(df['Start Time'], format="%m/%d/%YT%I:%M:%S")
        df['end_time'] = pd.to_datetime(df['End Time'], format="%m/%d/%YT%I:%M:%S")

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
        client = Socrata("data.austintexas.gov", app_token)
        t = self.max_ride_date.strftime("%Y-%m-%dT%H:%M:%S")
        query = f'start_time > "{t}"'
        try:
            res = client.get(identifier, where=query, limit=1000000)
            new_rides = pd.DataFrame.from_records(res)
            self.new_rides = self.basic_clean(new_rides)
        except:
            pass

    def write_new_rides(self):
        self.new_rides.to_sql(rides, self.engine, if_exists='append', index=False)
            

def write_to_db(database, user, password, port):
    pass

def fetch_new_data(client, resource, start_date):
    results = client.get(resource, where=f'Start Time > {latest_start_time}')
    # results_df = pd.DataFrame.from_records(results)
    return results
    
# '/home/bapfeld/scoothome/socrata/socrata.ini'
# micromobility data: "7d8e-dm7r"

def main():
    def initialize_params():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--ini_path',
            help="Path to the .ini file containing the app token",
            required=False,
        )
        return parser.parse_args()
    args = initialize_params()
    app_token, pg, ow_key = import_secrets(os.path.expanduser(args.ini_path))

    # Establish a client to query the database
    

    # Get latest dates for the different databases

    # Fetch new data

    # Write new data back to the database


if __name__ == "__main__":
    main()
