# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""

import logging
import time
import os
import pandas as pd

# from oemof import db
from oemof.tools import logger


logger.define_logging()
# conn = db.connection()
start = time.time()

basic_path = '/home/uwe/chiba/RLI/data'
logging.info("Datapath: {0}:".format(basic_path))

wt_demand = pd.read_csv(os.path.join(basic_path, 'waermetool_demand.csv'),
                        index_col=0)
print(wt_demand['unsaniert'].values)
print(wt_demand['saniert'].values)

df = pd.read_csv(os.path.join(basic_path, 'haus_berlin.csv'), index_col=0)
iwu_typen = pd.read_csv(os.path.join(basic_path, 'iwu_typen.csv'), index_col=0)
blocktype = pd.read_csv(os.path.join(basic_path, 'blocktype.csv'), ';',
                        index_col=0)
stadtstrukturtypen = pd.read_csv(
    os.path.join(basic_path, 'stadtnutzung_erweitert.csv'), index_col=0)

buildings = df.query("building_function == 1010")
# print(buildings.blocktype)

iwu_by_blocktype = iwu_typen.merge(blocktype, left_index=True, right_index=True)

buildings_full = buildings.merge(iwu_by_blocktype, on='blocktype')
stadtstruktur_full = stadtstrukturtypen.merge(iwu_by_blocktype,
                                              right_on='blocktype',
                                              left_on='typklar')

print(stadtstruktur_full.columns)
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

area = pd.DataFrame(
    stadtstruktur_full[[
        'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
            stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew,
            axis="index"),
    columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte'])

print('Area', area.sum())

demand_by_type_unsaniert = pd.DataFrame(
    stadtstruktur_full[[
        'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
            stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew,
            axis="index").values *
    wt_demand['unsaniert'].values,
    columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte'])
sum_by_type_unsaniert = demand_by_type_unsaniert.sum()

demand_by_type_saniert = pd.DataFrame(
    stadtstruktur_full[[
        'EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte']].multiply(
            stadtstruktur_full.ew * stadtstruktur_full.wohnflaeche_pro_ew,
            axis="index").values *
    wt_demand['saniert'].values,
    columns=['EFHv84', 'EFHn84', 'MFHv84', 'MFHn84', 'Platte'])
sum_by_type_saniert = demand_by_type_saniert.sum()

# print(stadtstruktur_full)

sanierungsquote = pd.Series(index=sum_by_type_saniert.index,
                            data=[0.12, 0.03, 0.08, 0.01, 0.29])
print(1 - sanierungsquote)
unsan = (sum_by_type_saniert * sanierungsquote).sum()
san = (sum_by_type_unsaniert * (1 - sanierungsquote)).sum()
print(unsan + san)
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

# print(buildings_full[['MFHv84', 'EFHv84']].values * buildings_full[[
#     'living_area', 'flatroof_area']].values)


