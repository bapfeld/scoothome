import pandas as pd
import numpy as np
from fbprophet import Prophet
import psycopg2
from matplotlib.backends.backend_pdf import PdfPages
from darksky.api import DarkSky
from darksky.types import languages, units, weather
import sys
sys.path.append('/home/bapfeld/scoothome')
from app.scoothome.model import tsModel, import_secrets
import configparser


def main():
    test_area = '9.0-48453001100'

if __name__ == "__main__":
    main()

