# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
import time_series
import pandas as pd
import datetime
# from oemof.tools import logger
import config as cfg
from reegis_hp.de21 import tools
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

    entsoe = pd.read_csv(load_file, index_col='cet', parse_dates=True)
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


if __name__ == "__main__":
    my_year = 2011
    oe = get_de21_profile(my_year, 'openego')
    rp = get_de21_profile(my_year, 'renpass')
    ege = get_de21_profile(my_year, 'openego_entsoe')

    netto2014 = 511500000  # kWh
    oe_s = get_de21_profile(my_year, 'openego', annual_demand=netto2014)
    rp_s = get_de21_profile(my_year, 'renpass', annual_demand=netto2014)
    ege_s = get_de21_profile(my_year, 'openego_entsoe', annual_demand=netto2014)

    print('[kWh] original    scaled')
    print(' oe:', round(oe.sum().sum()), oe_s.sum().sum())
    print(' rp:', round(rp.sum().sum()), rp_s.sum().sum())
    print('ege:', round(ege.sum().sum()), ege_s.sum().sum())
