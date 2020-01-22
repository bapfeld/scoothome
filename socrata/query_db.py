import pandas as pd
import configparser, argparse
import os
import psycopg2

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return config['postgres']

def get_series(idx, pg):
    conn = psycopg2.connect(database=pg['database'],
                            user=pg['username'],
                            password=pg['password'],
                            port=pg['port'],
                            host=pg['host'])
    q = f'SELECT * FROM ts WHERE area = {idx}'
    dat = pd.read_sql_query(q, conn)
    return dat

def main(pg):
    pass



if __name__ == "__main__":
    def initialize_params():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--ini_path',
            help="Path to the .ini file containing the app token",
            required=False,
        )
        return parser.parse_args()
    args = initialize_params()
    pg = import_secrets(os.path.expanduser(args.ini_path))
    main(pg)
