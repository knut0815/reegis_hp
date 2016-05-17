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

df = pd.read_csv(os.path.join(basic_path, 'haus_block_test.csv'), index_col=0)
iwu_typen = pd.read_csv(os.path.join(basic_path, 'iwu_typen.csv'), index_col=0)
blocktype = pd.read_csv(os.path.join(basic_path, 'blocktype.csv'), ';',
                         index_col=0)

buildings = df.query("building_function == 1010")
# print(buildings.blocktype)

iwu_by_blocktype = iwu_typen.merge(blocktype, left_index=True, right_index=True)
buildings_full = buildings.merge(iwu_by_blocktype, on='blocktype')
print(buildings_full.columns)
print(buildings_full[['MFHv84', 'EFHv84']].multiply(
    buildings_full[['living_area', 'flatroof_area']], axis=1))
print(buildings_full[['MFHv84', 'EFHv84']].values * buildings_full[['living_area', 'flatroof_area']].values)


