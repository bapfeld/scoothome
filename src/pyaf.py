import pandas as pd
import re
import psycopg2
import pyaf.HierarchicalForecastEngine as hautof

# with open('/home/bapfeld/scoothome/data/area_id_list.txt', 'r') as f:
#     area_list = f.readlines()
# area_list = [x.strip() for x in area_list]

# pg, ds_key = import_secrets('/home/bapfeld/scoothome/setup.ini')

# need to get the data in
# conn = psycopg2.connect(database=pg['database'],
#                         user=pg['username'],
#                         password=pg['password'],
#                         port=pg['port'],
#                         host=pg['host'])
# dat = pd.read_sql_query('SELECT * FROM ts', conn)

# with open('/home/bapfeld/scoothome/data/area_id_list.txt', 'r') as f:
#     area_list = f.readlines()
# area_list = [x.strip() for x in area_list]

# tracts = pd.unique(dat['tract'])
# districts = pd.unique(dat['district'])
dat = pd.read_csv("/home/bapfeld/scoothome/data/jan_19_ts.csv")

dat['time'] = pd.to_datetime(dat['time'])

areas = pd.unique(dat['area'])
districts = [re.sub(r'-.*$', '', x) for x in areas]
tracts = [re.sub(r'^.*-', '', x) for x in areas]
area_list = ['austin'] * len(areas)

lHierarchy = {'Levels': ['area', 'tract', 'district', 'austin'],
              'Data': pd.DataFrame({'area': areas,
                                    'tract': tracts,
                                    'district': districts,
                                    'austin': area_list}),
              'Type': 'Hierarchical'}

# Need to complete the time series...
dat = dat.set_index('time').groupby(['area']).resample('15T').mean().fillna(0)
dat.reset_index(inplace=True)

lEngine = hautof.cHierarchicalForecastEngine()

lSignalHierarchy = lEngine.plot_Hierarchy(dat, "time", "n", 1, lHierarchy, None)
# lSignalHierarchy.mStructure

# drop final day for predictions
train_df = dat[dat['time'] < pd.to_datetime('2019-01-30')].copy().pivot(index='time', columns='area', values='n').reset_index()

lSignalHierarchy = lEngine.train(train_df, 'time', 'n', 1, lHierarchy, None)

# And now results time
lInfo = lEngine.to_json()
perfs = [];
for model in sorted(lInfo['Models'].keys()):
    lPerf = lInfo['Models'][model]['Model_Performance']
    perfs.append([model , lPerf['RMSE'] , lPerf['MAPE']])
df_perf = pd.DataFrame(perfs , columns=['Model' , 'RMSE' , 'MAPE']);
df_perf = df_perf.sort_values(by = ['MAPE'])
print(df_perf)

lEngine.mSignalHierarchy.plot()
