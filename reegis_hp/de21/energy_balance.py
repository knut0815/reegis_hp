# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
import pandas as pd
from oemof.tools import logger
from reegis_hp.de21 import config as cfg


COLUMN_TRANSLATION = {
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

FUEL_GROUPS = {
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
STATES = {
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

SUM_COLUMNS = {
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

SECTOR_SHORT = {
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


SECTOR_SHORT_EN = {
    'total': 'total',
    'industrial': 'ind',
    'transport': 'transp',
    'rail transport': 'train',
    'road transport': 'street',
    'air transport': 'air',
    'waterway transport': 'ship',
    'domestic and retail': 'hghd',
    'retail': 'ghd',
    'domestic': 'dom',
}


SECTOR = {
    'Insgesamt': 'total',
    'Gewinnung v. Steinen u. Erden, sonst. Bergbau und Verarb. Gewerbe':
        'industrial',
    'Verkehr (gesamt)': 'transport',
    'Schienenverkehr': 'rail transport',
    'Straßenverkehr': 'road transport',
    'Luftverkehr': 'air transport',
    'Küsten- und Binnenschifffahrt': 'waterway transport',
    'Haushalte, Gewerbe, Handel, Dienstl., übrige Verbraucher':
        'domestic and retail',
    'Endenergieverbrauch': 'total',
    'Gewerbe, Handel, Dienstleistungen und übrige Verbraucher': 'retail',
    'Gewinngung und verarbeitendes Gewerbe': 'industrial',
    'Haushalte': 'domestic',
    'Haushalte, Gewerbe, Handel, Dienstleistungen, übrige Verbraucher':
        'domestic and retail',
    'Küsten und Binnenschiffahrt': 'waterway transport',
    'Verkehr insgesamt': 'transport',
}


def check_balance(orig, ebfile):
    logging.info('Analyse the energy balances')

    years = [2012, 2013, 2014]
    # energy balance
    file_type = ebfile.split('.')[1]
    if file_type == 'xlsx' or file_type == 'xls':
        eb = pd.read_excel(ebfile, index_col=[0, 1, 2]).fillna(0)
    elif file_type == 'csv':
        eb = pd.read_csv(ebfile, index_col=[0, 1, 2]).fillna(0)
    else:
        logging.error('.{0} is an invalid suffix.'.format(file_type))
        logging.error('Cannot load {0}'.format(ebfile))
        eb = None
        exit(0)
    eb.rename(columns=COLUMN_TRANSLATION, inplace=True)
    eb.sort_index(0, inplace=True)
    eb = eb.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)
    eb = eb.groupby(by=FUEL_GROUPS, axis=1).sum()

    # sum table (fuel)
    ftfile = os.path.join(cfg.get('paths', 'static'),
                          'sum_table_fuel_groups.xlsx')
    ft = pd.read_excel(ftfile)
    ft['Bundesland'] = ft['Bundesland'].apply(lambda x: STATES[x])
    ft.set_index(['Jahr', 'Bundesland'], inplace=True)
    ft.rename(columns=SUM_COLUMNS, inplace=True)
    ft.sort_index(inplace=True)

    # sum table (sector)
    stfile = os.path.join(cfg.get('paths', 'static'),
                          'sum_table_sectors.xlsx')

    st = pd.read_excel(stfile)
    st['Bundesland'] = st['Bundesland'].apply(lambda x: STATES[x])
    st.set_index(['Jahr', 'Bundesland'], inplace=True)
    st.rename(columns=SECTOR_SHORT, inplace=True)
    st.sort_index(inplace=True)
    del st['Anm.']

    if orig:
        outfile = os.path.join(cfg.get('paths', 'messages'),
                               'energy_balance_check_original.xlsx')
    else:
        outfile = os.path.join(cfg.get('paths', 'messages'),
                               'energy_balance_check_edited.xlsx')

    writer = pd.ExcelWriter(outfile)

    for year in years:
        # Compare sum of fuel groups with LAK-table
        endenergie_check = pd.DataFrame()
        for col in ft.columns:
            ft_piece = ft.loc[(year, slice(None)), col]
            ft_piece.index = ft_piece.index.droplevel([0])
            ft_piece = ft_piece.apply(lambda x: pd.to_numeric(x,
                                                              errors='coerce'))
            try:
                eb_piece = eb.loc[(year, slice(None), 'Endenergieverbrauch'),
                                  col]
            except KeyError:
                eb_piece = eb.loc[(year, slice(None), 'total'), col]
            eb_piece.index = eb_piece.index.droplevel([0, 2])
            endenergie_check[col] = ft_piece-eb_piece.round()

        endenergie_check['check'] = (endenergie_check.sum(1) -
                                     2 * endenergie_check['total'])
        endenergie_check.loc['all'] = endenergie_check.sum()
        endenergie_check.to_excel(writer, 'fuel_groups_{0}'.format(year),
                                  freeze_panes=(1, 1))

        # Compare subtotal of transport, industrial and domestic and retail with
        # the total of end-energy
        endenergie_summe = pd.DataFrame()

        if orig:
            main_cat = [
                'Haushalte, Gewerbe, Handel, Dienstleistungen,'
                ' übrige Verbraucher', 'Verkehr insgesamt',
                'Gewinngung und verarbeitendes Gewerbe']
            total = 'Endenergieverbrauch'
        else:
            main_cat = [
                    'domestic and retail', 'transport',
                    'industrial']
            total = 'total'
        for state in eb.index.get_level_values(1).unique():
            try:
                tmp = pd.DataFrame()
                n = 0
                for idx in main_cat:
                    n += 1
                    tmp[state, n] = eb.loc[year, state, idx]
                tmp = (tmp.sum(1) - eb.loc[year, state, total]
                       ).round()

                endenergie_summe[state] = tmp
            except KeyError:
                endenergie_summe[state] = None
        endenergie_summe.transpose().to_excel(
            writer, 'internal sum check {0}'.format(year), freeze_panes=(1, 1))

        # Compare sum of sector groups with LAK-table
        eb_fuel = (eb[['hard coal',  'lignite',  'oil',  'gas', 're',
                       'electricity', 'district heating', 'other']])

        eb_fuel = eb_fuel.sum(1)
        eb_sector = eb_fuel.round().unstack()
        eb_sector.rename(columns=SECTOR_SHORT, inplace=True)
        eb_sector.rename(columns=SECTOR_SHORT_EN, inplace=True)
        try:
            del eb_sector['ghd']
            del eb_sector['dom']
        except KeyError:
            del eb_sector['retail']
            del eb_sector['domestic']
        eb_sector = eb_sector.sort_index(1).loc[year]

        st_year = st.sort_index(1).loc[year]
        st_year.index = st_year.index
        st_year = st_year.apply(
            lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)
        (eb_sector.astype(int) - st_year.astype(int)).to_excel(
            writer, 'sector_groups_{0}'.format(year), freeze_panes=(1, 1))

        # Compare the sum of the columns with the "total" column.
        sum_check_hrz = pd.DataFrame()
        for row in eb.index.get_level_values(2).unique():
            eb.sort_index(0, inplace=True)
            summe = (eb.loc[(year, slice(None), row)]).sum(1)
            ges = (eb.loc[(year, slice(None), row), 'total'])

            tmp_check = round(summe - 2 * ges)
            tmp_check.index = tmp_check.index.droplevel(0)
            tmp_check.index = tmp_check.index.droplevel(1)
            sum_check_hrz[row] = tmp_check
        sum_check_hrz.to_excel(
                writer, 'sum_check_hrz_{0}'.format(year), freeze_panes=(1, 1))

        # Check states
        for state, abr in STATES.items():
            if abr not in eb.loc[year].index.get_level_values(0).unique():
                logging.warning(
                    '{0} ({1}) not present in the {2} balance.'.format(
                        state, abr, year))

    writer.save()


def edit_balance():
    """Fixes the energy balances after analysing them. This is done manually."""

    # Read energy balance table
    ebfile = os.path.join(cfg.get('paths', 'static'),
                          cfg.get('general_sources', 'energiebilanzen_laender'))
    eb = pd.read_excel(ebfile, index_col=[0, 1, 2]).fillna(0)
    eb.rename(columns=COLUMN_TRANSLATION, inplace=True)
    eb.sort_index(0, inplace=True)
    eb = eb.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)

    new_index_values = list()
    for value in eb.index.get_level_values(2):
        new_index_values.append(SECTOR[value])
    eb.index.set_levels(new_index_values, level=2, inplace=True)

    # ************************************************************************
    # Bavaria (Bayern) - Missing coal values
    # Difference between fuel sum and LAK table
    missing = {2012: 10529, 2013: 8995}
    for y in [2012, 2013]:
        fix = missing[y]
        # the missing value is added to 'hard coal raw' even though it is not
        # specified which hard coal product is missing.
        eb.loc[(y, 'BY', 'total'), 'hard coal (raw)'] = fix

        # There is a small amount specified in the 'domestic and retail' sector.
        dom_retail = eb.loc[(y, 'BY', 'domestic and retail'), 'hard coal (raw)']

        # The rest of the total hard coal consumption comes from the industrial
        # sector.
        eb.loc[(y, 'BY', 'industrial'), 'hard coal (raw)'] = fix - dom_retail

    # ************************************************************************
    # Berlin (Berlin) - corrected values for domestic gas and electricity
    # In new publications (e.g. LAK table) these values have changed. The newer
    # values will be used.
    electricity = {2012: 9150, 2013: 7095}
    gas = {2012: -27883, 2013: -13317}
    total = {2012: -18733, 2013: -6223}
    for row in ['total', 'domestic and retail']:
        for y in [2012, 2013]:
            eb.loc[(y, 'BE', row), 'electricity'] += electricity[y]
            eb.loc[(y, 'BE', row), 'natural gas'] += gas[y]
            eb.loc[(y, 'BE', row), 'total'] += total[y]

    # ************************************************************************
    # Saxony-Anhalt (Sachsen Anhalt) - missing values for hard coal, oil and
    # other depending on the year. Due to a lack of information the difference
    # will be halved between the sectors.
    missing = {2012: 5233, 2013: 4396, 2014: 3048}

    y = 2012
    fix = missing[y]
    # the missing value is added to 'hard coal raw' even though it is not
    # specified which hard coal product is missing.
    eb.loc[(y, 'ST', 'industrial'), 'waste (fossil)'] += fix / 2
    eb.loc[(y, 'ST', 'industrial'), 'hard coal (raw)'] += fix / 2

    # There is a small amount specified in the 'domestic and retail' sector.
    dom_retail_hc = eb.loc[(y, 'ST', 'domestic and retail'), 'hard coal (raw)']

    # The rest of the total hard coal consumption comes from the industrial
    # sector.
    eb.loc[(y, 'ST', 'total'), 'waste (fossil)'] += fix / 2
    eb.loc[(y, 'ST', 'total'), 'hard coal (raw)'] += fix / 2 + dom_retail_hc

    y = 2013
    fix = missing[y]
    # the missing value is added to 'hard coal raw' even though it is not
    # specified which hard coal product is missing.
    eb.loc[(y, 'ST', 'industrial'), 'mineral oil products'] += fix / 2
    eb.loc[(y, 'ST', 'industrial'), 'hard coal (raw)'] += fix / 2

    # There is a small amount specified in the 'domestic and retail' sector.
    dom_retail_hc = eb.loc[(y, 'ST', 'domestic and retail'), 'hard coal (raw)']
    dom_retail_oil = eb.loc[(y, 'ST', 'domestic and retail'),
                            'mineral oil products']
    # The rest of the total hard coal consumption comes from the industrial
    # sector.
    eb.loc[(y, 'ST', 'total'), 'mineral oil products'] += fix / 2 + (
        dom_retail_oil)
    eb.loc[(y, 'ST', 'total'), 'hard coal (raw)'] += fix / 2 + dom_retail_hc

    y = 2014
    fix = missing[y]
    # the missing value is added to 'hard coal raw' even though it is not
    # specified which hard coal product is missing.
    eb.loc[(y, 'ST', 'industrial'), 'mineral oil products'] += fix / 2
    eb.loc[(y, 'ST', 'industrial'), 'hard coal (coke)'] += fix / 2

    # There is a small amount specified in the 'domestic and retail' sector.
    dom_retail = eb.loc[(y, 'ST', 'domestic and retail'),
                        'mineral oil products']

    # The rest of the total hard coal consumption comes from the industrial
    # sector.
    eb.loc[(y, 'ST', 'total'), 'mineral oil products'] += fix / 2 + dom_retail
    eb.loc[(y, 'ST', 'total'), 'hard coal (coke)'] += fix / 2

    # ************************************************************************
    # Write results to table
    fname = os.path.join(cfg.get('paths', 'demand'),
                         cfg.get('energy_balance', 'energy_balance_edited'))
    eb.to_csv(fname)
    return fname


def get_grouped_de_balance(year=None):
    fname_de = os.path.join(
        cfg.get('paths', 'static'),
        cfg.get('energy_balance', 'energy_balance_de_original'))
    deb = pd.read_excel(fname_de, index_col=[0, 1, 2]).fillna(0)
    deb.rename(columns=COLUMN_TRANSLATION, inplace=True)
    deb.sort_index(0, inplace=True)
    deb = deb.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)

    new_index_values = list()
    for value in deb.index.get_level_values(2):
        new_index_values.append(SECTOR[value])
    deb.index.set_levels(new_index_values, level=2, inplace=True)

    deb_grp = deb.groupby(by=FUEL_GROUPS, axis=1).sum()
    deb_grp.index = deb_grp.index.set_names(['year', 'state', 'sector'])
    deb_grp.sort_index(0, inplace=True)
    if year is not None:
        deb_grp = deb_grp.loc[year]
    return deb_grp


def get_domestic_retail_share(year):
    deb_grp = get_grouped_de_balance(year=year)
    deb_grp.sort_index(1, inplace=True)

    deb_grp = deb_grp.groupby(level=[1]).sum()

    share = pd.DataFrame()
    share['domestic'] = (deb_grp.loc['domestic'] /
                         deb_grp.loc['domestic and retail']
                         ).round(2)
    share['retail'] = (deb_grp.loc['retail'] /
                       deb_grp.loc['domestic and retail']).round(2).transpose()
    return share


def get_grouped_balance(year=None):
    fname = os.path.join(cfg.get('paths', 'demand'),
                         cfg.get('energy_balance', 'energy_balance_edited'))
    if not os.path.isfile(fname):
        edit_balance()
    eb = pd.read_csv(fname, index_col=[0, 1, 2])
    eb_grp = eb.groupby(by=FUEL_GROUPS, axis=1).sum()
    eb_grp.index = eb_grp.index.set_names(['year', 'state', 'sector'])

    if year is not None:
        eb_grp = eb_grp.loc[year]

    return eb_grp


if __name__ == "__main__":
    logger.define_logging()
    # fn = os.path.join(cfg.get('paths', 'static'),
    #                   cfg.get('general_sources', 'energiebilanzen_laender'))
    # check_balance(orig=True, ebfile=fn)
    # fn = fix_balance()
    # check_balance(orig=False, ebfile=fn)
    print(get_grouped_balance(2013))
    print(get_domestic_retail_share(2013))
