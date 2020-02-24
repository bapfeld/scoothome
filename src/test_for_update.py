import pandas as pd
from sodapy import Socrata
import psycopg2, os, configparser, argparse
import datetime, sys, time
import boto3
from botocore.exceptions import ClientError

# Get socrata and postgres secrts
def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['socrata']['app_token'],
            config['postgres'],
            config['ec2'])
            
# Determine the maximum date in the database
def get_max_date(pg):
    """Fetch the maximum date in the database"""
    with psycopg2.connect(database=pg['database'],
                          user=pg['username'],
                          password=pg['password'],
                          port=pg['port'],
                          host=pg['host']) as conn:
        res = pd.read_sql_query('SELECT MAX(start_time) from rides', conn)
    current_max_date = res.iloc[0, 0]
    return current_max_date

# Query socrata to see latest data
def check_for_new_data(app_token):
    """Test the Austin API to see if there is new data"""
    client = Socrata("data.austintexas.gov", app_token)
    austin_res = client.get_metadata(dataset_identifier="7d8e-dm7r")
    austin_max = datetime.datetime.fromtimestamp(austin_res['rowsUpdatedAt'])
    austin_max_pretty = austin_max.strftime('%Y-%m-%d %H:%M')
    return (austin_max, austin_max_pretty)

# Check to see the difference and determine action
def calculate_action(austin_max, current_max_date):
    """Compare maximum dates to decide if action should be taken"""
    t_diff = (austin_max - current_max_date).days
    if t_diff > 1:
        if t_diff > 6:
            action = 'update'
        else:
            action = 'new data, no update'
    else:
        action = 'none'
    return action

# Write the results to the update log file
def log_decision(action, current_max_date, austin_max_pretty, logfile_path):
    """Log the decision to file"""
    logfile = os.path.expanduser(logfile_path)
    log_note = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    log_note += f'\nDB MAX: {current_max_date} --- AUSTIN MAX: {austin_max_pretty}\n'
    log_note += f'ACTION: {action}\n\n'
    with open(logfile, 'a') as outfile:
        outfile.writelines(log_note)

# If an update is required, start the updater instance and get the code running
def run_updater(ec2_config):
    """Thin wrapper to start the instance"""
    session = boto3.Session(profile_name='brendan-IAM')
    ec2 = session.client('ec2')
    updater_id = ec2_config['updater_id']
    # Start the instance
    ec2.start_instances(InstanceIds=[updater_id], DryRun=False)

def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the ini file",
        required=True,
        default='~/scoothome/setup.ini'
    )
    parser.add_argument(
        '--logfile_path',
        help="Path to the location of the logfile",
        required=True,
        default='~/update_check.log'
    )
    return parser.parse_args()



def main():
    # Initialize
    args = initialize_params()
    ini_path = os.path.expanduser(args.ini_path)
    app_token, pg, ec2_config = import_secrets(ini_path)
    # Fetch necessary info
    current_max_date = get_max_date(pg)
    austin_max, austin_max_pretty = check_for_new_data(app_token)
    action = calculate_action(austin_max, current_max_date)
    # Make decision, take action
    log_decision(action, current_max_date, austin_max_pretty, args.logfile_path)
    if action == 'update':
        run_updater(ec2_config)

if __name__ == "__main__":
    main()
