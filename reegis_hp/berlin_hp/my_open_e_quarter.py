# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import time
import os
import pandas as pd
import oemof.db as db
from oemof.tools import logger
import Open_eQuarterPy.building_evaluation as be


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
        SELECT DISTINCT ag.gid, ew.ew_ha2014, block.schluessel,
            ag.anzahldero, ag.strassen_n,
            ag.hausnummer, ag.pseudonumm, st_area(st_transform(ag.geom, 3068)),
            st_perimeter(st_transform(ag.geom, 3068)), ag.gebaeudefu,
            sn.typklar, hz."PRZ_NASTRO", hz."PRZ_FERN", hz."PRZ_GAS",
            hz."PRZ_OEL", hz."PRZ_KOHLE", ag.year_of_construction,
            plr.schluessel
        FROM berlin.{0} as space, berlin.alkis_gebaeude ag
        INNER JOIN berlin.stadtnutzung sn ON st_within(
            st_centroid(ag.geom), sn.geom)
        INNER JOIN berlin.einwohner ew ON st_within(
            st_centroid(ag.geom), ew.geom)
        INNER JOIN berlin.heizungsarten_geo hz ON st_within(
            st_centroid(ag.geom), hz.geom)
        INNER JOIN berlin.block block ON st_within(
            st_centroid(ag.geom), block.geom)
        INNER JOIN berlin.planungsraum  plr ON st_within(
            st_centroid(ag.geom), plr.geom)
        WHERE
            space.geom && ag.geom AND
            st_contains(space.geom, st_centroid(ag.geom)) AND
            ag.bauart_sch is NULL AND
            {1}
            ag.anzahldero::int > 0
        ;
    '''.format(spacetype, where_space)

logger.define_logging()
start = time.time()

# Select region
level, selection = ('berlin', None)
# level, selection = ('bezirk', 6)
# level, selection = ('planungsraum', 384)
# level, selection = ('block', (5812, 9335))
overwrite = False

sql = sql_string(level, selection)

filename = "/home/uwe/chiba/RLI/data/eQuarter_0-73_{0}_newage.hdf".format(level)
dfilename = "/home/uwe/chiba/RLI/data/eQuarter_data_{0}.hdf".format(level)

if not os.path.isfile(dfilename):

if not os.path.isfile(datafilepath) or overwrite:
    start_db = time.time()
    conn = db.connection()
    logging.debug("SQL query: {0}".format(sql))
    logging.info("Retrieving data from db...")
    results = (conn.execute(sql))

    data = pd.DataFrame(results.fetchall(), columns=[
        'gid', 'population_density', 'spatial_na', 'floors', 'name_street',
        'number', 'alt_number', 'area', 'perimeter', 'building_function',
        'blocktype', 'frac_off-peak_electricity_heating',
        'frac_district_heating', 'frac_natural_gas_heating',
        'frac_oil_heating', 'frac_coal_stove', 'age_scan', 'plr_key'])

    data.number.fillna(data.alt_number, inplace=True)
    data.drop('alt_number', 1, inplace=True)

    # Convert objects from db to floats:
    data.floors = data.floors.astype(float)
    data.population_density = data.population_density.astype(float)
    data.building_function = data.building_function.astype(int)

    # Define default year of construction
    data['year_of_construction'] = 1960
    sn_data = pd.read_csv("/home/uwe/chiba/RLI/data/data_by_blocktype.csv", ';')
    data = data.merge(sn_data, on='blocktype')
    data.to_hdf(dfilename, 'data')
    logging.info("DB time: {0}".format(time.time() - start_db))
else:
    logging.info("Retrieving data from file: {0}".format(dfilename))
    data = pd.read_hdf(dfilename, 'data')

# *** Year of construction ***
# Fill up the nan values in the scan data with the data from the area types
data['age_scan'].fillna(data['building_age'], inplace=True)

# Replace ranges with one year.
age_of_construction = {
    '1950-1979': 1964,
    'ab 1945': 1970,
    '1920-1939': 1929,
    '1920-1949': 1934,
    '1870-1918': 1894,
    'bis 1945': 1920,
    '1870-1945': 1908,
    '1890-1930': 1910,
    '1960-1989': 1975,
    'ab 1990': 2003,
    '1870-1899': 1885,
    'bis 1869': 1860,
    '1900-1918': 1909,
    '1975-1992': 1984,
    '1962-1974': 1968,
    '1946-1961': 1954,
    '1919-1932': 1926,
    '1933-1945': 1939
    }
data['age_scan'].replace(age_of_construction, inplace=True)

# Fill all remaining nan values with a default value of 1960
data['year_of_construction'] = data['age_scan'].fillna(1960)

# *** Type of the building ***
# 1100 - Gemischt genutztes Gebäude mit Wohnen
# 1110 - Wohngebäude mit Gemeinbedarf
# 1120 - Wohngebäude mit Handel und Dienstleistungen
# 1130 - Wohngebäude mit Gewerbe und Industrie
# 1220 - Land- und forstwirtschaftliches Wohn- und Betriebsgebäude
# 2310 - Gebäude für Gewerbe und Industrie mit Wohnen
# 3100 - Gebäude für öffentliche Zwecke mit Wohnen
typelist = {
    1000: 1,
    1010: 1,
    1020: 1,
    1024: 1,
    1100: 0.2,
    1110: 0.2,
    1120: 0.2,
    1130: 0.2,
    1220: 0.2,
    2310: 0.2,
    3100: 0.2}

# Filter by building_types to get only (partly) residential buildings
query_str = ""
for typ in typelist.keys():
    query_str += "building_function == {0} or ".format(typ)
data = data.query(query_str[:-4])


for typ, value in typelist.items():
    if value < 1:
        data.loc[data.building_function == typ, 'residential_fraction'] = value

# Calculate the heat demand of the building
logging.debug("Data types of the DataFrame: {0}".format(data.dtypes))
logging.info("Calculate the heat demand of the buildings...")

parameter = {'fraction_living_area': 0.8}

result = be.evaluate_building(data, **parameter)

str_cols = ['spatial_na', 'name_street', 'number', 'blocktype',
            'age_scan', 'floors_average', 'floor_area_fraction',
            'building_age', 'share_non_tilted_roof']
result.loc[:, str_cols] = result[str_cols].applymap(str)

# Store results to hdf5 file
logging.info("Store results to {0}".format(filename))
store = pd.HDFStore(filename)
store['oeq'] = result
store['age_of_construction'] = pd.Series(age_of_construction)
store['typelist'] = pd.Series(typelist)
store['parameter'] = pd.Series(parameter)
store.close()
logging.info("Elapsed time: {0}".format(time.time() - start))
