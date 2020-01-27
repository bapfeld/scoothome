import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, accuracy_score, confusion_matrix
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
import configparser, argparse
import os, datetime
import psycopg2

# need to get the data in
def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['postgres'], config['darksky']['key'])

pg, ds_key = import_secrets('/home/bapfeld/scoothome/setup.ini')
conn = psycopg2.connect(database=pg['database'],
                        user=pg['username'],
                        password=pg['password'],
                        port=pg['port'],
                        host=pg['host'])
dat = pd.read_sql_query('SELECT * FROM ts', conn)

weather = pd.read_sql_query('SELECT * from weather', conn)

# aggregate by time
dat = dat.groupby('time').sum().resample('H').sum()

# merge with weather
dat = pd.merge(dat, weather, how='left', on='time')
dat.dropna(inplace=True)

# Create test and train sets
train = dat[dat['time'] < pd.to_datetime('2019/12/01')].copy()
test = dat[dat['time'] > pd.to_datetime('2019/12/01')].copy()

train['heavy_rain'] = pd.cut(train['current_rain'])


X = train.drop(columns=['time', 'district', 'tract', 'n'])
y = train['n']

# Select relevant features

# svc
svc = LinearSVC()
svc.fit(X, y)
svc_pred = svc.predict(X)
svc_mse = mean_squared_error(y, svc_pred)
svc_rmse = np.sqrt(svc_mse)
svc_rmse

# decision tree
tree_clf = DecisionTreeClassifier(max_depth=2)
tree_clf.fit(X, y)
tree_pred = tree_clf.predict(X)
tree_mse = mean_squared_error(y, tree_pred)
tree_rmse = np.sqrt(tree_mse)
tree_rmse

# random forest
rnd_clf = RandomForestClassifier(n_estimators=500, max_leaf_nodes=16, n_jobs= -1)
rnd_clf.fit(X, y)
forest_pred = rnd_clf.predict(X)
forest_rmse = np.sqrt(mean_squared_error(y, forest_pred))
forest_rmse

# linear regression
lin = LinearRegression()
lin.fit(X, y)
lin_pred = lin.predict(X)
lin_mse = mean_squared_error(y, lin_pred)
lin_rmse = np.sqrt(lin_mse)
lin_rmse


# feature selection?
from sklearn.feature_selection import SelectKBest, chi2

best_features = SelectKBest(score_func=chi2, k=5)
fit = best_features.fit(X, y)
df_scores = pd.DataFrame(fit.scores_)
df_columns = pd.DataFrame(X.columns)
feature_scores = pd.concat([df_columns, df_scores], axis=1)
feature_scores.columns = ['Specs', 'Score']
print(feature_scores.nlargest(5, 'Score'))

# linear regression using only the relevant variables
X_small = train[['temp', 'uv', 'wind']]

lin_2 = LinearRegression()
lin_2.fit(X_small, y)
lin_2_pred = lin_2.predict(X_small)
lin_2_mse = mean_squared_error(y, lin_2_pred)
lin_2_rmse = np.sqrt(lin_2_mse)
lin_2_rmse
