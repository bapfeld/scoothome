from flask import Flask
import configparser, os
app = Flask(__name__)

# Define functions
def import_secrets(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)
    return (config['postgres'], config['darksky']['key'], config['mapbox']['public_token'])


from scoothomeflask import scoothome
ini_path = os.path.expanduser('~/scoothome/setup.ini')
pg, ds_key, map_pub_token = import_secrets(ini_path)
