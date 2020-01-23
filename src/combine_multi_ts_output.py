import os, argparse
from collections import Counter
import numpy as np
import pandas as pd

def clean_df(df):
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

    # Sort and reset the index
    df.sort_values(['start_time'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Return the result
    return df


def main(dir_path, dat_path, calculate_missing, out_path):
    event_list = []
    f_list = [x for x in os.listdir(dir_path) if x.endswith('txt')]
    f_list = [os.path.join(dir_path, x) for x in f_list]
    for f in f_list:
        with open(f, 'r') as f_in:
            event_list.extend(f_in.readlines())

    # Calculate the counts based on the full list
    counts = pd.DataFrame.from_dict(Counter(event_list),
                                        orient='index',
                                        columns=['n']).reset_index()
    counts['area'] = counts['index'].str.extract(r'^(.*?)--')
    counts['time'] = counts['index'].str.extract(r'--(.*?)$')

    # If we want to fill in missing place-times with 0s
    if calculate_missing:
        full_dat = pd.read_csv(os.path.expanduser(dat_path),
                               dtype={'Census Tract Start': object,
                                      'Census Tract End': object})
        full_dat = clean_df(dat)
        time_stamps = pd.date_range(full.dat.start_time.min(),
                                    full.dat.end_time.max(),
                                    freq="15min")
        full_areas = set(list(pd.unique(full_dat['location_start_id'])) +
                         list(pd.unique(full_dat['location_end_id'])))
        full_ts = pd.DataFrame(np.zeros(len(time_stamps) * len(full_areas),
                                        dtype=int),
                               index=pd.MultiIndex.from_product([full_areas, time_stamps],
                                                                names=['area', 'time']),
                               columns=['n'])
        full_ts['full_index'] = full_ts['area'] + '--' + full_ts['time'].astype(str)
        places_exist = set(event_list)
        full_places = set(tsm.ts['full_index'])
        missing_places = full_places - places_exist
        missing_df = pd.DataFrame.from_dict({k: 0 for k in missing_places},
                                            orient='index',
                                            columns=['n']).reset_index()
        counts = pd.concat([counts, missing_df])

    # Separate out the identifying variables again
    counts['district'] = counts['area'].str.extract(r'(^.*?)-').astype(float).astype(int)
    counts['tract'] = counts['area'].str.extract(r'-(.*?$)').astype(int)
    
    # write out again
    counts.to_csv(out_path,
                  columns=['area', 'district', 'tract', 'time', 'n'],
                  index=False)    

def initialize_params():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--dir_path',
            help="Path to directory storing all the files",
            required=True,
        )
        parser.add_argument(
            '--dat_path',
            help="Path to the corresponding data file to figure out missing values",
            required=False,
        )
        parser.add_argument(
            '--calculate_missing',
            help="Should the code attempt to fill in missing values with 0? Defaults to false.",
            required=False,
            action="store_true"
        )
        parser.add_argument(
            '--out_path',
            help="Path to where to save final file",
            required=True,
        )
        return parser.parse_args()
    
if __name__ == "__main__":
    args = initialize_params()
    main(os.path.expanduser(args.dir_path),
         os.path.expanduser(args.dat_path),
         args.calculate_missing,
         os.path.expanduser(args.out_path))
