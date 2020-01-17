import pandas as pd
from sodapy import Socrata
import configparser

config = configparser.ConfigParser()
config.read('/home/bapfeld/scoothome/socrata/socrata.ini')
app_token = config['socrata']['app_token']

client = Socrata("data.austintexas.gov", app_token)

