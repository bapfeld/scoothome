import pandas as pd
from sodapy import Socrata
import configparser, argparse
import os
import psycopg2

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['socrata']['app_token'], config['postgres'])
    

def get_max_date():
    pass

def write_to_db(database, user, password, port):
    pass

def fetch_new_data(client, resource, start_date):
    results = client.get(resource, where=f'Start Time > {latest_start_time}')
    # results_df = pd.DataFrame.from_records(results)
    return results
    
# '/home/bapfeld/scoothome/socrata/socrata.ini'
# micromobility data: "7d8e-dm7r"

def main():
    def initialize_params():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--ini_path',
            help="Path to the .ini file containing the app token",
            required=False,
        )
        return parser.parse_args()
    args = initialize_params()
    app_token, pg = import_secrets(os.path.expanduser(args.ini_path))

    # Establish a client to query the database
    client = Socrata("data.austintexas.gov", app_token)

    # Get latest dates for the different databases

    # Fetch new data

    # Write new data back to the database


if __name__ == "__main__":
    main()
