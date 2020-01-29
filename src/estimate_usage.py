import pandas as pd
from collections import Counter
import psycopg2, configparser

def clean_df(df, device_type=None):
    # Need to drop observations with essential missing data
    df.dropna(inplace=True)

    # And drop observations where the start/stop is out of bounds
    df = df[df['Census Tract Start'] != 'OUT_OF_BOUNDS']
    df = df[df['Census Tract End'] != 'OUT_OF_BOUNDS']

    # Want to create a new variable to uniquely identify areas
    df['location_start_id'] = df['Council District (Start)'].astype(str) + '-' + df['Census Tract Start']
    df['location_end_id'] = df['Council District (End)'].astype(str) + '-' + df['Census Tract End']

    # Convert time objects
    df['start_time'] = pd.to_datetime(df['Start Time'], format="%m/%d/%Y %I:%M:%S %p")
    df['end_time'] = pd.to_datetime(df['End Time'], format="%m/%d/%Y %I:%M:%S %p")
    df['date'] = df['Start Time'].str.extract(r'(\d\d/\d\d/\d\d\d\d)?')

    # Keep only the relevant information
    drop_cols = ['Start Time',
                 'End Time',
                 'Modified Date',
                 'Month',
                 'Hour',
                 'Day of Week',
                 'Council District (Start)',
                 'Council District (End)',
                 'Year',
                 'Census Tract Start',
                 'Census Tract End']
    df.drop(drop_cols, axis=1, inplace=True)
    df.rename(columns={'ID': 'trip_id',
                        'Device ID': 'device_id',
                        'Vehicle Type': 'vehicle_type',
                        'Trip Duration': 'duration',
                        'Trip Distance': 'distance'},
               inplace=True)

    # Allow subset of device type
    if device_type is not None:
        df = df[df.vehicle_type == device_type].copy()

    # Sort and reset the index
    df.sort_values(['start_time'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Return the result
    return df


dat = pd.read_csv(dat_path, dtype={'Census Tract Start': object,
                                   'Census Tract End': object})
dat = clean_df(dat, 'scooter')

# Generate an area-time stamp variable
dat['full_index'] = dat['location_start_id'] + '--' + dat['start_time']

# Find he unique set and count
counts = pd.DataFrame.from_dict(Counter(dat['full_index']),
                                orient='index',
                                columns='in_use').reset_index()
counts['area'] = counts['index'].str.extract(r'^(.*?)--')
counts['time'] = counts['index'].str.extract(r'--(.*?)$')

# this represents the actual usage
# so write to the db
config = configparser.ConfigParser()
config.read(ini_path)
pg_username = pg['username']
pg_password = pg['password']
pg_host = pg['localhost']
pg_db = pg['database']
pg_port = pg['port']

with psycopg2.connect(dbname=pg_db, user=pg_username,
                      password=pg_password, host=pg_host,
                      port=pg_port) as conn:
    with conn.cursor() as curs:
        conn.executemany("""UPDATE ts SET in_use = %s WHERE (time = %s AND area = %s)""",
                         zip(counts.in_use, counts.time, counts.area))
