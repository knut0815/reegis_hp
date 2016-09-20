# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import time
import os
import pandas as pd
import numpy as np
from oemof.tools import logger

logger.define_logging()

start = time.time()

sync_path = '/home/uwe/chiba/RLI/data'
basic_path = '/home/uwe/.oemof/reegis_hp'

# Define names of standardised buildings
std_buildings = ['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']
sanierungsquote = np.array([0.12, 0.03, 0.08, 0.01, 0.29])

logging.info("Datapath: {0}:".format(basic_path))

# Load the yearly demand of the standardised buildings
wt_demand = pd.read_csv(os.path.join(sync_path, 'waermetool_demand.csv'),
                        index_col=0)

# Load assignment of standardised building types to all area types
iwu4types = pd.read_csv(os.path.join(sync_path, 'iwu_typen.csv'), index_col=0)

# Load list of area types with full name and "typklar" name from db
blocktype = pd.read_csv(os.path.join(sync_path, 'blocktype.csv'), ';',
                        index_col=0)

# Load "stadtnutzung" from SenStadt extended by residents and population density
stadtnutzung = pd.read_csv(
    os.path.join(sync_path, 'stadtnutzung_erweitert.csv'), index_col=0)

# Merge "typklar" as blocktype to fraction of each iwu-type
iwu4block = iwu4types.merge(blocktype, left_index=True, right_index=True)

# Merge fraction of building types to all blocks
stadtnutzung_full = stadtnutzung.merge(iwu4block, right_on='blocktype',
                                       left_on='typklar')

# Determine the living area
stadtnutzung_full['living_area'] = (stadtnutzung_full.ew *
                                    stadtnutzung_full.wohnflaeche_pro_ew)

# Determine the demand by type
demand_by_type_unsaniert = pd.DataFrame(
    (stadtnutzung_full[[
        'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
            stadtnutzung_full.living_area, axis="index").values *
        wt_demand['unsaniert'].values * (1 - sanierungsquote)),
    columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']).merge(
        stadtnutzung_full[['spatial_na', 'schluessel_planungsraum']],
        left_index=True, right_index=True)

demand_by_type_saniert = pd.DataFrame(
    (stadtnutzung_full[[
        'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
            stadtnutzung_full.living_area, axis="index").values *
        wt_demand['saniert'].values * sanierungsquote),
    columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']).merge(
        stadtnutzung_full[['spatial_na', 'schluessel_planungsraum']],
        left_index=True, right_index=True)

total_demand_wt = (demand_by_type_saniert[std_buildings].sum().sum() +
                   demand_by_type_unsaniert[std_buildings].sum().sum())

demand_by_type = demand_by_type_unsaniert.merge(
    demand_by_type_saniert, left_index=True, right_index=True)

for typ in std_buildings:
    demand_by_type[typ] = (demand_by_type[typ + '_y'] +
                           demand_by_type[typ + '_x'])

demand_by_type.rename(columns={'schluessel_planungsraum_x':
                               'schluessel_planungsraum'}, inplace=True)

demand_by_type['total'] = 0

for std_bld in std_buildings:
    demand_by_type['total'] += demand_by_type[std_bld]

demand_by_type.to_csv("/home/uwe/waermetool.csv")

# # Store results to hdf5 file
# logging.info("Store results to {0}".format(filepath))
# store = pd.HDFStore(filepath)
# store['oeq'] = result
# store['year_of_construction'] = pd.Series(year_of_construction)
# store['typelist'] = pd.Series(typelist)
# store['parameter'] = pd.Series(parameter)
# if isinstance(selection, int):
#     selection = (selection,)
# if selection is None:
#     selection = (0,)
# store['selection'] = pd.Series(list(selection), name=level)
# store.close()

wt_plr = pd.DataFrame(
    demand_by_type.groupby('schluessel_planungsraum')['total'].sum())

wt_plr.to_hdf('/home/uwe/demand_plr', 'wt')

print(time.time() - start)
