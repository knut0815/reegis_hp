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
from Open_eQuarterPy import building_evaluation as be


def sql_string(spacetype, space_gid=None):
    """
    spacetype (string): Type of space (berlin, bezirk, block, planungsraum...)
    space_gid (tuple): chosen gids for
    """
    if space_gid is None:
        space_gid = "everything"
    logging.info("From table berlin.{1} get {0}.".format(
        space_gid, spacetype))
    if spacetype != "berlin":
        if isinstance(space_gid, int):
            space_gid = "({0})".format(space_gid)
        where_space = "space.gid in {0} AND".format(space_gid)
    else:
        where_space = ''

    return '''
        SELECT DISTINCT ag.gid, ew.ew_ha2014, ag.anzahldero, ag.strassen_n,
            ag.hausnummer, ag.pseudonumm, st_area(st_transform(ag.geom, 3068)),
            st_perimeter(st_transform(ag.geom, 3068)), ag.gebaeudefu,
            sn.typklar, hz."PRZ_NASTRO", hz."PRZ_FERN", hz."PRZ_GAS",
            hz."PRZ_OEL", hz."PRZ_KOHLE"
        FROM berlin.{0} as space, berlin.alkis_gebaeude ag
        INNER JOIN berlin.stadtnutzung sn ON st_within(
            st_centroid(ag.geom), sn.geom)
        INNER JOIN berlin.einwohner ew ON st_within(
            st_centroid(ag.geom), ew.geom)
        INNER JOIN berlin.heizungsarten_geo hz ON st_within(
            st_centroid(ag.geom), hz.geom)
        WHERE
            space.geom && ag.geom AND
            st_contains(space.geom, st_centroid(ag.geom)) AND
            ag.bauart_sch is NULL AND
            {1}
            ag.anzahldero::int > 0
        ;
    '''.format(spacetype, where_space)

logger.define_logging()
conn = db.connection()
start = time.time()

filename = "/home/uwe/haus_berlin.csv"

sql = sql_string('berlin')
# sql = sql_string('bezirk', 7)
# sql = sql_string('planungsraum', (1, 2, 3))
# sql = sql_string('block', (5812, 9335))

logging.debug("SQL query: {0}".format(sql))
logging.info("Retrieving data from db...")
results = (conn.execute(sql))

data = pd.DataFrame(results.fetchall(), columns=[
    'gid', 'population_density', 'floors', 'name_street', 'number',
    'alt_number', 'area', 'perimeter', 'building_function', 'blocktype',
    'frac_off-peak_electricity_heating', 'frac_district_heating',
    'frac_natural_gas_heating', 'frac_oil_heating', 'frac_coal_stove'])

data.number.fillna(data.alt_number, inplace=True)
data.drop('alt_number', 1, inplace=True)

# Convert objects from db to floats:
data.floors = data.floors.astype(float)
data.population_density = data.population_density.astype(float)
data.building_function = data.building_function.astype(int)

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
