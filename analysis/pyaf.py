import pandas as pd
import re
import pyaf.HierarchicalForecastEngine as hautof

# need to get the data in
dat = pd.read_csv("/home/bapfeld/scoothome/data/jan_19_ts.csv")

dat['time'] = pd.to_datetime(dat['time'])

areas = pd.unique(dat['area'])
districts = [re.sub(r'-.*$', '', x) for x in areas]
tracts = [re.sub(r'^.*-', '', x) for x in areas]
a_list = ['austin'] * len(areas)

lHierarchy = {'Levels': ['area', 'tract', 'district', 'austin'],
              'Data': pd.DataFrame({'area': areas,
                                    'tract': tracts,
                                    'district': districts,
                                    'austin': a_list}),
              'Type': 'Hierarchical'}

lEngine = hautof.cHierarchicalForecastEngine()

lSignalHierarchy = lEngine.plot_Hierarchy(dat, "time", "n", 1, lHierarchy, None)
lSignalHierarchy.mStructure

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
