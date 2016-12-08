# from shapely.wkt import loads
# tester = Point(11.00287, 48.26659)
#
# regions = pd.read_csv('geometries/polygons_de21.csv', index_col='gid')
# for n in range(21):
#     poly = loads(regions.geom[n])
#     if tester.within(poly):
#         print(regions.index[n])
# import pandas as pd
#
# my = pd.read_hdf('/home/uwe/.oemof4/Germany_21_Regions.hf5', 'wind_pwr')
#
# store = pd.HDFStore("/home/uwe/.oemof4/Germany_21_Regions.hf5")
# print(my.mean())
# print(store.keys())
# store.close()
# from shapely.wkt import loads as wkt_loads
# import datetime
import pandas as pd
# import geopandas as gpd
import oemof.db as db
import oemof.db.coastdat as coastdat
from shapely.wkt import loads
# from matplotlib import pyplot as plt
# from shapely.geometry import Point

conn = db.connection()
polygon = loads(pd.read_csv('geometries/germany.csv', index_col='gid',
                            squeeze=True)[0])

for year in [1998, 2003, 2007, 2010, 2011, 2012, 2013, 2014]:
    weather_sets = coastdat.get_weather(conn, polygon, year)
    store = pd.HDFStore('coastDat2_de_{0}.h5'.format(str(year)))
    for weather_set in weather_sets:
        print(weather_set.name)
        store['A' + str(weather_set.name)] = weather_set.data
    store.close()
exit(0)

# #
# # import subprocess
# #
# # subprocess.call(["ogr2ogr", "-a_srs", "WGS84", "-f", "ESRI Shapefile",
# #                  "output.shp", "input.csv", "-dialect", "sqlite",
# #                  "-sql", "SELECT *, GeomFromText(geom) FROM input"])
#
# # sql = "SELECT * FROM deutschland.vg2500_bld"
# # bld = gpd.GeoDataFrame.from_postgis(sql, conn, crs='epsg:4326', index_col='gid')
#
# sql = "SELECT * FROM coastdat.de_grid"
#
# coastdat_grid_de = gpd.GeoDataFrame.from_postgis(sql, conn, crs='epsg:4326',

my = pd.read_hdf('data2/renewable_power_plants_DE.edited.hdf', 'data')
print(my.groupby(['region', 'coastdat_id', 'energy_source_level_2']).sum())
