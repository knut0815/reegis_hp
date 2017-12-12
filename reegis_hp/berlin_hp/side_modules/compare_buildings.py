import pandas as pd
import time
import logging
import os

from reegis_hp.berlin_hp import config as cfg
from oemof.tools import logger

logger.define_logging()
start = time.time()

logging.info("Starting...")


filename_oeq_results = os.path.join(cfg.get('paths', 'oeq'),
                                    cfg.get('oeq', 'results'))
filename_heat_profile = os.path.join(cfg.get('paths', 'oeq'),
                                     'heat_profile_state_2012.csv')
filename_heat_factor = os.path.join(cfg.get('paths', 'static'),
                                    'heat_factor_by_building_type.csv')
heat = pd.read_csv(filename_heat_profile, index_col=[0], header=[0, 1, 2],
                   parse_dates=True)
heat_factor = pd.read_csv(filename_heat_factor, index_col=[0])
print(heat['BE'].sum())
print(heat['BE'].sum().groupby(level=1).sum() * 1/3.6e+3)
print(heat['BE'].sum().groupby(level=0).sum() * 1/3.6e+3)
print((heat['BE'].sum().groupby(level=1).sum().sum() - heat['BE'].sum().groupby(
    level=1).sum()['total']) * 1/3.6e+3)

data = pd.read_hdf(filename_oeq_results, 'oeq')
logging.info("Query...")

subset = data.query("building_function == 1010")
logging.info("Sum...")
cols = ['air_change_heat_loss', 'total_trans_loss_pres',
        'total_trans_loss_contemp', 'total_loss_pres', 'total_loss_contemp',
        'HLAC', 'HLAP', 'AHDC', 'AHDP', 'total']
print(data[cols].sum() / 1000 / 1000 / 1000)
frac_cols = ['frac_district_heating', 'frac_gas', 'frac_coal', 'frac_elec',
             'frac_oil']
data['check'] = data[frac_cols].sum(axis=1)

data.loc[data['check'] > 95, frac_cols] = data.loc[data['check'] > 95, frac_cols].multiply((100 / data.loc[data['check'] > 95, 'check']), axis=0)
data['check'] = data[frac_cols].sum(axis=1)
length = len(data.loc[round(data['check']) == 100, frac_cols])
s = data.loc[data['check'] > 95, frac_cols].sum()/length

data.loc[data['check'] < 1, frac_cols] = data.loc[data['check'] < 1, frac_cols] + s
data['check'] = data[frac_cols].sum(axis=1)

print(data['total'].sum() / 1000 / 1000 / 1000)
del heat_factor['gebaeude_1']
data = data.merge(heat_factor, left_on='building_function', right_index=True)
data['total'] = data['total'] * data['heat_factor']
print(data['total'].sum() / 1000 / 1000 / 1000)
data[frac_cols] = data[frac_cols].multiply(data['total'] * 0.01, axis=0)
print((data['total'].sum() - data['frac_elec'].sum()) / 1000 / 1000 / 1000)
print(data[frac_cols].sum() / 1000 / 1000 / 1000)
print(data[frac_cols].sum().sum() / 1000 / 1000 / 1000)

print(subset.total_loss_contemp.sum() / subset.living_area.sum())
print(subset.total_loss_pres.sum() / subset.living_area.sum())
