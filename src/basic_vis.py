import pandas as pd
import matplotlib.pyplot as plt

dat = pd.read_csv("/home/bapfeld/Downloads/Shared_Micromobility_Vehicle_Trips.csv",
                  dtype={'Census Tract Start': object, 'Census Tract End': object})

# Take a quick look at the data
dat.groupby('Council District (Start)').count()[['Census Tract Start']]

len(pd.unique(dat['Census Tract Start']))

# Distribution of trips by census tract
starts = dat.groupby('Census Tract Start').count()[['ID']]
starts = starts.sort_values("ID")

fig, ax = plt.subplots(1, 1, figsize=(12, 6))
starts.plot(kind='bar', ax=ax)
# plt.show()
plt.savefig("/home/bapfeld/insight/presentation/images/full_hist.jpeg")
plt.close()

start_simple = starts.iloc[-40:]
fig, ax = plt.subplots(1, 1, figsize=(12, 6))
start_simple.plot(kind='bar', ax=ax)
plt.savefig("/home/bapfeld/insight/presentation/images/simple_hist.jpeg")
plt.close()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
starts.plot(kind='bar', ax=ax1)
ax1.set_xlabel("All census tracts")
start_simple.plot(kind='bar', ax=ax2)
ax2.set_xlabel("High frequency census tracts")
fig.suptitle("Distribution of ride start points by census tract")
plt.savefig("/home/bapfeld/insight/presentation/images/hist_joint.jpeg")
plt.close


# Distribution of trips by time for one tract
# Tract 48453001308

tract = dat[dat['Census Tract Start'] == "48453001308"]
tract['date'] = tract['Start Time'].str.extract(r'(\d\d/\d\d/\d\d\d\d)?')
# tract['date'] = pd.to_datetime(tract.date)
tract_days = tract.groupby('date').count()[['ID']]
tract_days_small = tract_days[100:150]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
tract_days.plot(kind='bar', ax=ax1)
ax1.set_xlabel("Full Time Period")
tract_days_small.plot(kind='bar', ax=ax2)
ax2.set_xlabel("8/28/18 to 10/16/18")
fig.suptitle("Distribution of rides over time within one census tract")
plt.savefig("/home/bapfeld/insight/presentation/images/full_hist_time.jpeg")
plt.close()
