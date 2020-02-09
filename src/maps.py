#!/usr/bin/env python

import geopandas
import matplotlib.pyplot as plt
import contextily as ctx
import pandas as pd
import numpy as np
import configparser
import psycopg2

def add_basemap(ax, zoom, url='http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'):
    """
    Function to add an underlay basemap to geopandas plot. 

    Necessary if version of contextily does not contain function.
    """
    xmin, xmax, ymin, ymax = ax.axis()
    basemap, extent = ctx.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, url=url)
    ax.imshow(basemap, extent=extent, interpolation='bilinear')
    # restore original x/y limits
    ax.axis((xmin, xmax, ymin, ymax))

# Import postgres data
config = configparser.ConfigParser()
config.read('/home/bapfeld/scoothome/setup.ini')
pg = config['postgres']

# Query postgres db for summary of number of trips
with psycopg2.connect(database=pg['database'],
                              user=pg['username'],
                              password=pg['password'],
                              port=pg['port'],
                              host=pg['host']) as conn:
    query = 'SELECT area, COUNT(area) FROM ts WHERE N > 0 GROUP BY area'
    dat = pd.read_sql(query, conn)

# Create a logged version of the variable
dat['log_count'] = np.log(dat['count'])

# Import the census and council district polygons
tracts = geopandas.read_file('/home/bapfeld/scoothome/data/census_tracts')
tracts = tracts[tracts['COUNTYFP'] == '453']
tracts = tracts.to_crs({'init': 'epsg:4326'})

districts = geopandas.read_file('/home/bapfeld/scoothome/data/council_districts')

austin = geopandas.sjoin(tracts, districts, op='intersects', how='inner')
austin = austin.to_crs(epsg=3857)

# Eliminate areas at the periphery
sm_austin = austin[austin['geometry'].area < 12.0e+06].copy().reset_index(drop=True)
sm_austin['centroid_real'] = sm_austin['geometry'].centroid
lats = list(map(lambda val: val.x, sm_austin.centroid_real))
sm_austin['c_lat'] = lats
sm_austin = sm_austin[sm_austin['c_lat'] < -1.087e7]

sm_austin['area'] = (sm_austin['council_di'].astype(str) + '-' + sm_austin['STATEFP'].astype(str) +
                     sm_austin['COUNTYFP'].astype(str) + sm_austin['TRACTCE'].astype(str))

sm_austin = sm_austin.merge(dat, on='area')

# Building up some layers
# Empty map of austin
ax = sm_austin.plot(edgecolor='black', alpha=0.0, figsize=(8, 12))
add_basemap(ax, zoom=12, url=ctx.sources.ST_WATERCOLOR)
ax.set_axis_off()
plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
            hspace = 0, wspace = 0)
plt.margins(0,0)
plt.savefig('/home/bapfeld/scoothome/figures/austin_base_map.png')
plt.close()

# Map with outlines of areas
ax = sm_austin.plot(edgecolor='black', facecolor='none', figsize=(8, 12))
add_basemap(ax, zoom=12, url=ctx.sources.ST_WATERCOLOR)
ax.set_axis_off()
plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
            hspace = 0, wspace = 0)
plt.margins(0,0)
plt.savefig('/home/bapfeld/scoothome/figures/austin_areas_map.png')
plt.close()

# Map with areas colored by frequency of trips
fig, ax = plt.subplots(1, 1, figsize=(8, 12))
sm_austin.plot(edgecolor='black', column='log_count', ax=ax)
add_basemap(ax, zoom=12, url=ctx.sources.ST_WATERCOLOR)
ax.set_axis_off()
plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
            hspace = 0, wspace = 0)
plt.margins(0,0)
plt.savefig('/home/bapfeld/scoothome/figures/austin_starts_map.png')
plt.close()
