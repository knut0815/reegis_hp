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

sync_path = '/home/uwe/chiba/RLI/data'
basic_path = '/home/uwe/.oemof/reegis_hp'

logging.info("Datapath: {0}:".format(basic_path))

# Load results of Open_eQuarter analyses
oeq = pd.read_hdf(os.path.join(basic_path, 'buildings.hdf'), 'oeq')
print(len(oeq))

# Load assignment of standardised building types to all area types
iwu4types = pd.read_csv(os.path.join(sync_path, 'iwu_typen.csv'), index_col=0)

# Load list of area types with full name and "typklar" name from db
blocktype = pd.read_csv(os.path.join(sync_path, 'blocktype.csv'), ';',
                        index_col=0)

# Merge "typklar" as blocktype to fraction of each iwu-type
iwu4block = iwu4types.merge(blocktype, left_index=True, right_index=True)

# Merge fraction of building types to all oeq_buildings
buildings = oeq.merge(iwu4block, on='blocktype')
print(buildings.columns)

demand_by_type = pd.read_csv("/home/uwe/waermetool.csv")

print(buildings['total_loss_pres'].sum() * 0.2)
print(buildings['total_loss_contemp'].sum() * 0.8)
buildings['total_loss_mix'] = (buildings['total_loss_pres'] * 0.2 +
                               buildings['total_loss_contemp'] * 0.8) * 0.518512
print(buildings['total_loss_mix'].sum())
print(buildings.living_area.sum())
print(buildings['total_loss_pres'].sum() * 0.2 +
      buildings['total_loss_contemp'].sum() * 0.8)

oeq_plr = pd.DataFrame(
    buildings.groupby('schluessel_planungsraum')['total_loss_mix'].sum())
wt_plr = pd.DataFrame(
    demand_by_type.groupby('schluessel_planungsraum')['total'].sum())

demand_plr = pd.merge(oeq_plr, wt_plr, right_index=True, left_index=True)

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
data = (planungsraum['diff'] + 10000000) / 20000000

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
