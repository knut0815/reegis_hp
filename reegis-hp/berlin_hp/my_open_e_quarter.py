# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import time
import pandas as pd
from oemof import db
from oemof.tools import logger
from Open_eQuarterPy.stat_util import building_evaluation as be


def sql_string(spacetype, space_gid=None):
    """
    spacetype (string): Type of space (berlin, bezirk, block, planungsraum...)
    space_gid (tuple): chosen gids for
    """
    if spacetype != "berlin":
        if isinstance(space_gid, int):
            space_gid = "({0})".format(space_gid)
        where_space = "space.gid in {0} AND".format(space_gid)
    else:
        where_space = ''

    return '''
        SELECT
            space.gid, alkis_ew.ew_ha2014, alkis_ew.gid, alkis_ew.anzahldero,
            alkis_ew.strassen_n, alkis_ew.hausnummer, alkis_ew.pseudonumm,
            alkis_ew.st_area, alkis_ew.st_perimeter
        FROM
            (SELECT
                    ew.ew_ha2014, ag.gid, ag.anzahldero, ag.strassen_n,
                    ag.hausnummer, ag.pseudonumm,
                    st_area(st_transform(ag.geom, 3068)),
                    st_perimeter(st_transform(ag.geom, 3068)), ag.geom,
                    ag.bauart_sch
                FROM
                    berlin.einwohner ew
                INNER JOIN
                    berlin.alkis_gebaeude ag ON st_within(ag.geom, ew.geom)
                WHERE
                    ag.bauart_sch is NULL) as alkis_ew,

            berlin.{0} as space
        WHERE
            ST_contains(space.geom, st_centroid(alkis_ew.geom)) AND
            {1}
            alkis_ew.bauart_sch is NULL
    ;
    '''.format(spacetype, where_space)

logger.define_logging()
conn = db.connection()
start = time.time()

filename = "/home/uwe/haus.csv"

sql = sql_string('berlin')
sql = sql_string('bezirk', 7)
sql = sql_string('planungsraum', (1, 2, 3))
sql = sql_string('block', (5812, 9335))

logging.info("Retrieving data from db....")
results = (conn.execute(sql))

data = pd.DataFrame(results.fetchall(), columns=[
    'block_id', 'population_density', 'gid', 'floors', 'name_street', 'number',
    'alt_number', 'area', 'perimeter'])

data.set_index('gid', drop=True, inplace=True)
data.number.fillna(data.alt_number, inplace=True)
data.drop('alt_number', 1, inplace=True)

# Convert objects from db to floats:
data.floors = data.floors.astype(float)
data.population_density = data.population_density.astype(float)

# Define default year of construction
data['year_of_construction'] = 1960

# Calculate the heat demand of the building
logging.debug("Data types of the DataFrame: {0}".format(data.dtypes))
logging.info("Calculate the heat demand of the buildings...")
result = be.evaluate_building(data)

# Store results to csv file
logging.info("Store results to {0}".format(filename))
result.to_csv(filename)
logging.info("Elapsed time: {0}".format(time.time() - start))
