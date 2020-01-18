import pandas as pd
import configparser, argparse
import os
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['socrata']['app_token'], config['postgres'])


# Create a database
engine = create_engine(f'postgresql://{username}:{password}@{host}:{port}/{db_name}')
if not database_exists(engine.url):
    create_database(engine.url)
