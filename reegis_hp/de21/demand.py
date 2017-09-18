# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
from reegis_hp.de21 import time_series
import pandas as pd
import datetime
from oemof.tools import logger
from reegis_hp.de21 import config as cfg
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


def heat_demand():
    column_translation = {
        'Steinkohle (roh)': 'hard coal (raw)',
        'Steinkohle (Briketts)': 'hard coal (brick)',
        'Steinkohle (Koks)': 'hard coal (coke)',
        'Steinkohle (sonstige)': 'hard coal (other)',
        'Braunkohle (roh)': 'lignite (raw)',
        'Braunkohle (Briketts)': 'lignite (brick)',
        'Braunkohle (sonstige)': 'lignite (other)',
        'Erdöl': 'oil (raw)',
        'Rohbenzin': 'petroleum',
        'Ottokraftstoffe': 'gasoline',
        'Dieselkraftstoffe': 'diesel',
        'Flugturbinenkraftstoffe': 'jet fuel',
        'Heizöl (leicht)': 'light heating oil',
        'Heizöl (schwer)': 'heavy heating oil',
        'Petrolkoks': 'petroleum coke',
        'Mineralölprodukte (sonstige)': 'mineral oil products',
        'Flüssiggas': 'liquid gas',
        'Raffineriegas': 'refinery gas',
        'Kokereigas, Stadtgas': 'coke oven gas',
        'Gichtgas, Konvertergas': 'furnace/converter gas',
        'Erdgas': 'natural gas',
        'Grubengas': 'mine gas',
        'Klärgas, Deponiegas': 'sewer/landfill gas',
        'Wasserkraft': 'hydro power',
        'Windkraft': 'wind power',
        'Solarenergie': 'solar power',
        'Biomasse': 'biomass',
        'Biotreibstoff': 'biofuel',
        'Abfälle (biogen)': 'waste (biogen)',
        'EE (sonstige)': 'other renewable',
        'Strom': 'electricity',
        'Kernenergie': 'nuclear energy',
        'Fernwärme': 'district heating',
        'Abfälle (nicht biogen)': 'waste (fossil)',
        'andere Energieträger': 'other',
        'Insgesamt': 'total'}

    fuel_groups = {
        'hard coal (raw)': 'hard coal',
        'hard coal (brick)': 'hard coal',
        'hard coal (coke)': 'hard coal',
        'hard coal (other)': 'hard coal',
        'lignite (raw)': 'lignite',
        'lignite (brick)': 'lignite',
        'lignite (other)': 'lignite',
        'oil (raw)': 'oil',
        'petroleum': 'oil',
        'gasoline': 'oil',
        'diesel': 'oil',
        'jet fuel': 'oil',
        'light heating oil': 'oil',
        'heavy heating oil': 'oil',
        'petroleum coke': 'oil',
        'mineral oil products': 'oil',
        'liquid gas': 'oil',
        'refinery gas': 'oil',
        'coke oven gas': 'gas',
        'furnace/converter gas': 'gas',
        'natural gas': 'gas',
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
        'total': 'total'
    }
    states = {
        'Baden-Württemberg': 'BW',
        'Bayern': 'BY',
        'Berlin': 'BE',
        'Brandenburg': 'BB',
        'Bremen': 'HB',
        'Hamburg': 'HH',
        'Hessen': 'HE',
        'Mecklenburg-Vorpommern': 'MV',
        'Niedersachsen': 'NI',
        'Nordrhein-Westfalen': 'NW',
        'Rheinland-Pfalz': 'RP',
        'Saarland': 'SL',
        'Sachsen': 'SN',
        'Sachsen-Anhalt': 'ST',
        'Schleswig-Holstein': 'SH',
        'Thüringen': 'TH',
        }

    sum_columns = {
        'Insgesamt': 'total',
        'Steinkohle': 'hard coal',
        'Braunkohle': 'lignite',
        'Mineralöle und Mineralölprodukte': 'oil',
        'Gase': 'gas',
        'Erneuerbare Energieträger': 're',
        'Strom': 'electricity',
        'Fernwärme': 'district heating',
        'andere Energieträger': 'other',
    }

    sector_columns = {
        'Insgesamt': 'total',
        'Gewinnung v. Steinen u. Erden, sonst. Bergbau und Verarb. Gewerbe':
            'ind',
        'Verkehr (gesamt)': 'transp',
        'Schienenverkehr': 'train',
        'Straßenverkehr': 'street',
        'Luftverkehr': 'air',
        'Küsten- und Binnenschifffahrt': 'ship',
        'Haushalte, Gewerbe, Handel, Dienstl., übrige Verbraucher': 'hghd',
        'Endenergieverbrauch': 'total',
        'Gewerbe, Handel, Dienstleistungen und übrige Verbraucher': 'ghd',
        'Gewinngung und verarbeitendes Gewerbe': 'ind',
        'Haushalte': 'dom',
        'Haushalte, Gewerbe, Handel, Dienstleistungen, übrige Verbraucher':
            'hghd',
        'Küsten und Binnenschiffahrt': 'ship',
        'Verkehr insgesamt': 'transp',
    }

    year = 2013
    # energy balance
    ebfile = os.path.join(cfg.get('paths', 'static'),
                          cfg.get('general_sources', 'energiebilanzen_laender'))
    eb = pd.read_excel(ebfile, index_col=[0, 1, 2]).fillna(0)
    eb.rename(columns=column_translation, inplace=True)
    eb.sort_index(0, inplace=True)
    eb = eb.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)
    eb = eb.groupby(by=fuel_groups, axis=1).sum()

    # sum table (fuel)
    ftfile = os.path.join(cfg.get('paths', 'static'),
                          'sum_table_fuel_groups.xlsx')
    ft = pd.read_excel(ftfile)
    ft['Bundesland'] = ft['Bundesland'].apply(lambda x: states[x])
    ft.set_index(['Jahr', 'Bundesland'], inplace=True)
    ft.rename(columns=sum_columns, inplace=True)
    ft.sort_index(inplace=True)

    # sum table (sector)
    stfile = os.path.join(cfg.get('paths', 'static'),
                          'sum_table_sectors.xlsx')

    st = pd.read_excel(stfile)
    st['Bundesland'] = st['Bundesland'].apply(lambda x: states[x])
    st.set_index(['Jahr', 'Bundesland'], inplace=True)
    st.rename(columns=sector_columns, inplace=True)
    st.sort_index(inplace=True)
    del st['Anm.']

    # Comparing
    endenergie_check = pd.DataFrame()
    for col in ft.columns:
        ft_piece = ft.loc[(year, slice(None)), col]
        ft_piece.index = ft_piece.index.droplevel([0])
        ft_piece = ft_piece.apply(lambda x: pd.to_numeric(x, errors='coerce'))
        eb_piece = eb.loc[(year, slice(None), 'Endenergieverbrauch'), col]
        eb_piece.index = eb_piece.index.droplevel([0, 2])
        endenergie_check[col] = ft_piece-eb_piece.round()

    writer = pd.ExcelWriter('/home/uwe/output.xlsx')
    endenergie_check.to_excel(writer, 'tester1')
    endenergie_check.sum().to_excel(writer, 'tester2')
    print(endenergie_check.sum(1))
    print(endenergie_check.sum().sum())
    writer.save()
    exit(0)
    endenergie_summe = pd.DataFrame()

    for state in eb.index.get_level_values(1).unique():
        tmp = pd.DataFrame()
        n = 0
        main_cat = [
            'Haushalte, Gewerbe, Handel, Dienstleistungen, übrige Verbraucher',
            'Verkehr insgesamt',
            'Gewinngung und verarbeitendes Gewerbe']
        for idx in main_cat:
            n += 1
            tmp[state, n] = eb.loc[year, state, idx]
        tmp = (tmp.sum(1) - eb.loc[year, state, 'Endenergieverbrauch']).round()

        endenergie_summe[state] = tmp
    print(endenergie_summe)
    exit(0)
    eb_fuel = (eb[['hard coal',  'lignite',  'oil',  'gas', 're', 'electricity',
                   'district heating', 'other']])

    eb_fuel = eb_fuel.sum(1)
    print((eb_fuel - eb['total']).round().unstack())
    # eb_sectoreb_fuel.unstack())
    # exit(0)
    eb_sector = eb_fuel.round().unstack()
    eb_sector.rename(columns=sector_columns, inplace=True)
    del eb_sector['ghd']
    del eb_sector['dom']
    eb_sector = eb_sector.sort_index(1).loc[2012:2013]
    st = st.sort_index(1).loc[2012:2013]
    st.index = eb_sector.index
    st = st.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)
    print(eb_sector.astype(int) - st.astype(int))
    # print(st)

    # for row in eb.index.get_level_values(2).unique():
    #     eb.sort_index(0, inplace=True)
    #     summe = (eb.loc[(year, slice(None), row)]).sum(1)
    #     ges = (eb.loc[(year, slice(None), row), ('Insgesamt')])
    #     # print(round(summe - 2 * ges))

    # print(eb.columns)

    # print(eb_grp.columns)
    # print(eb_grp.loc[2014, :, 'Endenergieverbrauch']['hard coal'])
    # exit(0)
    # eb_grp.loc[year, :, 'Endenergieverbrauch'].to_excel('/home/uwe/test.xls')


if __name__ == "__main__":
    logger.define_logging()
    heat_demand()
    # test_elec_demand(2009)
