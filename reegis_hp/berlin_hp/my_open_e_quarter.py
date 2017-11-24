# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import datetime
import os
import pandas as pd
from oemof import tools as otools
import Open_eQuarterPy.building_evaluation as be
from reegis_hp.berlin_hp import config as cfg


otools.logger.define_logging()
start = datetime.datetime.now()
overwrite = False

filename_hdf = os.path.join(cfg.get('paths', 'fis_broker'),
                            cfg.get('fis_broker', 'alkis_joined_hdf'))
filename_csv = os.path.join(cfg.get('paths', 'fis_broker'),
                            cfg.get('fis_broker', 'alkis_joined_csv'))
filename_geo_csv = os.path.join(cfg.get('paths', 'fis_broker'),
                                cfg.get('fis_broker', 'alkis_geometry_csv'))
filename_oeq_results = os.path.join(cfg.get('paths', 'oeq'),
                                    cfg.get('oeq', 'results'))

if not os.path.isfile(filename_hdf) or overwrite:
    # fetch data from download module
    pass

data = pd.read_hdf(filename_hdf, 'alkis')
data['alkis_id'] = data.index

sn_data = pd.read_csv(os.path.join(cfg.get('paths', 'static'),
                                   'data_by_blocktype.csv'), ';')

pd.DataFrame(data['TYPKLAR'].unique()).to_excel('/home/uwe/test1.xlsx')
data = data.merge(sn_data, on='TYPKLAR', how='left')
data.set_index('alkis_id', drop=True, inplace=True)

rename_alkis = {
    'AnzahlDerO': 'floors',
    'Gebaeudefu': 'building_function',
    'SCHL5': 'block',
    'PLR': 'lor',
    'STAT': 'statistical_region',
    'TYPKLAR': 'block_type_name',
    'EW_HA': 'population_density',
    'PRZ_FERN': 'frac_district_heating',
    'PRZ_GAS': 'frac_gas',
    'PRZ_KOHLE': 'frac_coal',
    'PRZ_NASTRO': 'frac_elec',
    'PRZ_OEL': 'frac_oil',
    'type': 'block_type',
    }

data = data.rename(columns=rename_alkis)

# data = data.loc[data['lor'] == 1011101]
# *** Year of construction ***

# Replace ranges with one year.
year_of_construction = {
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
    '1933-1945': 1939,
    'None': None,
    'NaN': None,
    'nan': None
    }
# data['age_scan'].replace(year_of_construction, inplace=True)
data['building_age'].replace(year_of_construction, inplace=True)

# Fill all remaining nan values with a default value of 1960
data['year_of_construction'] = data['building_age'].fillna(1960)

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

# # Filter by building_types to get only (partly) residential buildings
# query_str = ""
# for typ in typelist.keys():
#     query_str += "building_function == {0} or ".format(typ)
# data = data.query(query_str[:-4])


for typ, value in typelist.items():
    if value < 1:
        data.loc[data.building_function == typ, 'residential_fraction'] = value

# Calculate the heat demand of the building
logging.debug("Data types of the DataFrame: {0}".format(data.dtypes))
logging.info("Calculate the heat demand of the buildings...")

parameter = {'fraction_living_area': 0.8}

result = be.evaluate_building(data, **parameter)

result['total'] = result.total_loss_pres

print(result.dtypes)
str_cols = ['block', 'block_type_name', 'share_non_tilted_roof']
result.loc[:, str_cols] = result[str_cols].applymap(str)

# Store results to hdf5 file
logging.info("Store results to {0}".format(filename_oeq_results))
store = pd.HDFStore(filename_oeq_results)
store['oeq'] = result
store['year_of_construction'] = pd.Series(year_of_construction)
store['typelist'] = pd.Series(typelist)
store['parameter'] = pd.Series(parameter)
# if isinstance(selection, int):
#     selection = (selection,)
# if selection is None:
#     selection = (0,)
# store['selection'] = pd.Series(list(selection), name=level)
store.close()
logging.warning('No date saved! Please add date to hdf5-file.')
logging.info("Elapsed time: {0}".format(datetime.datetime.now() - start))
