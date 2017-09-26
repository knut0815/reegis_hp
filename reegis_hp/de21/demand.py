# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
from reegis_hp.de21 import time_series
import pandas as pd
import datetime
from oemof.tools import logger
from reegis_hp.de21 import config as cfg
from reegis_hp.de21 import tools
from reegis_hp.de21 import energy_balance

import demandlib.bdew as bdew
import demandlib.particular_profiles as profiles
from workalendar.europe import Germany


def renpass_demand_share():
    demand_share = os.path.join(cfg.get('paths', 'static'),
                                cfg.get('static_sources',
                                        'renpass_demand_share'))
    return pd.read_csv(
            demand_share, index_col='region_code', squeeze=True)


def openego_demand_share():
    demand_reg = prepare_ego_demand()['sector_consumption_sum']
    demand_sum = demand_reg.sum()
    return demand_reg.div(demand_sum)


def de21_profile_from_entsoe(year, share, annual_demand=None, overwrite=False):
    load_file = os.path.join(cfg.get('paths', 'time_series'),
                             cfg.get('time_series', 'load_file'))

    if not os.path.isfile(load_file) or overwrite:
        time_series.split_timeseries_file(overwrite)

    start = datetime.datetime(year, 1, 1, 0, 0)
    end = datetime.datetime(year, 12, 31, 23, 0)

    entsoe = pd.read_csv(load_file, index_col='utc_timestamp', parse_dates=True)
    entsoe = entsoe.tz_localize('UTC').tz_convert('Europe/Berlin')
    de_load_profile = entsoe.ix[start:end].DE_load_

    load_profile = pd.DataFrame(index=de_load_profile.index)
    for i in range(21):
        region = 'DE{:02.0f}'.format(i + 1)
        if region not in share:
            share[region] = 0
        load_profile[region] = de_load_profile.multiply(float(share[region]))

    if annual_demand is not None:
        load_profile = load_profile.div(load_profile.sum().sum()).multiply(
            annual_demand)
    return load_profile


def prepare_ego_demand(overwrite=False):
    egofile = os.path.join(cfg.get('paths', 'demand'),
                           cfg.get('demand', 'ego_file'))

    if os.path.isfile(egofile) and not overwrite:
        ego_demand = pd.read_csv(egofile, index_col=[0])
    else:
        # Read basic file (check oedb-API)
        load_file = os.path.join(cfg.get('paths', 'static'),
                                 cfg.get('demand', 'ego_input_file'))
        ego_demand = pd.read_csv(load_file, index_col=[0])

        # Create GeoDataFrame from DataFrame
        ego_demand_geo = tools.create_geo_df(ego_demand, wkt_column='st_astext')

        # Add column with region id
        ego_demand_geo = tools.add_spatial_name(
            ego_demand_geo,
            os.path.join(cfg.get('paths', 'geometry'),
                         cfg.get('geometry', 'region_polygons')),
            'region', 'ego_load')

        ego_demand['region'] = ego_demand_geo['region']
        del ego_demand['geom']
        ego_demand.to_csv(egofile)
    return ego_demand.groupby('region').sum()


def create_de21_slp_profile(year, outfile):
    demand_de21 = prepare_ego_demand()

    cal = Germany()
    holidays = dict(cal.holidays(year))

    de21_profile = pd.DataFrame()

    for region in demand_de21.index:
        annual_demand = demand_de21.loc[region]

        annual_electrical_demand_per_sector = {
            'g0': annual_demand.sector_consumption_retail,
            'h0': annual_demand.sector_consumption_residential,
            'l0': annual_demand.sector_consumption_agricultural,
            'i0': annual_demand.sector_consumption_industrial}
        e_slp = bdew.ElecSlp(year, holidays=holidays)

        elec_demand = e_slp.get_profile(annual_electrical_demand_per_sector)

        # Add the slp for the industrial group
        ilp = profiles.IndustrialLoadProfile(e_slp.date_time_index,
                                             holidays=holidays)

        elec_demand['i0'] = ilp.simple_profile(
            annual_electrical_demand_per_sector['i0'])

        de21_profile[region] = elec_demand.sum(1).resample('H').mean()
    de21_profile.to_csv(outfile)


def get_de21_slp_profile(year, annual_demand=None, overwrite=False):
    outfile = os.path.join(
        cfg.get('paths', 'demand'),
        cfg.get('demand', 'ego_profile_pattern').format(year=year))
    if not os.path.isfile(outfile) or overwrite:
        create_de21_slp_profile(year, outfile)

    de21_profile = pd.read_csv(
        outfile, index_col=[0], parse_dates=True).multiply(1000)

    if annual_demand is not None:
        de21_profile = de21_profile.div(de21_profile.sum().sum()).multiply(
            annual_demand)

    return de21_profile


def get_annual_demand_bmwi(year):
    """Returns the annual demand for the given year from the BMWI Energiedaten
    in Wh (Watthours). Will return None if data for the given year is not
    available.
    """
    infile = tools.get_bmwi_energiedaten_file()

    table = pd.read_excel(infile, '21', skiprows=7, index_col=[0])
    try:
        return table.loc['   zusammen', year] * 1e+12
    except KeyError:
        return None


def get_de21_profile(year, kind, annual_demand=None, overwrite=False):
    """

    Parameters
    ----------
    year : int
        The year of the profile. The year is passed to the chosen function. Make
        sure the function can handle the given year.
    kind : str
        Name of the method to create the profile
    annual_demand : float
        The annual demand for the profile. By default the original annual demand
        is used.
    overwrite :
        Be aware that some results are stored to speed up the calculations. Set
        overwrite to True or remove the stored files if you are not sure.

    Returns
    -------

    """
    # Use the openEgo proposal to calculate annual demand and standardised
    # load profiles to create profiles.
    if kind == 'openego':
        return get_de21_slp_profile(year, annual_demand, overwrite)

    # Use the renpass demand share values to divide the national entsoe profile
    # into 18 regional profiles.
    elif kind == 'renpass':
        return de21_profile_from_entsoe(year, renpass_demand_share(),
                                        annual_demand, overwrite)

    # Use the openEgo proposal to calculate the demand share values and use them
    # to divide the national entsoe profile.
    elif kind == 'openego_entsoe':
        return de21_profile_from_entsoe(year, openego_demand_share(),
                                        annual_demand, overwrite)

    else:
        logging.error('Method "{0}" not found.'.format(kind))


def test_elec_demand(year):
    oe = get_de21_profile(year, 'openego') * 1000000
    rp = get_de21_profile(year, 'renpass') * 1000000
    ege = get_de21_profile(year, 'openego_entsoe') * 1000000

    netto = get_annual_demand_bmwi(year)

    oe_s = get_de21_profile(year, 'openego', annual_demand=netto)
    rp_s = get_de21_profile(year, 'renpass', annual_demand=netto)
    ege_s = get_de21_profile(year, 'openego_entsoe', annual_demand=netto)

    print('[TWh] original    scaled (BMWI)')
    print(' oe:  ', int(oe.sum().sum() / 1e+12), '       ',
          int(oe_s.sum().sum() / 1e+12))
    print(' rp:  ', int(rp.sum().sum() / 1e+12), '       ',
          int(rp_s.sum().sum() / 1e+12))
    print('ege:  ', int(ege.sum().sum() / 1e+12), '       ',
          int(ege_s.sum().sum() / 1e+12))


def heat_demand(year):
    FUEL_GROUPS = {
        'hard coal (raw)': 'coal',
        'hard coal (brick)': 'coal',
        'hard coal (coke)': 'coal',
        'hard coal (other)': 'coal',
        'lignite (raw)': 'coal',
        'lignite (brick)': 'coal',
        'lignite (other)': 'coal',
        'oil (raw)': 'oil (raw)',
        'petroleum': 'petroleum',
        'gasoline': 'oil',
        'diesel': 'oil',
        'jet fuel': 'oil',
        'light heating oil': 'oil',
        'heavy heating oil': 'oil',
        'petroleum coke': 'oil',
        'mineral oil products': 'oil',
        'liquid gas': 'natural gas',
        'refinery gas': 'oil',
        'coke oven gas': 'gas',
        'furnace/converter gas': 'gas',
        'natural gas': 'natural gas',
        'mine gas': 'gas',
        'sewer/landfill gas': 're',
        'hydro power': 're',
        'wind power': 're',
        'solar power': 're',
        'biomass': 're',
        'biofuel': 're',
        'waste (biogen)': 're',
        'other renewable': 're',
        'electricity': 'electricity',
        'district heating': 'district heating',
        'waste (fossil)': 'other',
        'other': 'other',
        'total': 'total'}
    eb = energy_balance.get_states_balance(year)
    eb.sort_index(inplace=True)
    share = energy_balance.get_domestic_retail_share(year)
    share.fillna(0.5, inplace=True)

    check_value = True
    for state in eb.index.get_level_values(0).unique():
        tmp = eb.loc[state]
        tot = tmp.pop('total')
        # print(state, (tot - tmp.sum(1)).round())

        for col in eb.columns:
            check = (eb.loc[(state, 'domestic'), col] +
                     eb.loc[(state, 'retail'), col] -
                     eb.loc[(state, 'domestic and retail'), col]).round()
            if check < 0:
                for sector in ['domestic', 'retail']:
                    eb.loc[(state, sector), col] = (
                        eb.loc[(state, 'domestic and retail'), col] *
                        share.loc[col, sector])

                check = (eb.loc[(state, 'domestic'), col] +
                         eb.loc[(state, 'retail'), col] -
                         eb.loc[(state, 'domestic and retail')
                         , col]).round()

                if check < 0:
                    logging.error("In {0} the {1} sector results {2}".format(
                        state, col, check))
                    check_value = False
    if check_value:
        logging.info("Everything worked fine.")
    eb_new = eb.loc[(slice(None), ['industrial', 'domestic', 'retail',
                                   'transport', 'total', 'domestic and retail']), ]
    eb_new = eb_new.groupby(by=FUEL_GROUPS, axis=1).sum()
    for col in eb_new.columns:
        if not eb_new.loc[(slice(None), 'domestic and retail'), col].sum() > 0:
            del eb_new[col]
        # print(col)
    del eb_new['electricity']
    # del eb_new['gasoline']
    # del eb_new['diesel']
    # del eb_new['oil']
    # eb_new['electricity'] = eb_new['electricity'] - 1380
    dom_by_sector = eb_new.loc[(slice(None), 'domestic'), ].sum()
    retail_by_sector = eb_new.loc[(slice(None), 'retail'), ].sum()
    dr = eb_new.loc[(slice(None), 'domestic and retail'), ].sum()
    ind = eb_new.loc[(slice(None), 'industrial'), ].sum()
    print('dom', (dom_by_sector / dom_by_sector[:-1].sum() * 100).round(1))
    print('ret', (retail_by_sector / retail_by_sector[:-1].sum() * 100).round(1))
    print('dr', (dr / dr[:-1].sum() * 100).round(1))
    print('dr', dr / 1000)
    all = (dr + ind) / 1000
    # all['electricity'] = all['electricity'] - 1380
    print('all', all)
    print('all_sum', all.sum() - all.total)

    print("Jetzt bitte vergleichen, ob das in etwa hinhaut!!!")
    # print(dom_by_sector[:-1].sum(), dom_by_sector['total'])
    # print(retail_by_sector[:-1].sum(), retail_by_sector['total'])
    # print(dr[:-1].sum(), dr['total'])
    # print((dom_by_sector[:-1].sum() + retail_by_sector[:-1].sum()).round())
    # print(dom_by_sector['total'] + retail_by_sector['total'])

    # print((by_sector / by_sector['total'] * 100).round().apply(int))


if __name__ == "__main__":
    logger.define_logging()
    from reegis_hp.de21 import tools as t
    filename = t.get_bmwi_energiedaten_file()
    # fs = pd.read_excel(filename, '7', skiprows=6, index_col=[0]).ix[4:7]
    fs = pd.read_excel(filename, '7', skiprows=7)
    remove_list = ['1996 *)', 'Anteil am Endenergie-verbrauch 1996', 2008, 2009,
                   2010, 2011, 2012, 2014, 2015,
                   'Anteil am Endenergie-verbrauch 2015']
    for c in remove_list:
        del fs[c]
    fs['Unnamed: 0'] = fs['Unnamed: 0'].apply(str)
    fs['A'] = fs['Unnamed: 0'].apply(lambda x: x if '-' not in x else float('nan'))
    fs['B'] = fs['Unnamed: 0'].apply(lambda x: x if '-' in x else float('nan'))
    fs['A'] = fs['A'].fillna(method='ffill')
    del fs['Unnamed: 0']
    fs = fs.set_index(['A', 'B'], drop=True)
    # print(fs)
    print(fs.loc['mechanische Energie'])
    # print(fs.loc[' - davon Strom'])
    exit(0)
    heat_demand(2013)
    # test_elec_demand(2009)
