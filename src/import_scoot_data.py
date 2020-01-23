import pandas as pd
import configparser, argparse
import os
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

def import_postgres(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return config['postgres']

pg = import_postgres('/home/bapfeld/scoothome/setup.ini')
username = pg['username']
password = pg['password']
port = pg['port']
db_name = pg['database']
host = 'localhost'

# Create a database
engine = create_engine(f'postgresql://{username}:{password}@{host}:{port}/{db_name}')
if not database_exists(engine.url):
    create_database(engine.url)
