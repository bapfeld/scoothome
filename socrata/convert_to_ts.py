import pandas as pd
import numpy as np

dat = pd.read_csv("/home/bapfeld/scoothome/data/micro.csv",
                  dtype={'Census Tract Start': object, 'Census Tract End': object})

list(dat)
dat.describe()
dat.dtypes
dat.shape

pd.unique(dat['Vehicle Type'])

# Need to drop observations with essential missing data
dat.dropna(inplace=True)

# And drop observations where the start/stop is out of bounds
dat = dat[dat['Census Tract Start'] != 'OUT_OF_BOUNDS']
dat = dat[dat['Census Tract End'] != 'OUT_OF_BOUNDS']

# Want to create a new variable to uniquely identify areas
dat['location_start_id'] = dat['Council District (Start)'].astype(str) + '-' + dat['Census Tract Start']
dat['location_end_id'] = dat['Council District (End)'].astype(str) + '-' + dat['Census Tract End']

# Get all unique area identifiers
areas = set(list(pd.unique(dat['location_start_id'])) +
            list(pd.unique(dat['location_end_id'])))

# Convert time objects
dat['start_time'] = pd.to_datetime(dat['Start Time'], format="%m/%d/%Y %I:%M:%S %p")
dat['end_time'] = pd.to_datetime(dat['End Time'], format="%m/%d/%Y %I:%M:%S %p")
dat['date'] = dat['Start Time'].str.extract(r'(\d\d/\d\d/\d\d\d\d)?')

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
dat.drop(drop_cols, axis=1, inplace=True)
dat.rename(columns={'ID': 'trip_id',
                    'Device ID': 'device_id',
                    'Vehicle Type': 'vehicle_type',
                    'Trip Duration': 'duration',
                    'Trip Distance': 'distance'},
           inplace=True)


# Smaller sample to make life easier:
test = dat[(dat.vehicle_type == "scooter") & (dat.end_time <= pd.Timestamp("20190430T235959"))]

test.reset_index(drop=True, inplace=True)
test.sort_values(['start_time'], inplace=True)
test.reset_index(drop=True, inplace=True)

# Make a new dataframe

time_stamps = pd.date_range(test.start_time.min(),
                            test.end_time.max(),
                            freq="15min")
ts = pd.DataFrame(np.zeros(len(time_stamps) * len(areas), dtype=int),
                  index=pd.MultiIndex.from_product([areas, time_stamps],
                                                   names=['area', 'time']),
                  columns=['n'])

def where_am_i(df, ts, idx):
    tmp = df[df.device_id == idx]
    tmp.reset_index(drop=True, inplace=True)
    travel = tmp.groupby('date').sum()
    tmp.drop_duplicates(subset=['start_time'], keep='first', inplace=True)
    for i in range(tmp.shape[0] - 2):
        # final trip has to be dropped
        # need to figure out if subsequent trip is in same area
        # if it is, then logically can it be there continuously
        # if not, then how much longer did it stay there
        if tmp.iloc[i, 5] == tmp.iloc[i, 6]:
            # trip starts and ends in same area
            pass
        else:
            # trip ends in different area
            # calculate length of trip
            p = ((tmp.iloc[i, 3] / 60) // 15) + 1
            time_span = list(map(str, pd.date_range(tmp.iloc[i, 7],
                                                    periods=int(p),
                                                    freq="15min")))
            # add one vehicle to area for that time
            ts.loc[pd.IndexSlice[tmp.iloc[i, 5], time_span], :'n'] += 1


ts.loc[pd.IndexSlice[foo.iloc[0, 5], ['2019-04-03 08:30:00', '2019-04-03 08:45:00']], :]
