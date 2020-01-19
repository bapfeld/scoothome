import pandas as pd
import numpy as np

dat = pd.read_csv("/home/bapfeld/scoothome/data/micro.csv",
                  dtype={'Census Tract Start': object, 'Census Tract End': object})

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
    return df

dat = clean_df(dat)

# Smaller sample to make life easier:
test = dat[(dat.vehicle_type == "scooter") & (dat.end_time <= pd.Timestamp("20190430T235959"))]

test.reset_index(drop=True, inplace=True)
test.sort_values(['start_time'], inplace=True)
test.reset_index(drop=True, inplace=True)


class ts_maker():
    """convert data to ts without constantly passing parameters and rewriting things

    """
    def __init__(self, dat):
        self.dat = dat
        self.areas = set(list(pd.unique(self.dat['location_start_id'])) +
                         list(pd.unique(self.dat['location_end_id'])))
        self.init_ts_df()
        self.travel_totals = pd.DataFrame()

    def init_ts_df(self):
        time_stamps = pd.date_range(self.dat.start_time.min(),
                                    self.dat.end_time.max(),
                                    freq="15min")
        self.ts = pd.DataFrame(np.zeros(len(time_stamps) * len(self.areas), dtype=int),
                          index=pd.MultiIndex.from_product([self.areas, time_stamps],
                                                           names=['area', 'time']),
                          columns=['n'])

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
        self.ts.loc[pd.IndexSlice[tmp.iloc[i, 5], time_span], 'n'] += 1

    def where_am_i(self, idx):
        tmp = self.dat[self.dat.device_id == idx]
        tmp.reset_index(drop=True, inplace=True)
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
                        if (t.total_seconds() > 43200) and (t.total_seconds() < (86400 * 3)):
                            chunks = ((t.total_seconds() - 43200) / 60) // 15
                            # assume 12 hours for recharge and moving
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
        



        

ts_test = ts_maker(foo)
ts_test.where_am_i("df2fb7a8-00ab-40ad-83d8-bc4a728e46db")
ts_test.ts.describe()

ts_test_2 = ts_maker(test)
for j, idx in enumerate(pd.unique(test['device_id'])):
    if j % 100 == 0:
        print(j)
    ts_test_2.where_am_i(idx)

ts_test_2.ts.describe()
