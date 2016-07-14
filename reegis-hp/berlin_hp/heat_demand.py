# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import time
import os
import pandas as pd
import oemof.db
from oemof.tools import logger


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

basic_path = '/home/uwe/chiba/RLI/data'
logging.info("Datapath: {0}:".format(basic_path))

# Load the yearly demand of the standardised buildings
wt_demand = pd.read_csv(os.path.join(basic_path, 'waermetool_demand.csv'),
                        index_col=0)

# Define names of standardised buildings
std_buildings = ['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']

# Load results of Open_eQuarter analyses
oeq = pd.read_hdf(os.path.join(basic_path, 'eQuarter_0-694_berlin.hdf'), 'oeq')

# Load assignment of standardised building types to all area types
iwu4types = pd.read_csv(os.path.join(basic_path, 'iwu_typen.csv'), index_col=0)

# Load list of area types with full name and "typklar" name from db
blocktype = pd.read_csv(os.path.join(basic_path, 'blocktype.csv'), ';',
                        index_col=0)

# Load geometry of all Blocks
bloecke = pd.read_hdf(os.path.join(basic_path, 'bloecke.hdf'), 'bloecke')

# Load "stadtnutzung" from SenStadt extended by residents and population density
stadtnutzung = pd.read_csv(
    os.path.join(basic_path, 'stadtnutzung_erweitert.csv'), index_col=0)

oeq_query = oeq.query(
    "building_function == 1000" +
    "or building_function == 1010"
    "or building_function == 1020"
    "or building_function == 1024"
    "or building_function == 1120"
    )

# Merge "typklar" as blocktype to fraction of each iwu-type
iwu4block = iwu4types.merge(blocktype, left_index=True, right_index=True)

# Merge fraction of building types to all oeq_buildings
buildings = oeq_query.merge(iwu4block, on='blocktype')

# Merge fraction of building types to all blocks
stadtnutzung_full = stadtnutzung.merge(iwu4block, right_on='blocktype',
                                       left_on='typklar')

sanierungsquote = pd.Series(data=[0.12, 0.03, 0.08, 0.01, 0.29],
                            index=wt_demand.index)

demand_by_type_unsaniert = pd.DataFrame(
    (stadtnutzung_full[[
        'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
            stadtnutzung_full.ew * stadtnutzung_full.wohnflaeche_pro_ew,
            axis="index").values *
        wt_demand['unsaniert'].values *
        (1 - sanierungsquote).values),
    columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']).merge(
        stadtnutzung_full[['spatial_na', 'schluessel_planungsraum']],
        left_index=True, right_index=True)

demand_by_type_saniert = pd.DataFrame(
    (stadtnutzung_full[[
        'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
            stadtnutzung_full.ew * stadtnutzung_full.wohnflaeche_pro_ew,
            axis="index").values *
        wt_demand['saniert'].values *
        sanierungsquote.values),
    columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']).merge(
        stadtnutzung_full[['spatial_na', 'schluessel_planungsraum']],
        left_index=True, right_index=True)

total_demand_wt = (demand_by_type_saniert[std_buildings].sum().sum() +
                   demand_by_type_unsaniert[std_buildings].sum().sum())

print(buildings['total_loss_pres'].sum())
print(buildings['total_loss_contemp'].sum())
print(buildings.living_area.sum())
print(total_demand_wt)

print(time.time() - start)
