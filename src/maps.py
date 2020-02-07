import geopandas
import matplotlib.pyplot as plt
import contextily as ctx

def add_basemap(ax, zoom, url='http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'):
    xmin, xmax, ymin, ymax = ax.axis()
    basemap, extent = ctx.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, url=url)
    ax.imshow(basemap, extent=extent, interpolation='bilinear')
    # restore original x/y limits
    ax.axis((xmin, xmax, ymin, ymax))

tracts = geopandas.read_file('/home/bapfeld/scoothome/data/census_tracts')
tracts = tracts[tracts['COUNTYFP'] == '453']
tracts = tracts.to_crs({'init': 'epsg:4326'})

districts = geopandas.read_file('/home/bapfeld/scoothome/data/council_districts')

austin = geopandas.sjoin(tracts, districts, op='intersects', how='inner')
austin = austin.to_crs(epsg=3857)

ax = austin.plot(edgecolor='black', alpha=0.5, figsize=(10, 10))
add_basemap(ax, zoom=11, url=ctx.sources.ST_TONER_LITE) # 12 looks a little better but takes a long time
ax.set_axis_off()
plt.show()
plt.close()

sm_austin = austin[austin['geometry'].area < 12.0e+06]
sm_austin['centroid_real'] = sm_austin['geometry'].centroid
lats = list(map(lambda val: val.x, sm_austin.centroid_real))
sm_austin['c_lat'] = lats
sm_austin = sm_austin[sm_austin['c_lat'] < -1.087e7]

ax = sm_austin.plot(edgecolor='black', alpha=0.5, figsize=(8, 12))
add_basemap(ax, zoom=12, url=ctx.sources.ST_WATERCOLOR)
ax.set_axis_off()
plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
            hspace = 0, wspace = 0)
plt.margins(0,0)
#plt.show()
#plt.close()

plt.savefig('/home/bapfeld/scoothome/figures/areas_map.png')
plt.close()
