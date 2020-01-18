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

# Make a new dataframe

time_stamps = pd.date_range(test.start_time.min(),
                            test.end_time.max(),
                            freq="15min")
ts = pd.DataFrame(np.zeros(len(time_stamps) * len(areas), dtype=int),
                  index=pd.MultiIndex.from_product([areas, time_stamps]),
                  columns=['n'])
