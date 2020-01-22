import pandas as pd
import configparser, argparse
import os
import psycopg2

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return config['postgres']

class tsModel():
    """Class to query required underlying data, estimate a model, and forecast.

    """
    def __init__(self, pg):
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['localhost']
        self.pg_db = pg['database']
        self.pg_port = pg['port']
        
    def get_area_series(self, idx):
        conn = psycopg2.connect(database=self.pg_db,
                                user=self.pg_username,
                                password=self.pg_password,
                                port=self.pg_port,
                                host=self.pg_host)
        q = f'SELECT * FROM ts WHERE area = {idx}'
        self.area_series = pd.read_sql_query(q, conn)

def main(pg):
    m = tsModel(pg)


def initialize_params():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--ini_path',
            help="Path to the .ini file containing the app token",
            required=False,
        )
        return parser.parse_args()

if __name__ == "__main__":
    args = initialize_params()
    pg = import_secrets(os.path.expanduser(args.ini_path))
    main(pg)
