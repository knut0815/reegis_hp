
import os
import pprint
import pandas as pd
import configuration as config


def check_fraction(dic):
    """pass"""
    s = round(sum(dic.values()), 15)
    if s != 1:
        fdict = pprint.pformat(dic)
        raise ValueError('The sum of the values does not equal one. ' +
                         'Got {0} instead. \n {1}'.format(s, fdict))


def create_subdict_from_config_dict(conf, names):
    dc = {name: conf[name] for name in names}
    check_fraction(dc)
    return dc


def initialise_scenario():
    c = config.get_configuration('scenario')

    subpath = os.path.join(c.paths['scenario_data'],
                           c.general['name']).replace(' ', '_').lower()
    if not os.path.isdir(subpath):
        os.mkdir(subpath)
    return c


def prepare_capacities(c):
    # read renewable powerplants data
    re2conv = {
        'Biomass and biogas': 'Bioenergy',
        'Other fossil fuels': 'Other fossil fuels'}

    transformers = ['Biomass and biogas', 'Hard coal', 'Lignite', 'Natural gas',
                    'Nuclear', 'Oil', 'Other fossil fuels', 'Waste']

    sources = ['Geothermal', 'Hydro', 'Solar', 'Wind']

    pp = pd.read_csv(os.path.join(c.paths['renewable'],
                                  c.pattern['grouped'].format(cat='renewable')),
                     index_col=[0, 1, 2, 3])
    print(pp.index.get_level_values(0).unique())
    # prepare one year (rows: regions, columns: types)
    my_index = pp.index.get_level_values(2).unique()
    powerplants_renewable = pd.DataFrame(index=my_index)
    for pptype in pp.index.levels[0]:
        powerplants_renewable[pptype] = (
            pp.loc[pptype, c.general['year']].groupby(level=0).sum())

    # read conventional powerplants data
    pp = pd.read_csv(
        os.path.join(
            c.paths['conventional'],
            c.pattern['grouped'].format(cat='conventional')),
        index_col=[0, 1, 2])
    print(pp.index.get_level_values(0).unique())
    # prepare one year (rows: regions, columns: (types, (capacity, efficiency)))
    my_index = pp.index.get_level_values(2).unique()
    my_cols = pd.MultiIndex(levels=[[], []], labels=[[], []],
                            names=['fuel', 'value'])
    powerplants_conventional = pd.DataFrame(index=my_index, columns=my_cols)
    for fuel in pp.index.get_level_values(0).unique():
        for col in pp.columns:
            powerplants_conventional[fuel, col] = (
                pp.loc[fuel, c.general['year']][col])

    # fill gaps of efficiency columns with mean value
    for fuel in pp.index.get_level_values(0).unique():
        sum_out = powerplants_conventional[fuel, 'capacity'].sum()
        sum_in = powerplants_conventional[fuel, 'capacity'].div(
            powerplants_conventional[fuel, 'efficiency']).sum()
        mean_eff = sum_out / sum_in
        powerplants_conventional[fuel, 'efficiency'].fillna(mean_eff,
                                                            inplace=True)

    # sort DataFrames and fill nan-values (capacity) with 0
    powerplants_conventional.sort_index(inplace=True)
    powerplants_renewable.sort_index(inplace=True)
    powerplants_conventional.fillna(0, inplace=True)
    powerplants_renewable.fillna(0, inplace=True)

    # add renewable data (transformer) to conventional data
    for fuel, pptype in re2conv.items():
        powerplants_conventional[fuel, 'capacity'] += (
            powerplants_renewable[pptype])

    powerplants_conventional[transformers].to_csv(
        os.path.join(c.paths['scenario_data'],
                     c.general['name'].replace(' ', '_').lower(),
                     'transformer.csv'))

    # add conventional data (sources) to renewable data: Hydro
    powerplants_renewable['Hydro'] += powerplants_conventional[
        'Hydro', 'capacity']

    powerplants_renewable[sources].to_csv(
        os.path.join(c.paths['scenario_data'],
                     c.general['name'].replace(' ', '_').lower(),
                     'sources_capacity.csv'))


def model_sources(c):
    subpath = os.path.join(c.paths['scenario_data'],
                           c.general['name']).replace(' ', '_').lower()
    if not os.path.isdir(subpath):
        os.mkdir(subpath)

    # read renewable powerplants
    pp = pd.read_csv(os.path.join(c.paths['renewable'],
                                  c.pattern['grouped'].format(cat='renewable')),
                     index_col=[0, 1, 2, 3])

    # Store renewable powerplants
    my_index = pp.loc['Wind', c.general['year']].groupby(level=0).sum().index
    powerplants_renewable = pd.DataFrame(index=my_index)
    for pptype in pp.index.levels[0]:
        powerplants_renewable[pptype] = (
            pp.loc[pptype, c.general['year']].groupby(level=0).sum())
    powerplants_renewable.to_csv(os.path.join(subpath,
                                              c.files['renewable_capacities']))

    # read wind feedin time series (feedin_wind)
    feedin_wind = pd.read_csv(
        os.path.join(c.paths['feedin'], 'wind', 'de21',
                     c.pattern['feedin_de21'].format(year=c.general['year'],
                                                     type='wind')),
        index_col=0, header=[0, 1])
    feedin = feedin_wind.columns.set_levels(['wind'], level=1, inplace=True)

    # read solar feedin time series (feedin_solar)
    feedin_solar = pd.read_csv(
        os.path.join(
            c.paths['feedin'], 'solar', 'de21',
            c.pattern['feedin_de21'].format(year=c.general['year'],
                                            type='solar')),
        index_col=0, header=[0, 1, 2], parse_dates=True)

    module_inverter_sets = create_subdict_from_config_dict(
        c.pv, c.pv['module_inverter_types'])
    orientation_sets = create_subdict_from_config_dict(
        c.pv, c.pv['orientation_types'])

    orientation_fraction = pd.Series(orientation_sets)

    feedin_solar.sort_index(1, inplace=True)
    orientation_fraction.sort_index(inplace=True)

    # print(orientation_fraction)
    print(feedin_solar['DE01', 'M_STP280S__I_GEPVb_5000_NA_240'].multiply(
        orientation_fraction))

    exit(0)
    solar = pd.DataFrame(index=feedin_solar.index)
    for reg in feedin_solar.columns.levels[0]:
        solar[reg] = 0
        for set in module_inverter_sets.keys():
            for subset in orientation_sets.keys():
                if reg in powerplants_renewable.index:
                    solar[reg] += feedin_solar[reg, set, subset].multiply(
                        powerplants_renewable.loc[reg, 'Solar']).multiply(
                            set_name[set] * orientation[subset])
    solar = solar.sum(1)
    solar.to_csv(os.path.join(c.paths['analysis'], 'solar_de.csv'))

    re_file = os.path.join(c.paths['time_series'],
                           c.files['renewables_time_series'])

    start = datetime.datetime(year, 1, 1, 0, 0)
    end = datetime.datetime(year, 12, 31, 23, 0)

    ts = pd.read_csv(re_file, index_col='cet', parse_dates=True).loc[start:end]
    print(ts['DE_solar_generation'].sum())
    print(solar[:8760].sum())
    print((solar[:8760].sum()) / (34.93 * 1000000))
    new = pd.DataFrame()
    new['own'] = solar[:8760]
    new['other'] = ts['DE_solar_generation']
    new.plot()

    plt.show()
    print('Done')


if __name__ == "__main__":
    cfg = initialise_scenario()
    prepare_capacities(cfg)
    model_sources(cfg)
