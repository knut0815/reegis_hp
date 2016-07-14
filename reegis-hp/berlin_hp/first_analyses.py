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
plt.style.use('ggplot')
import oemof.db
from oemof.tools import logger
from shapely.wkt import loads as wkt_loads
import pickle


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

# Load geometry of all "planungsraum"
plr = pickle.load(open('plr.data', 'rb'))

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
exit(0)
# buildings = buildings.merge(
#     bloecke, right_on='schluessel', left_on='spatial_na')
#
# area_plr_alkis = pd.DataFrame(
#     buildings.groupby('schluessel_planungsraum')['living_area'].sum())
#
# area_plr_alkis = plr.merge(area_plr_alkis, right_index=True,
#                            left_on='schluessel')
# demand_by_type_unsaniert = pd.DataFrame(
#     buildings_full[['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
#         buildings_full['living_area'], axis="index").values *
#     wt_demand['unsaniert'].values,
#     columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte'])
# sum_by_type_unsaniert = demand_by_type_unsaniert.sum()
#
# demand_by_type_saniert = pd.DataFrame(
#     buildings_full[['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
#         buildings_full['living_area'], axis="index").values *
#     wt_demand['saniert'].values,
#     columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte'])
# sum_by_type_saniert = demand_by_type_saniert.sum()
#
# area = stadtstruktur_full[[
#         'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
#             stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew,
#             axis="index")
#
# stadtstruktur_full['area'] = (
#     stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew)
# print(stadtstruktur_full.wohnflaeche_pro_ew.max())
# print(stadtstruktur_full.columns)
#
# area_plr_statistik = pd.DataFrame(stadtstruktur_full.groupby(
#     'schluessel_planungsraum')['area'].sum())
#
# print(area_plr_alkis.columns)
# print(area_plr_alkis.index)
# print(area_plr_statistik.columns)
# print(area_plr_statistik.index)
#
# area_plr_alkis = area_plr_alkis.merge(area_plr_statistik, left_on='schluessel',
#                                       right_index=True)
#
# area_plr_alkis['diff'] = area_plr_alkis['area'] / area_plr_alkis['living_area']
#
# print(area_plr_alkis['diff'].max())
# print(area_plr_alkis['diff'].min())
# data = np.array(area_plr_alkis['diff'] / 2)
#
# bplot = geoplot.GeoPlotter(geom=area_plr_alkis.shp_geo,
#                            bbox=(13.1, 13.76, 52.3, 52.7),
#                            data=data)
# bplot.draftplot()
# exit(0)
# bloecke['shp_geo'] = bloecke.geom.apply(wkt_loads)
# pickle.dump(bloecke, open('block.data', 'wb'))
# bloecke = pickle.load(open('block.data', 'rb'))
#
# stadtstruktur_full = stadtstruktur_full.merge(
#     bloecke[['shp_geo', 'schluessel']], right_on='schluessel',
#     left_on='spatial_na')

# print(stadtstruktur_full.wohnflaeche_pro_ew.max())
# print(stadtstruktur_full.wohnflaeche_pro_ew.min())
# data = (stadtstruktur_full.wohnflaeche_pro_ew) / 116
#
# plt.plot(data)
# plt.show()
#
#
# bplot = geoplot.GeoPlotter(geom=stadtstruktur_full.shp_geo,
#                            bbox=(13.1, 13.76, 52.3, 52.7),
#                            data=data)
#
# bplot.draftplot()
# exit(0)
# print('Area', area.sum())
# # Area EFHv84    2.108395e+07
# # EFHn84    2.676466e+06
# # MFHv84    7.980254e+07
# # MFHn84    1.330757e+07
# # Platte    2.111442e+07
#
# print(wt_demand)
# sanierungsquote = pd.Series(data=[0.12, 0.03, 0.08, 0.01, 0.29],
#                             index=wt_demand.index)
# print(sanierungsquote)
#
# print(type(stadtstruktur_full[[
#         'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
#             stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew,
#             axis="index").values * wt_demand['unsaniert'].values))
#
# # TODO Überprüfe ob die Operation die Reihenfolge erhält
# demand_by_type_unsaniert = pd.DataFrame(
#     (stadtstruktur_full[[
#         'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
#             stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew,
#             axis="index").values *
#         wt_demand['unsaniert'].values *
#         (1 - sanierungsquote).values),
#     columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']).merge(
#         stadtstruktur_full[['spatial_na', 'schluessel_planungsraum']],
#         left_index=True, right_index=True)
#
# demand_by_type_saniert = pd.DataFrame(
#     (stadtstruktur_full[[
#         'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
#             stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew,
#             axis="index").values *
#         wt_demand['saniert'].values *
#         sanierungsquote.values),
#     columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']).merge(
#         stadtstruktur_full[['spatial_na', 'schluessel_planungsraum']],
#         left_index=True, right_index=True)
#
# sum_by_type_unsaniert = demand_by_type_unsaniert.sum()
# sum_by_type_saniert = demand_by_type_saniert.sum()
# print(sum_by_type_unsaniert[gebaeudetypen].sum())
# print(sum_by_type_saniert[gebaeudetypen].sum())

print(sum_by_type_saniert.sum() / buildings_full['living_area'].sum())
print(sum_by_type_unsaniert.sum() / buildings_full['living_area'].sum())
print(sum_by_type_saniert.sum() / (stadtstruktur_full.ew *
                                   stadtstruktur_full.wohnflaeche_pro_ew).sum())
print(sum_by_type_unsaniert.sum() / (
    stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew).sum())
print(buildings_full['total_loss_pres'].sum())
print(buildings_full['total_loss_contemp'].sum())
print(buildings_full['living_area'].sum())
print('Area', area.sum().sum())

print(buildings_full['living_area'].sum())

# print(buildings_full[['MFHv84', 'EFHv84']].values * buildings_full[[
#     'living_area', 'flatroof_area']].values)


