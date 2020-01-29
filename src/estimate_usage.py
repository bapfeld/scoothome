import pandas as pd
from collections import Counter
import psycopg2, configparser

config = configparser.ConfigParser()
config.read(ini_path)
pg_username = pg['username']
pg_password = pg['password']
pg_host = pg['host']
pg_db = pg['database']
pg_port = pg['port']

with psycopg2.connect(dbname=pg_db, user=pg_username,
                      password=pg_password, host=pg_host,
                      port=pg_port) as conn:
    dat = pd.read_sql('SELECT council_district_start, census_tract_start, start_time FROM rides', conn)

# Generate an area-time stamp variable
dat['location_start_id'] = dat['council_district_start'].astype(float).astype(str) + '-' + dat['census_tract_start'].astype(str)
dat['full_index'] = dat['location_start_id'] + '--' + dat['start_time'].astype(str)

# Find he unique set and count
counts = pd.DataFrame.from_dict(Counter(dat['full_index']),
                                orient='index',
                                columns=['in_use']).reset_index()
counts['area'] = counts['index'].str.extract(r'^(.*?)--')
counts['time'] = counts['index'].str.extract(r'--(.*?)$')
counts.drop(columns=['index'], inplace=True)

# this represents the actual usage
# so write to the db

with psycopg2.connect(dbname=pg_db, user=pg_username,
                      password=pg_password, host=pg_host,
                      port=pg_port) as conn:
    with conn.cursor() as curs:
        conn.executemany("""UPDATE ts SET in_use = %s WHERE (time = %s AND area = %s)""",
                         zip(counts.in_use, counts.time, counts.area))
        conn.commit()



with psycopg2.connect(dbname=pg_db, user=pg_username,
                      password=pg_password, host=pg_host,
                      port=pg_port) as conn:
    ts = pd.read_sql('SELECT * FROM ts', conn)

new_ts = pd.merge(ts, counts, how='left', left_on=['area', 'time'])
