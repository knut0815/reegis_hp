# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import matplotlib.pyplot as plt
import logging
import time
import os
import pandas as pd
import geoplot
import oemof.db
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
    results = oemof.db.connection().execute(db_string)
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
df = pd.read_hdf(os.path.join(basic_path, 'haus_berlin_0_694.hdf'), 'alkis')
bloecke = pd.read_hdf(os.path.join(basic_path, 'bloecke.hdf'), 'block')
stadtnutzung = pd.read_hdf(
    os.path.join(basic_path, 'stadtnutzung_erweitert.hdf'), 'stadtnutzung')

# Filter by building_types to get only residential buildings
buildings = df.query(
    "building_function == 1000" +
    "or building_function == 1010"
    "or building_function == 1020"
    "or building_function == 1024"
    "or building_function == 1120"
    )

# Add schluessel_planungsraum to every building by merging the block table
buildings = buildings.merge(
    bloecke, right_on='schluessel', left_on='spatial_na')

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
planungsraum['diff'] = planungsraum.area_stadtnutz - planungsraum.area_alkis


sigma = np.std(planungsraum['diff'])
mu = planungsraum['diff'].mean()

import matplotlib.mlab as mlab
bins = 50

# the histogram of the data
n, bins, patches = plt.hist(planungsraum['diff'], 50, facecolor='green', alpha=0.75, normed=1)

# add a 'best fit' line
y = (mlab.normpdf(bins, mu, sigma))
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

data = (planungsraum['diff'] + 100000) / 200000

plr_def['data'] = data
plr_def['geom'] = planungsraum.geom

berlinplot = geoplot.GeoPlotter(**plr_def)
plt.box(on=None)
berlinplot.plot(plt.subplot(111), linewidth=0)
berlinplot.draw_legend((-100000, 100000), legendlabel="EW*spez_Wohnf - Alkis",
                       extend='both', integer=True)
plt.tight_layout()
plt.show()

print(area_plr.sum() / 450)
