import pandas as pd
import configparser, os, datetime, psycopg2

class tsResults():
    """Class to query postgres database and return predictions

    """
    def __init__(self, pg, area, t):
        self.pg = pg
        self.area = area
        self.t = t
        
        
