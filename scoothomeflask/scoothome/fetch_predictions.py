import pandas as pd
import configparser, os, datetime, psycopg2

def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the .ini file containing the app token",
        required=False,
    )
    return parser.parse_args()

class tsResults():
    """Class to query postgres database and return predictions

    """
    def __init__(self, pg, area, t):
        self.pg = pg
        self.area = area
        self.t = t
        self.pg_username = pg['username']
        self.pg_password = pg['password']
        self.pg_host = pg['host']
        self.pg_db = pg['database']
        self.pg_port = pg['port']

    def fetch_scooters(self, var):
        q = f"""SELECT ds, yhat, yhat_lower, yhat_upper FROM predictions
                WHERE area = '{self.area}'
                AND ds >= '{self.t}'
                AND var = '{var}'"""
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            preds = pd.read_sql(q, conn)
            if preds.shape[0] > 0:
                preds = preds.groupby('ds').mean()
            return preds

    def fetch_bikes(self, var):
        q = f"""SELECT ds, yhat, yhat_lower, yhat_upper FROM bike_predictions
                WHERE area = '{self.area}'
                AND ds >= '{self.t}'
                AND var = '{var}'"""
        with psycopg2.connect(database=self.pg_db,
                              user=self.pg_username,
                              password=self.pg_password,
                              port=self.pg_port,
                              host=self.pg_host) as conn:
            preds = pd.read_sql(q, conn)
            preds.groupby('ds').mean()
            return preds
