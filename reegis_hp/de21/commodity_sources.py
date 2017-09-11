__copyright__ = "Uwe Krien"
__license__ = "GPLv3"

import pandas as pd
import numpy as np
import os

import logging
from oemof.tools import logger
import configuration as config
from reegis_hp.de21 import tools as t


def initialise_commodity_sources():
    cols = pd.MultiIndex(levels=[[], []], labels=[[], []], names=['', ''])
    src = pd.DataFrame(columns=cols, index=range(1990, 2017))
    return src


def prices_from_bmwi_energiedaten(c, src):
    fuels = {
        '  - Rohöl': 'Oil',
        '  - Erdgas': 'Natural gas',
        '  - Steinkohlen': 'Hard coal'
    }

    filename = t.get_bmwi_energiedaten_file()

    # get prices for commodity source from sheet 26
    fs = pd.read_excel(filename, '26', skiprows=6, index_col=[0]).ix[4:7]
    del fs['Einheit']
    fs = fs.transpose().rename(columns=fuels)

    # get unit conversion (uc) from sheet 0.2
    uc = pd.read_excel(filename, '0.2', skiprows=6, index_col=[0]).ix[:6]
    del uc['Unnamed: 1']
    del uc.index.name
    uc.set_index(uc.index.str.strip(), inplace=True)
    uc = uc.drop(uc.index[[0]])

    # convert the following columns to EUR / Joule using uc (unit conversion)
    fs['Oil'] = (fs['Oil'] /
                 uc.loc['1 Mio. t Rohöleinheit (RÖE)', 'PJ'] / 1.0e15 * 1.0e6)
    fs['Natural gas'] = fs['Natural gas'] / 1.0e+12
    fs['Hard coal'] = (fs['Hard coal'] /
                       uc.loc['1 Mio. t  Steinkohleeinheit (SKE)', 'PJ'] /
                       1.0e15 * 1.0e6)

    for col in fs.columns:
        src[col, 'costs'] = fs[col]

    return src


def emissions_from_znes(c, src):

    znes = pd.read_csv(os.path.join(c.paths['static'], c.files['znes_flens']),
                       skiprows=1, header=[0, 1], index_col=[0])
    znes['emission', 'value'] /= 1.0e+3  # gCO2 / J
    for fuel in znes.index:
        src[fuel, 'emission'] = znes.loc[fuel, ('emission', 'value')]
    return src


def prices_2014_from_znes(c, src, force_znes=False):
    znes = pd.read_csv(os.path.join(c.paths['static'], c.files['znes_flens']),
                       skiprows=1, header=[0, 1], index_col=[0])
    znes['fuel price', 'value'] /= 1.0e+9  # EUR / J
    for fuel in znes.index:
        if src.get((fuel, 'costs')) is None or force_znes:
            src.loc[2014, (fuel, 'costs')] = znes.loc[
                fuel, ('fuel price', 'value')]
    return src


def set_limit_by_energy_production(c, src):
    filename = os.path.join(c.paths['general'], c.files['bmwi_energiedaten'])
    t.download_file(filename, c.url['bmwi_energiedaten'])

    # get energy production from renewable source from sheet 20
    repp = pd.read_excel(filename, '20', skiprows=22).ix[:23]
    repp = repp.drop(repp.index[[0, 4, 8, 12, 16, 20]])
    repp['type'] = (['water'] * 3 + ['wind'] * 3 + ['Biomass and biogas'] * 3 +
                    ['biogenic waste'] * 3 + ['solar'] * 3 + ['geothermal'] * 3)
    repp['value'] = ['energy', 'capacity', 'fraction'] * 6
    repp.set_index(['type', 'value'], inplace=True)
    del repp['Unnamed: 0']
    repp = repp.transpose().sort_index(1)

    tpp = pd.read_csv(os.path.join(c.paths['powerplants'],
                                   c.files['transformer']),
                      index_col=[0, 1, 2])

    for fuel in tpp.index.get_level_values(0).unique():
        for year in src.index:
            try:
                df = tpp.loc[fuel, year]
                idx = df.efficiency.notnull()
                w_avg = np.average(df[idx].efficiency, weights=df[idx].capacity)
                limit = repp.loc[year, (fuel, 'energy')] / w_avg
                src.loc[year, (fuel, 'limit')] = limit
            except KeyError:
                src.loc[year, (fuel, 'limit')] = float('inf')
    return src


def prepare_commodity_sources(c):
    logging.info("Commodity Sources.")
    commodity_sources = initialise_commodity_sources()
    commodity_sources = prices_from_bmwi_energiedaten(cfg, commodity_sources)
    commodity_sources = emissions_from_znes(cfg, commodity_sources)
    commodity_sources = prices_2014_from_znes(cfg, commodity_sources)
    commodity_sources = set_limit_by_energy_production(cfg, commodity_sources)
    commodity_sources.sort_index(1, inplace=True)
    commodity_sources.to_csv(os.path.join(c.paths['commodity'],
                                          c.files['commodity_sources']))


if __name__ == "__main__":
    logger.define_logging()
    cfg = config.get_configuration()
    logging.info("Commodity Sources.")
    prepare_commodity_sources(cfg)
