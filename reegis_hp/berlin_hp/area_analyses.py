# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import logging
import time
import os
import pandas as pd
import geoplot
import oemof.db as db
import numpy as np
from oemof.tools import logger
plt.style.use('ggplot')


def fetch_geometries(**kwargs):
    """Reads the geometry and the id of all given tables and writes it to
     the 'geom'-key of each branch of the data tree.
    """
    sql_str = '''
        SELECT {id_col}, ST_AsText(
            ST_SIMPLIFY({geo_col},{simp_tolerance})) geom
        FROM {schema}.{table}
        WHERE "{where_col}" {where_cond}
        ORDER BY {id_col} DESC;'''

    db_string = sql_str.format(**kwargs)
    results = db.connection().execute(db_string)
    cols = results.keys()
    return pd.DataFrame(results.fetchall(), columns=cols)


logger.define_logging()
# conn = db.connection()
start = time.time()

plr_def = {
        'table': 'planungsraum',
        'geo_col': 'geom',
        'id_col': 'schluessel',
        'schema': 'berlin',
        'facecolor': 'red',
        'simp_tolerance': '0',
        'where_col': 'gid',
        'where_cond': '> 0',
        'linewidth': -0.1,
        'alpha': 0.5,
        'cmapname': 'seismic',
        'bbox': (13.1, 13.76, 52.3, 52.7),
        'color': 'red'
        }
planungsraum = fetch_geometries(**plr_def)
planungsraum['geom'] = geoplot.postgis2shapely(planungsraum.geom)

basic_path = '/home/uwe/chiba/RLI/data'
logging.info("Datapath: {0}:".format(basic_path))

# Read tables from csv
df = pd.read_hdf(os.path.join(basic_path, 'eQuarter_0-73_berlin_newage.hdf'),
                 'oeq')
# df.to_csv(os.path.join(basic_path, 'eQuarter_0-73_berlin_newage.csv'))
df['spatial_int'] = df.spatial_na.apply(int)
bloecke = pd.read_hdf(os.path.join(basic_path, 'bloecke.hdf'), 'block')
stadtnutzung = pd.read_hdf(
    os.path.join(basic_path, 'stadtnutzung_erweitert.hdf'), 'stadtnutzung')

# 1100 - Gemischt genutztes Gebäude mit Wohnen
# 1110 - Wohngebäude mit Gemeinbedarf
# 1120 - Wohngebäude mit Handel und Dienstleistungen
# 1130 - Wohngebäude mit Gewerbe und Industrie
# 1220 - Land- und forstwirtschaftliches Wohn- und Betriebsgebäude
# 2310 - Gebäude für Gewerbe und Industrie mit Wohnen
# 3100 - Gebäude für öffentliche Zwecke mit Wohnen

# typelist = {
#     1000: 1,
#     1010: 1,
#     1020: 1,
#     1024: 1,
#     1100: 0.5,
#     1110: 0.5,
#     1120: 0.5,
#     1130: 0.5,
#     1220: 0.5,
#     2310: 0.45,
#     3100: 0.45}
#
# # Filter by building_types to get only (partly) residential buildings
# query_str = ""
# for typ in typelist.keys():
#     query_str += "building_function == {0} or ".format(typ)
# buildings = df.query(query_str[:-4])
#
# Add schluessel_planungsraum to every building by merging the block table
buildings = df.merge(
    bloecke, right_on='schluessel', left_on='spatial_int')
#
# for typ, value in typelist.items():
#     if value < 1:
#         buildings.loc[buildings.building_function == typ, 'living_area'] = (
#             buildings.living_area * 0.496)
print(len(buildings))
buildings.to_hdf(os.path.join(basic_path, 'buildings.hdf'), 'oeq')

# Sum up the area within every planungsraum (buildings)
area_plr_buildings = pd.DataFrame(
    buildings.groupby('schluessel_planungsraum')['living_area'].sum())
area_plr_buildings.rename(columns={'living_area': 'area_alkis'}, inplace=True)

# Calculate the living area by from population and specific living area
stadtnutzung['area'] = (stadtnutzung.ew * stadtnutzung.wohnflaeche_pro_ew)

# Sum up the area within every planungsraum (stadtnutzung)
area_plr_stadtnutzung = pd.DataFrame(stadtnutzung.groupby(
    'schluessel_planungsraum')['area'].sum())
area_plr_stadtnutzung.rename(columns={'area': 'area_stadtnutz'}, inplace=True)

area_plr = pd.merge(area_plr_buildings, area_plr_stadtnutzung,
                    right_index=True, left_index=True)

# Convert key (schluessel) from string to float
planungsraum['key'] = planungsraum.schluessel.astype(float)

# Merge the spatial column and the area columns
planungsraum = planungsraum.merge(area_plr, left_on='key',
                                  right_index=True)

# Create columns to calculate the difference between both models
planungsraum['diff'] = - planungsraum.area_stadtnutz + planungsraum.area_alkis


sigma = np.std(planungsraum['diff'])
mu = planungsraum['diff'].mean()

# the histogram of the data
n, bins, patches = plt.hist(planungsraum['diff'], 50, facecolor='green',
                            alpha=0.75, normed=1)
print(bins)
# add a 'best fit' line
y = mlab.normpdf(bins, mu, sigma)
l = plt.plot(bins, y, 'r--', linewidth=1)

plt.xlabel('Smarts')
plt.ylabel('Probability')
plt.title("Histogram: $\mu$={0}, $\sigma$={1}m²".format(int(mu), int(sigma)))
plt.grid(True)

plt.show()
# ax = planungsraum['diff'].plot.hist(bins, ax=plt.subplot(111))
y = mlab.normpdf(bins, mu, sigma)
plt.plot(y, 'r--', linewidth=3)
plt.title(r'$\mathrm{Histogram\ of\ IQ:}\ \mu=100,\ \sigma=15$')
plt.show()

# data = (planungsraum['diff'] - 0.5) / 1.5
print(planungsraum['diff'].max())
print(planungsraum['diff'].min())
data = (planungsraum['diff'] + 100000) / 200000

plr_def['data'] = data
plr_def['geom'] = planungsraum.geom

berlinplot = geoplot.GeoPlotter(**plr_def)
plt.box(on=None)
berlinplot.plot(plt.subplot(111), linewidth=0)
berlinplot.draw_legend((-100000, 100000), legendlabel="", location='right',
                       extend='both', integer=True)
plt.tight_layout()
plt.show()

print(area_plr.sum())
