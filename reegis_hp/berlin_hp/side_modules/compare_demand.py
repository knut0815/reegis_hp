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
import numpy as np
import geoplot
import oemof.db
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

result = pd.read_hdf(
    '/home/uwe/.reegis_hp/heat_demand/eQuarter_berlin.hdf', 'oeq')

result['total_loss_mix'] = (result['total_loss_pres'] * 0.2 * 0.5 +
                            result['total_loss_pres'] * 0.8)
oeq_plr = pd.DataFrame(
    result.groupby('plr_key')['total_loss_mix'].sum())

oeq_plr = oeq_plr.set_index(oeq_plr.index.astype('float'))

wt_plr = pd.read_hdf('/home/uwe/demand_plr', 'wt')
print(wt_plr.sum())
print(oeq_plr.sum())
oeq_plr = oeq_plr.div(1.3755072160337949)
demand_plr = pd.merge(oeq_plr, wt_plr, right_index=True, left_index=True)
print(demand_plr.sum())

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

planungsraum['key'] = planungsraum.schluessel.astype(float)

# Merge the spatial column and the area columns
planungsraum = planungsraum.merge(demand_plr, left_on='key',
                                  right_index=True)

planungsraum['diff'] = planungsraum.total_loss_mix - planungsraum.total
oeq_f = planungsraum.total_loss_mix / planungsraum.total -1
oeq_f[oeq_f < 0] = 0
wt_f = planungsraum.total / planungsraum.total_loss_mix - 1
wt_f[wt_f < 0] = 0
planungsraum['frac'] = oeq_f - wt_f
print(planungsraum)
sigma = np.std(planungsraum['diff'])
mu = planungsraum['diff'].mean()

# the histogram of the data
n, bins, patches = plt.hist(planungsraum['diff'], 50, facecolor='green',
                            alpha=0.75, normed=1)
# add a 'best fit' line
y = mlab.normpdf(bins, mu, sigma)
l = plt.plot(bins, y, 'r--', linewidth=1)

plt.xlabel('Smarts')
plt.ylabel('Probability')
plt.title("Histogram: $\mu$={0}, $\sigma$={1}m²".format(int(mu), int(sigma)))
plt.grid(True)

plt.show()
# ax = planungsraum['diff'].plot.hist(bins, ax=plt.subplot(111))
planungsraum = planungsraum.replace(np.inf, 0)
sigma = np.std(planungsraum['frac'])
mu = planungsraum['frac'].mean()

planungsraum['frac'].to_csv('/home/uwe/test4.csv')

# the histogram of the data
n, bins, patches = plt.hist(planungsraum['frac'], 500, facecolor='green',
                            alpha=0.75)
# add a 'best fit' line
y = mlab.normpdf(bins, mu, sigma)
l = plt.plot(bins, y, 'r--', linewidth=1)

plt.xlabel('Smarts')
plt.ylabel('Probability')
print(mu, sigma)
plt.title("Histogram: $\mu$={0}, $\sigma$={1}m²".format(int(mu), int(sigma)))
plt.grid(True)

plt.show()

# data = (planungsraum['diff'] - 0.5) / 1.5
print(planungsraum['diff'].max())
print(planungsraum['diff'].min())

data = planungsraum.frac
data = data + 0.5

print(data)

# data = (planungsraum['diff'] + 10000000) / 20000000

plr_def['data'] = data
plr_def['geom'] = planungsraum.geom

berlinplot = geoplot.GeoPlotter(**plr_def)
plt.box(on=None)
berlinplot.plot(plt.subplot(111), linewidth=0)
berlinplot.draw_legend((-100000, 100000), legendlabel="", location='right',
                       extend='both', integer=True)
plt.tight_layout()
plt.show()

print(demand_plr.sum())

print(time.time() - start)
