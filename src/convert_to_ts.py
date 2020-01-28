import pandas as pd
import numpy as np
import os, argparse, configparser, re, logging, time
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from collections import Counter
from multiprocessing import Process

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
        self.areas = set(list(pd.unique(self.dat['location_start_id'])) +
                         list(pd.unique(self.dat['location_end_id'])))
        self.init_ts_list()
        # self.init_ts_df()
        self.travel_totals = pd.DataFrame()
        self.sql_init = False
        
    def sql_setup(self, pg):
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['localhost']
        self.pg_db = pg['database']
        self.pg_port = pg['port']
        self.engine = create_engine(f'postgresql://{self.pg_username}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}')

    def sql_create(self, replace_ts_table=False):
        if replace_ts_table:
            self.ts.tosql('ts', self.engine, if_exists='replace', chunksize=20000)
        else:
            try:
                self.ts.to_sql('ts', self.engine, if_exists='fail', chunksize=20000)
            except ValueError:
                pass

    def write_to_sql(self):
        ts_out = self.ts[self.ts.n != 0].copy().reset_index()
        with psycopg2.connect(dbname=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              host=self.pg_host,
                              port=self.pg_port) as conn:
            with conn.cursor() as curs:
                curs.executemany("""UPDATE ts SET n = n+%s WHERE (time = %s AND area = %s)""",
                                 zip(ts_out.n, ts_out.time, ts_out.area))
                conn.commit()

    def ts_list_to_txt(self, out_dir, num):
        fp = os.path.expanduser(out_dir) + "/" + num + '.txt'
        with open(fp, 'w') as outfile:
            outfile.writelines(x + '\n' for x in self.ts_list)


    def init_ts_df(self):
        time_stamps = pd.date_range(self.dat.start_time.min(),
                                    self.dat.end_time.max(),
                                    freq="15min")
        self.ts = pd.DataFrame(np.zeros(len(time_stamps) * len(self.areas), dtype=int),
                          index=pd.MultiIndex.from_product([self.areas, time_stamps],
                                                           names=['area', 'time']),
                          columns=['n'])

    def init_ts_list(self):
        self.ts_list = []

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
        # add one vehicle to area for that time
        # self.ts.loc[pd.IndexSlice[tmp.iloc[i, 5], time_span], 'n'] += 1
        new_list = [tmp.iloc[i, 5] + '--' + x for x in time_span]
        self.ts_list.extend(new_list)

    def where_am_i(self, idx):
        tmp = self.dat[self.dat.device_id == idx].copy()
        travel = tmp.groupby('date').sum()
        travel['device_id'] = idx
        self.travel_totals = pd.concat([self.travel_totals, travel])
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


def multi_single_id(idx_list, dat, out_dir):
    for i in idx_list:
        tsm = ts_maker(dat)
        tsm.where_am_i(i)
        tsm.ts_list_to_txt(out_dir, i)

def split_dat(dat):
    id_list = pd.unique(dat['device_id'])
    if len(id_list) > 5000:
        ids = np.array_split(id_list, len(id_list) // 5000)
    else:
        ids = [id_list]
    return [dat[dat.device_id.isin(x)].copy().reset_index(drop=True) for x in ids]

def main(dat_path,
         dat_out,
         vehicle_type,
         report,
         multi,
         multi_out,
         continue_process,
         pg):
    if pg is not None:
        create_db(pg['username'], pg['password'], 'localhost', pg['port'], pg['database'])
    dat = pd.read_csv(os.path.expanduser(dat_path),
                  dtype={'Census Tract Start': object, 'Census Tract End': object})
    dat = clean_df(dat, vehicle_type)

    if not multi:
        tsm = ts_maker(dat)
        tsm.process_devices(report)

        # generate the list of place-times that exist
        places_exist = set(tsm.ts_list)

        # and generate the full list
        tsm.init_ts_df()
        tsm.ts.reset_index(inplace=True)
        tsm.ts['full_index'] = tsm.ts['area'] + '--' + tsm.ts['time'].astype(str)
        full_places = set(tsm.ts['full_index'])

        # and find the difference
        missing_places = full_places - places_exist

        # convert to dataframes
        missing_df = pd.DataFrame.from_dict({k: 0 for k in missing_places},
                                            orient='index',
                                            columns=['n']).reset_index()

        incomplete_df = pd.DataFrame.from_dict(Counter(tsm.ts_list),
                                           orient='index',
                                           columns=['n']).reset_index()

        complete_df = pd.concat([incomplete_df, missing_df])

        complete_df['area'] = complete_df['index'].str.extract(r'^(.*?)--')
        complete_df['time'] = complete_df['index'].str.extract(r'--(.*?)$')

        # Write the result
        complete_df.to_csv(dat_out, columns=['area', 'time', 'n'], index=False)

    else:
        ids = pd.unique(dat['device_id'])
        if continue_process:
            existing_list = [x for x in os.listdir(multi_out) if x.endswith('txt')]
            existing_list = [re.sub('\.txt$', '', x) for x in existing_list]
            ids = list(set(ids) - set(existing_list))
        n_cpu = os.cpu_count() - 1
        id_list = np.array_split(ids, n_cpu)
        processes = []
        for i, idl in enumerate(id_list):
            proc = Process(target=multi_single_id, args=(idl, dat, multi_out))
            processes.append(proc)
            proc.start()
        for proc in processes:
            proc.join()

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
            '--ini_path',
            help="Path to the .ini file containing the app token",
            required=False,
        )
    parser.add_argument(
            '--vehicle_type',
            help="Type of vehicle to use. Options are scooter or scooter. Defaults to scooter",
            default='scooter', 
        )
    parser.add_argument(
        '--report',
        help="Frequency of reporting how many vehicle ids have been processed.",
        required=False,
    )
    parser.add_argument(
        '--multi',
        help="Should the code be run as a multi-threaded process? If so, then multi_out must also be specified.",
        required=False,
        action='store_true'
    )
    parser.add_argument(
        '--multi_out',
        help="Directory to where to store files from multi-threaded processes",
        required=False,
    )
    parser.add_argument(
        '--continue_process',
        help="Should the processor pick up where it left off? Defaults to false.",
        required=False,
        action='store_true'
    )
    return parser.parse_args()


if __name__ == "__main__":
    fmt = "%(asctime)s: %(message)s"
    logging.basicConfig(format=fmt, level=logging.INFO, datefmt="%H:%M:%S")
    args = initialize_params()
    if args.ini_path is not None:
        pg = import_secrets(os.path.expanduser(args.ini_path))
    else:
        pg = None
    main(os.path.expanduser(args.dat_path),
         args.dat_out,
         args.vehicle_type,
         args.report,
         args.multi,
         os.path.expanduser(args.multi_out),
         args.continue_process, 
         pg)
