from flask import Flask
app = Flask(__name__)

from scoothomeflask import scoothome
# from scoothomeflask.scoothome.fetch_predictions import initialize_params
# args = initialize_params()
# pg, ds_key, map_pub_token = import_secrets(os.path.expanduser(args.ini_path))
