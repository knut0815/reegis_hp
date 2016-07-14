# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import matplotlib.pyplot as plt
import logging
import time
import pandas as pd
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

map_def = {
        'table': 'power_grids',
        'geo_col': 'geom',
        'id_col': 'gid',
        'schema': 'world',
        'simp_tolerance': '0',
        'where_col': 'grid_level',
        'where_cond': "= 'entsoe_eu_31'",
        }
logging.info("Retrieving data from database...")
df = fetch_geometries(**map_def)
path = '/home/uwe/geo.csv'
logging.info("Save data to csv: {0}".format(path))
df.to_csv(path)
