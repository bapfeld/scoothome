import pandas as pd
import os, argparse, configparser, re

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
    
    df.rename(columns={'ID': 'trip_id',
                       'Device ID': 'device_id',
                       'Vehicle Type': 'vehicle_type',
                       'Trip Duration': 'duration',
                       'Trip Distance': 'distance',
                       'Modified Date': 'modified_date',
                       'Month': 'month',
                       'Hour': 'hour',
                       'Day of Week': 'day_of_week',
                       'Council District (Start)': 'council_district_start',
                       'Council District (End)': 'council_district_end',
                       'Year': 'year',
                       'Census Tract Start': 'census_tract_start',
                       'Census Tract End': 'census_tract_end'},
               inplace=True)

dat = pd.read_csv('/home/bapfeld/scoothome/data/Shared_Micromobility_Vehicle_Trips.csv',
                  dtype={'Census Tract Start': object, 'Census Tract End': object})

dat = clean_df(dat)

cols = ["trip_id", "device_id", "vehicle_type", "duration", "distance", "start_time", "end_time", "modified_date", "month", "hour", "day_of_week", "council_district_start", "council_district_end", "year", "census_tract_start", "census_tract_end"]
dat.to_csv('/home/bapfeld/scoothome/data/full_orig.csv', header=True, index=False,
           columns=cols)
