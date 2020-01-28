import pandas as pd
import numpy as np
import os, argparse, configparser, re, logging, time
import psycopg2
from collections import Counter

def create_db(username, password, host, port, db_name):
    engine = create_engine(f'postgresql://{username}:{password}@{host}:{port}/{db_name}')
    if not database_exists(engine.url):
        create_database(engine.url)

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return config['postgres']

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


class ts_maker():
    """convert data to ts without constantly passing parameters and rewriting things

    """
    def __init__(self, dat):
        self.dat = dat
        self.ts_list = []
        self.ts_inuse = []

    def ts_list_to_txt(self, out_dir, num):
        fp = os.path.expanduser(out_dir) + "/" + num + '.txt'
        with open(fp, 'w') as outfile:
            outfile.writelines(x + '\n' for x in self.ts_list)

    def add_vehicle(self, tmp, i, arbitrary=None):
        if arbitrary is None:
            # p = ((tmp.iloc[i, 3] / 60) // 15) + 1
            time_span = list(map(str, pd.date_range(tmp.iloc[i, 7],
                                                    tmp.iloc[i, 8],
                                                    freq="15min")))
        elif isinstance(arbitrary, int):
            time_span = list(map(str, pd.date_range(tmp.iloc[i, 8],
                                                    periods=arbitrary,
                                                    freq="15min")))
        else:
            time_span = arbitrary
        new_list = [tmp.iloc[i, 5] + '--' + x for x in time_span]
        self.ts_list.extend(new_list)

    def where_am_i(self, idx):
        tmp = self.dat[self.dat.device_id == idx].copy()
        tmp.drop_duplicates(subset=['start_time'], keep='first', inplace=True)
        tmp.reset_index(drop=True, inplace=True)
        # final trip has to be ignored
        for i in range(tmp.shape[0] - 1):
            # Did the trip start and stop in the same area?
            if tmp.iloc[i, 5] == tmp.iloc[i, 6]:
                # trip starts and ends in same area
                # first, take care of the journey itself
                self.add_vehicle(tmp, i)
                
                # What if the vehicle sits idle for a period?
                if tmp.iloc[i, 6] != tmp.iloc[i + 1, 5]:
                    # vehicle changed zones between journeys
                    # does it appear to have been depleted?
                    if travel.loc[tmp.iloc[i, 9]]['duration'] >= 24000:
                        # vehicle appears to be exhausted and is assumed to be useless
                        # nothing added
                        # potential to add a random variable here
                        pass
                    else:
                        # how long between the changes?
                        t = tmp.iloc[i + 1, 7] - tmp.iloc[i, 8]

                        # less than 3 days suggests availability 
                        # very long length suggests vehicle hidden or out of service
                        if (t.total_seconds() > 28800) and (t.total_seconds() < (86400 * 3)):
                            chunks = ((t.total_seconds() - 28800) / 60) // 15
                            # assume 8 hours for recharge and moving
                            self.add_vehicle(tmp, i, int(chunks))
                            # could add more complexity here
                else:
                    # vehicle stayed in same area
                    if travel.loc[tmp.iloc[i, 9]]['duration'] >= 24000:
                        # vehicle appears to be exhausted and is assumed to be useless
                        # nothing added
                        # potential to add a random variable here
                        pass
                    else:
                        # how long between the changes?
                        t = tmp.iloc[i + 1, 7] - tmp.iloc[i, 8]
                        if t.total_seconds() >= 86400:
                            # assume 12 additional hours, then vehicle was charged if more than a day
                            self.add_vehicle(tmp, i, 48) 
                            # could add more complexity here
                        else:
                            # otherwise fill in until the next ride
                            chunks = list(map(str, pd.date_range(tmp.iloc[i, 8],
                                                                 tmp.iloc[i + 1, 7],
                                                                 freq="15min")))
                            self.add_vehicle(tmp, i, chunks[1:-1])
            else:
                # trip ends in different area
                self.add_vehicle(tmp, i)

    def process_devices(self, report=None):
        for n, idx in enumerate(pd.unique(self.dat['device_id'])):
            if report is not None:
                if n % int(report) == 0:
                    print(n)
            self.where_am_i(idx)

def look_back(row):
    pass

def look_ahead(v_id, v_id_next, area, area_next):
    if v_id == v_id_next:
        # same vehicle
        if area == area_next:
            # area is the same
            pass
        else:
            # area is different
            pass
    else:
        pass

def main(dat_path,
         dat_out,
         vehicle_type,
         pg):
    conn = psycopg2.connect(database=pg['database'],
                            user=pg['username'],
                            password=pg['password'],
                            port=pg['port'],
                            host=pg['host'])
    q = f"SELECT * FROM rides WHERE vehicle_type = '{vehicle_type}'"
    dat = pg.read_sql_query(q, conn)

    # minor df cleaning
    dat.drop(columns=['trip_id', 'modified_date', 'month',
                      'hour', 'day_of_week', 'year'], inplace=True)
    dat = dat.apply(lambda x: pd.to_datetime(x) if x.name in ['start_time', 'end_time'] else x)
    dat.sort_values(['device_id', 'council_district_start',
                     'census_tract_start', 'start_time'], inplace=True)

    # generate lead and lag values
    dat_lead = pd.shift(dat, -1)
    dat_lead.columns = map(lambda x: re.sub(r'$', '_lead', x), dat_lead.columns)
    dat_lag = pd.shift(dat, 1)
    dat_lag.columns = map(lambda x: re.sub(r'$', '_lag', x), dat_lag.columns)
    dat = pd.concat([dat, dat_lead, dat_lag], axis=1)

    dat['neg_periods'] = dat.apply(lambda row: look_back(row), axis=1)
    dat['pos_periods'] = dat.apply(lambda row: look_ahead(row['vehicle_id'].values,
                                                          row['vehicle_id_lead'].values,
                                                          row['area'].values,
                                                          row['area_lead'].values),
                                   axis=1)


    # Write the result
    # complete_df.to_csv(dat_out, columns=['area', 'time', 'n'], index=False)

def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dat_path',
        help="Path to the new data to be processed",
        required=True,
    )
    parser.add_argument(
        '--dat_out',
        help="Path to where the data will be saved",
        required=False,
    )
    parser.add_argument(
            '--vehicle_type',
            help="Type of vehicle to use. Options are scooter or scooter. Defaults to scooter",
            default='scooter', 
        )
    parser.add_argument(
        '--ini_path',
        help="Path to the .ini file containing the app token",
        required=False,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = initialize_params()
    config = configparser.ConfigParser()
    config.read(ini_path)
    pg = config['postgres']
    main(os.path.expanduser(args.dat_path),
         args.dat_out,
         args.vehicle_type,
         pg)
