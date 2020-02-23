import pandas as pd
from sodapy import Socrata
import psycopg2, os, configparser
import datetime, sys
import boto3
from botocore.exceptions import ClientError

# Get socrata and postgres secrts
ini_path = os.path.expanduser('~/scoothome/setup.ini')
def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['socrata']['app_token'],
            config['postgres'])
app_token, pg = import_secrets(ini_path)
            
# Determine the maximum date in the database
with psycopg2.connect(database=pg['database'],
                      user=pg['username'],
                      password=pg['password'],
                      port=pg['port'],
                      host=pg['host']) as conn:
    res = pd.read_sql_query('SELECT MAX(start_time) from rides', conn)
current_max_date = res.iloc[0, 0]

# Query socrata to see latest data
client = Socrata("data.austintexas.gov", app_token)
austin_res = client.get_metadata(dataset_identifier="7d8e-dm7r")
austin_max = datetime.datetime.fromtimestamp(austin_res['rowsUpdatedAt'])
austin_max_pretty = austin_max.strftime('%Y-%m-%d %H:%M')

# Check to see the difference and determine action
t_diff = (austin_max - current_max_date).days
if t_diff > 1:
    if t_diff > 6:
        action = 'update'
    else:
        action = 'new data, no update'
else:
    action = 'none'

# Write the results to the update log file
logfile = os.path.expanduser('~/update_check.log')
log_note = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
log_note += f'\nDB MAX: {current_max_date} --- AUSTIN MAX: {austin_max_pretty}\n'
log_note += f'ACTION: {action}\n\n'
with open(logfile, 'a') as outfile:
    outfile.writelines(log_note)

# If an update is required, start the updater instance and get the code running
ec2 = boto3.client('ec2')
response = ec2.describe_instances()
