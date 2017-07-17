__copyright__ = "Uwe Krien"
__license__ = "GPLv3"


import pandas as pd
# import geopandas as gpd
import config as cfg
import configuration as config
import logging
import os
import feedin as f
import pvlib
import datetime
import oemof.tools.logger as logger
from matplotlib import pyplot as plt
# import plots


def get_full_load_hours():
    """pass"""
    c = config.get_configuration()
    feedinpath = os.path.join(c.paths['feedin'], '{type}', c.pattern['feedin'])

    my_idx = pd.MultiIndex(levels=[[], []], labels=[[], []],
                           names=['year', 'key'])
    df = pd.DataFrame(index=my_idx, columns=['wind'])

    years = list()
    for vtype in ['solar', 'wind']:
        for year in range(1970, 2020):
            if os.path.isfile(feedinpath.format(year=year, type=vtype.lower())):
                years.append(year)
    years = list(set(years))

    # opening one file to get the keys of the weather fields and the columns of
    # the solar file (the columns represent the sets).
    file = pd.HDFStore(feedinpath.format(year=years[0], type='solar'))
    keys = file.keys()
    columns = list(file[keys[0]].columns)
    for col in columns:
        df[col] = ''
    file.close()

    for key in keys:
        df.loc[(0, int(key[2:])), :] = 0
    df.loc[(0, 0), :] = 0

    for year in years:
        df.loc[(year, 0), :] = 0
        logging.info("Processing: {0}".format(year))
        solar = pd.HDFStore(feedinpath.format(year=year, type='solar'))
        wind = pd.HDFStore(feedinpath.format(year=year, type='wind'))
        for key in keys:
            skey = int(key[2:])
            df.loc[(year, skey), 'wind'] = wind[key].sum()
            df.loc[(0, skey), 'wind'] += df.loc[(year, skey), 'wind']
            df.loc[(year, 0), 'wind'] += df.loc[(year, skey), 'wind']
            df.loc[(0, 0), 'wind'] += df.loc[(year, skey), 'wind']

            df.loc[(year, skey), columns] = solar[key].sum()
            df.loc[(0, skey), columns] += df.loc[(year, skey), columns]
            df.loc[(year, 0), columns] += df.loc[(year, skey), columns]
            df.loc[(0, 0), columns] += df.loc[(year, skey), columns]
        solar.close()
        wind.close()
        df.loc[(year, 0), :] = (df.loc[(year, 0), :] / len(keys))

    for key in keys:
        df.loc[(0, int(key[2:])), :] = df.loc[(0, int(key[2:])), :] / len(years)
    df.loc[(0, 0), :] = df.loc[(0, 0), :] / (len(years) * len(keys))
    df.sort_index(inplace=True)
    df.to_csv(os.path.join(c.paths['analysis'], 'full_load_hours.csv'))


def analyse_pv_types(year, key, orientation):
    c = config.get_configuration()
    weatherpath = os.path.join(c.paths['weather'], c.pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(c.paths['geometry'],
                                      c.files['grid_centroid']),
                         index_col='gid').loc[key]
    location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}

    weather = f.adapt_weather_to_pvlib(weather, location)

    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    invertername = 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_'
    for modu in sandia_modules.keys():
        if 'BP_Solar' in modu:
            print(modu)
    exit(0)
    df_ts_ac = pd.DataFrame()
    df = pd.DataFrame()
    length = len(sandia_modules.keys())
    for smod in sandia_modules.keys():
        name = smod  # .replace('__', '_')
        logging.info("{0}, {1}".format(name, length))
        length -= 1
        smodule = {
            'module_parameters': sandia_modules[smod],
            'inverter_parameters': sapm_inverters[invertername],
            'surface_azimuth': orientation['azimuth'],
            'surface_tilt': orientation['tilt'],
            'albedo': 0.2}
        p_peak = (
            smodule['module_parameters'].Impo *
            smodule['module_parameters'].Vmpo)

        mc = f.feedin_pvlib_modelchain(location, smodule, weather)
        df_ts_ac[name] = mc.ac.clip(0).fillna(0).div(p_peak)
        df.loc[name, 'ac'] = df_ts_ac[name][:8760].sum()
        df.loc[name, 'dc_norm'] = mc.dc.p_mp.clip(0).div(p_peak).sum()
        df.loc[name, 'dc'] = mc.dc.p_mp.clip(0).sum()
    df.to_csv(os.path.join(c.paths['analysis'], 'module_feedin.csv'))
    df_ts_ac.to_csv(os.path.join(c.paths['analysis'],
                                 'module_feedin_ac_ts.csv'))


def analyse_performance_ratio(year, key):
    c = config.get_configuration()
    sets = dict()
    set_ids = ['solar_set1', 'solar_set2', 'solar_set3', 'solar_set4']
    sets['system'] = list()
    for s in set_ids:
        m = cfg.get(s, 'module_name')
        i = cfg.get(s, 'inverter_name')
        sets['system'].append((m, i))
    sets['azimuth'] = [120, 180, 240]
    sets['tilt'] = [0, 30, 60, 90]

    weatherpath = os.path.join(c.paths['weather'], c.pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(c.paths['geometry'],
                                      c.files['coastdatgrid_centroids']),
                         index_col='gid').loc[key]
    location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}

    weather = f.adapt_weather_to_pvlib(weather, location)

    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    my_index = pd.MultiIndex(levels=[[], [], []],
                             labels=[[], [], []],
                             names=['name', 'azimuth', 'tilt'])
    cols = ['irrad', 'dc', 'ac', 'dc/i', 'ac/i', 'ac/dc']
    df = pd.DataFrame(columns=cols, index=my_index)

    for system in sets['system']:
        for tlt in sets['tilt']:
            if tlt == 0:
                az_s = [0]
            else:
                az_s = sets['azimuth']
            for az in az_s:
                name = system[0].replace('_', '')[:10]
                logging.info("{0}, {1}, {2}".format(system, tlt, az))
                smodule = {
                    'module_parameters': sandia_modules[system[0]],
                    'inverter_parameters': sapm_inverters[system[1]],
                    'surface_azimuth': az,
                    'surface_tilt': tlt,
                    'albedo': 0.2}
                p_peak = (
                    smodule['module_parameters'].Impo *
                    smodule['module_parameters'].Vmpo)
                area = smodule['module_parameters'].Area

                mc = f.feedin_pvlib_modelchain(location, smodule, weather)
                dc = mc.dc.p_mp.clip(0).div(p_peak).sum()
                ac = mc.ac.clip(0).div(p_peak).sum()
                i = mc.total_irrad['poa_global'].multiply(area).div(
                    p_peak).sum()

                df.loc[(name, az, tlt), 'dc'] = dc
                df.loc[(name, az, tlt), 'ac'] = ac
                df.loc[(name, az, tlt), 'irrad'] = i
                df.loc[(name, az, tlt), 'dc/i'] = dc / i
                df.loc[(name, az, tlt), 'ac/i'] = ac / i
                df.loc[(name, az, tlt), 'ac/dc'] = ac / dc

    # df_ts.to_csv(os.path.join(paths['analysis'], 'orientation_feedin.csv'))
    df.to_csv(os.path.join(c.paths['analysis'], 'performance_ratio.csv'))


def get_index_of_max(df):
    column = None
    idx = None
    max_value = df.max().max()
    for col in df:
        try:
            idx = df[col][df[col] == max_value].index[0]
            column = col
        except IndexError:
            pass
    return column, idx


def analyse_pv_orientation_region():
    c = config.get_configuration()
    weatherpath = os.path.join(c.paths['weather'], c.pattern['weather'])

    my_index = pd.MultiIndex(levels=[[], [], []],
                             labels=[[], [], []],
                             names=['coastdat', 'year', 'system'])
    my_cols = pd.MultiIndex(levels=[[], []],
                            labels=[[], []],
                            names=['type', 'angle'])
    df = pd.DataFrame(columns=my_cols, index=my_index)

    key = 1141078
    for n in range(22):
        key += 1
        key -= 1000
        for year in [1998, 2003, 2008]:
            weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
            latlon = pd.read_csv(
                os.path.join(c.paths['geometry'],
                             c.files['coastdatgrid_centroids']),
                index_col='gid').loc[key]
            location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}

            weather = f.adapt_weather_to_pvlib(weather, location)

            sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
            sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

            systems = {
                1: {'m': 'LG_LG290N1C_G3__2013_',
                    'i': 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_'},
                2: {'m': 'BP_Solar_BP2150S__2000__E__',
                    'i':
                        'SolarBridge_Technologies__P235HV_240_240V__CEC_2011_'},
                3: {'m': 'Solar_Frontier_SF_160S__2013_',
                    'i': 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_'}
                }
            for system in systems.values():
                name = system['m'][:2].replace('o', 'F')
                logging.info("{0} - {1} - {2}".format(key, year, name))
                azimuth = range(175, 201)
                tilt = range(30, 41)
                dc = pd.DataFrame()
                ac = pd.DataFrame()
                ir = pd.DataFrame()
                for az in azimuth:
                    for tlt in tilt:
                        smodule = {
                            'module_parameters': sandia_modules[system['m']],
                            'inverter_parameters': sapm_inverters[system['i']],
                            'surface_azimuth': az,
                            'surface_tilt': tlt,
                            'albedo': 0.2}
                        p_peak = (
                            smodule['module_parameters'].Impo *
                            smodule['module_parameters'].Vmpo)

                        mc = f.feedin_pvlib_modelchain(location, smodule,
                                                       weather)
                        dc.loc[az, tlt] = mc.dc.p_mp.clip(0).div(p_peak).sum()
                        ac.loc[az, tlt] = mc.ac.clip(0).div(p_peak).sum()
                        ir.loc[az, tlt] = mc.total_irrad['poa_global'].clip(
                            0).sum()
                dc_max = get_index_of_max(dc)
                df.loc[(key, year, name), ('dc', 'tilt')] = dc_max[0]
                df.loc[(key, year, name), ('dc', 'azimuth')] = dc_max[1]
                ac_max = get_index_of_max(dc)
                df.loc[(key, year, name), ('ac', 'tilt')] = ac_max[0]
                df.loc[(key, year, name), ('ac', 'azimuth')] = ac_max[1]
                ir_max = get_index_of_max(dc)
                df.loc[(key, year, name), ('ir', 'tilt')] = ir_max[0]
                df.loc[(key, year, name), ('ir', 'azimuth')] = ir_max[1]
        df.to_csv(os.path.join(c.paths['analysis'],
                               'optimal_orientation_multi.csv'))
    logging.info('Done')


def analyse_optimal_orientation_file():
    c = config.get_configuration()
    df = pd.read_csv(os.path.join(c.paths['analysis'],
                                  'optimal_orientation_multi.csv'),
                     index_col=[0, 1, 2], header=[0, 1])
    df.sort_index(axis=0, inplace=True)
    df.sort_index(axis=1, inplace=True)
    df['avg', 'azimuth'] = df.loc[:, (slice(None), 'azimuth')].sum(1).div(3)
    df['avg', 'tilt'] = df.loc[:, (slice(None), 'tilt')].sum(1).div(3)
    print(df.index)
    print(df['avg'].groupby('year').mean())


def analyse_pv_orientation(year, key, module_name):
    c = config.get_configuration()
    weatherpath = os.path.join(c.paths['weather'], c.pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(c.paths['geometry'],
                                      c.files['grid_centroid']),
                         index_col='gid').loc[key]
    location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}

    weather = f.adapt_weather_to_pvlib(weather, location)

    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    invertername = 'SMA_America__SB5000US_11_208V__CEC_2007_'

    azimuth = range(0, 361, 10)
    tilt = range(0, 91, 10)

    # df_ts = pd.DataFrame()
    df_dc = pd.DataFrame()
    df_ac = pd.DataFrame()
    df_sun = pd.DataFrame()
    length = len(azimuth) * len(tilt)
    # from matplotlib import pyplot as plt
    for az in azimuth:
        for tlt in tilt:
            name = 'az{0}_tlt{1}'.format(az, tlt)
            logging.info("{0}, {1}".format(name, length))
            length -= 1
            smodule = {
                'module_parameters': sandia_modules[module_name],
                'inverter_parameters': sapm_inverters[invertername],
                'surface_azimuth': az,
                'surface_tilt': tlt,
                'albedo': 0.2}
            p_peak = (
                smodule['module_parameters'].Impo *
                smodule['module_parameters'].Vmpo)

            mc = f.feedin_pvlib_modelchain(location, smodule, weather)
            df_dc.loc[az, tlt] = mc.dc.p_mp.clip(0).div(p_peak).sum()
            df_ac.loc[az, tlt] = mc.ac.clip(0).div(p_peak).sum()
            # print(mc.total_irrad.columns)
            # print(mc.total_irrad['poa_global'].fillna(0).div(p_peak).sum())
            df_sun.loc[az, tlt] = mc.total_irrad['poa_global'].div(p_peak).sum()
    # df_ts.to_csv(os.path.join(paths['analysis'], 'orientation_feedin.csv'))
    df_sun.to_csv(os.path.join(c.paths['analysis'], 'sun.csv'))
    df_dc.to_csv(os.path.join(c.paths['analysis'], 'orientation_feedin_dc.csv'))
    df_ac.to_csv(os.path.join(c.paths['analysis'], 'orientation_feedin_ac.csv'))


def analyse_inverter(year, key, module_name, orientation):
    c = config.get_configuration()
    weatherpath = os.path.join(c.paths['weather'], c.pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(c.paths['geometry'],
                                      c.files['grid_centroid']),
                         index_col='gid').loc[key]
    location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}
    weather = f.adapt_weather_to_pvlib(weather, location)
    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    inv = pd.DataFrame()
    failed = pd.Series()
    length = len(sapm_inverters.keys())
    for sinv in sapm_inverters.keys():
        name = sinv  # .replace('__', '_')
        logging.info("{0}, {1}".format(name, length))
        length -= 1
        smodule = {
            'module_parameters': sandia_modules[module_name],
            'inverter_parameters': sapm_inverters[sinv],
            'surface_azimuth': orientation['azimuth'],
            'surface_tilt': orientation['tilt'],
            'albedo': 0.2}
        p_peak = (
                smodule['module_parameters'].Impo *
                smodule['module_parameters'].Vmpo)
        try:
            mc = f.feedin_pvlib_modelchain(location, smodule, weather)
            inv.loc[name, 'ac'] = mc.ac.clip(0).fillna(0).div(p_peak).sum()
            inv.loc[name, 'dc'] = mc.dc.p_mp.clip(0).fillna(0).div(p_peak).sum()
        except ValueError:
            logging.info("Inverter {0} failed.".format(name))
            failed.loc[name] = 'failed'
    inv.to_csv(os.path.join(c.paths['analysis'],
                            'sapm_inverters_feedin_full2.csv'))
    failed.to_csv(os.path.join(c.paths['analysis'],
                               'sapm_inverters_failed.csv'))


def single_pv_set(year, key, module_name, inverter_name, orientation):
    c = config.get_configuration()
    weatherpath = os.path.join(c.paths['weather'], c.pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(c.paths['geometry'],
                                      c.files['grid_centroid']),
                         index_col='gid').loc[key]
    location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}
    weather = f.adapt_weather_to_pvlib(weather, location)
    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    smodule = {
        'module_parameters': sandia_modules[module_name],
        'inverter_parameters': sapm_inverters[inverter_name],
        'surface_azimuth': orientation['azimuth'],
        'surface_tilt': orientation['tilt'],
        'albedo': 0.2}
    p_peak = (
            smodule['module_parameters'].Impo *
            smodule['module_parameters'].Vmpo)

    mc = f.feedin_pvlib_modelchain(location, smodule, weather)
    ac = mc.ac  # .clip(0).fillna(0).div(p_peak)
    dc = mc.dc.p_mp  # .clip(0).fillna(0).div(p_peak)

    print('ac:', ac.sum())
    print('dc:', dc.sum())


def analyse_feedin_de(year):
    c = config.get_configuration()

    # read renewable powerplants
    pp = pd.read_csv(os.path.join(c.paths['renewable'],
                                  c.pattern['grouped'].format(cat='renewable')),
                     index_col=[0, 1, 2, 3])

    # group renewable powerplants
    my_index = pp.loc['Wind', year].groupby(level=0).sum().index
    powerplants_renewable = pd.DataFrame(index=my_index)
    for pptype in pp.index.levels[0]:
        powerplants_renewable[pptype] = pp.loc[pptype, year].groupby(
            level=0).sum()

    # read wind feedin time series (feedin_wind)
    feedin_wind = pd.read_csv(
        os.path.join(c.paths['feedin'], 'wind', 'de21',
                     c.pattern['feedin_de21'].format(year=year, type='wind')),
        index_col=0, header=[0, 1])

    # multiply time series with installed capacity
    wind = pd.DataFrame()
    for reg in feedin_wind.columns.levels[0]:
        wind[reg] = feedin_wind[reg, 'feedin_wind_turbine'].multiply(
            powerplants_renewable.loc[reg, 'Wind'])
    wind = wind.sum(1)
    wind.to_csv(os.path.join(c.paths['analysis'], 'wind_de.csv'))

    # read solar feedin time series (feedin_solar)
    feedin_solar = pd.read_csv(
        os.path.join(
            c.paths['feedin'], 'solar', 'de21',
            c.pattern['feedin_de21'].format(year=year, type='solar')),
        index_col=0, header=[0, 1, 2], parse_dates=True)

    set_name = {
        'M_STP280S__I_GEPVb_5000_NA_240': 0.2,
        'M_BP2150S__I_P235HV_240': 0.2,
        'M_LG290G3__I_ABB_MICRO_025_US208': 0.3,
        'M_SF160S___I_ABB_MICRO_025_US208': 0.3,
        }

    orientation = {
        'tlt000_az000_alb02': 0.1,
        'tlt090_az120_alb02': 0.0,
        'tlt090_az180_alb02': 0.1,
        'tlt090_az240_alb02': 0.0,
        'tltopt_az120_alb02': 0.2,
        'tltopt_az180_alb02': 0.4,
        'tltopt_az240_alb02': 0.2,
        }

    solar = pd.DataFrame(index=feedin_solar.index)
    for reg in feedin_solar.columns.levels[0]:
        solar[reg] = 0
        for set in set_name.keys():
            for subset in orientation.keys():
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


def get_maximum_value(filename, pathname=None, icol=None):
    if pathname is None:
        c = config.get_configuration()
        pathname = c.paths['analysis']
    if icol is None:
        icol = [0]
    table = pd.read_csv(os.path.join(pathname, filename), index_col=icol)
    idx = None
    column = None
    if isinstance(table, pd.Series):
        max_value = table.max()
        idx = table[table == max_value].index[0]
    elif isinstance(table, pd.DataFrame):
        max_value = table.max().max()
        for col in table:
            try:
                idx = table[col][table[col] == max_value].index[0]
                column = col
            except IndexError:
                pass
    print(column, idx)
    # print("Maximum value of {0} is {1}".format(df_file, df.max().max()))
    # return df.max().max()


def analyse_pv_capacity():
    c = config.get_configuration()
    cap = pd.read_csv(
        os.path.join(c.paths['renewable'], c.pattern['grouped'].format(
            cat='renewable')), index_col=[0, 1, 2])
    cap_full = pd.read_csv(
        os.path.join(c.paths['renewable'], c.pattern['prepared'].format(
            cat='renewable')), index_col=['commissioning_date'],
        parse_dates=True)
    print(cap_full.loc[cap_full['energy_source_level_2'] == 'Solar'][
              'electrical_capacity'].sum())
    print(cap_full.columns)
    select = cap_full.loc[pd.notnull(cap_full['decommissioning_date'])]
    select = select.loc[select['energy_source_level_2'] == 'Solar'][
              'electrical_capacity']
    print(select.sum())

    for y in range(2012, 2017):
        print(y, 'my', cap.loc['Solar', y]['capacity'].sum())

    re_file = os.path.join(c.paths['time_series'],
                           c.files['renewables_time_series'])
    ts = pd.read_csv(re_file, index_col='cet', parse_dates=True)

    for y in range(2012, 2016):
        start = ts.loc[datetime.datetime(y, 1, 1, 0, 0)]['DE_solar_capacity']
        end = ts.loc[datetime.datetime(y, 12, 31, 0, 0)]['DE_solar_capacity']
        print(y, 'avg', (start + end) / 2)
    for y in range(2012, 2017):
        start = ts.loc[datetime.datetime(y, 1, 1, 0, 0)]['DE_solar_capacity']
        print(y, 'start', start)
    new = pd.DataFrame()
    new['other'] = ts['DE_solar_capacity']
    new['own'] = 0
    new['quaschning'] = 0
    new['fraunhofer'] = 0

    quaschning = {
        2016: 41.27,
        2015: 39.74,
        2014: 38.24,
        2013: 36.34,
        2012: 33.03}

    fraunhofer = {
        2016: 40.85,
        2015: 39.33,
        2014: 37.90,
        2013: 36.71,
        2012: 33.03}

    for y in range(2012, 2017):
        start = datetime.datetime(y, 1, 1, 0, 0)
        end = datetime.datetime(y, 12, 31, 23, 0)
        new.loc[(new.index <= end) & (new.index >= start), 'own'] = cap.loc[
            'Solar', y]['capacity'].sum()
        new.loc[(new.index <= end) & (new.index >= start), 'quaschning'] = (
            quaschning[y] * 1000)
        new.loc[(new.index <= end) & (new.index >= start), 'fraunhofer'] = (
            fraunhofer[y] * 1000)
    new.plot()
    plt.show()


def weather_statistics():
    c = config.get_configuration()
    from matplotlib import pyplot as plt
    import numpy as np
    years = list()
    for y in range(1970, 2020):
        if os.path.isfile(os.path.join(c.paths['weather'],
                                       c.pattern['weather'].format(year=y))):
            years.append(y)
    mypath = c.paths['geometry']
    myfile = 'intersection_region_coastdatgrid.csv'
    df = pd.read_csv(os.path.join(mypath, myfile), index_col='id')
    ids = df[df.region_number < 19].coastdat.unique()
    ghi = pd.DataFrame()
    if not os.path.isfile(
            os.path.join(c.paths['analysis'], 'ghi_coastdat.csv')):
        for year in years:
            print(year)
            weather = pd.HDFStore(os.path.join(
                c.paths['weather'], c.pattern['weather'].format(year=year)),
                mode='r')
            for cid in ids:
                wdf = weather['/A{0}'.format(cid)]
                ghi.loc[cid, year] = (wdf.dhi + wdf.dirhi).sum() / 1000
        ghi.to_csv(os.path.join(c.paths['analysis'], 'ghi_coastdat.csv'))
    df = pd.read_csv(os.path.join(c.paths['analysis'], 'ghi_coastdat.csv'),
                     index_col=[0])
    df.columns = pd.to_numeric(df.columns)
    dwd = pd.read_csv(os.path.join(c.paths['external'], 'dwd_ghi.csv'),
                      index_col=[0])
    print(type(pd.Series(df.max())))
    dwd['coastdat_max'] = round(df.max())
    dwd['coastdat_mean'] = round(df.sum() / len(df))
    dwd['coastdat_min'] = round(df.min())
    print(dwd)
    # dwd.plot(style=['b-.', 'b:', 'g-.', 'g:'], linewidth=[1,3,1,1,3,1])
    fig, ax = plt.subplots()
    ax = dwd[['dwd_max', 'coastdat_max']].plot(style=['b:', 'g:'], ax=ax)
    ax = dwd[['dwd_mean', 'coastdat_mean']].plot(style=['b-', 'g-'], ax=ax,
                                                 linewidth=3)
    dwd[['dwd_min', 'coastdat_min']].plot(style=['b-.', 'g-.'], ax=ax)
    # dwd.plot(kind='bar')
    plt.show()
    n_df = 2
    n_col = 3
    n_ind = 17
    neu1 = pd.DataFrame()
    neu1['DWD (min)'] = dwd['dwd_min']
    neu1['DWD (mean)'] = dwd['dwd_mean'] - dwd['dwd_min']
    neu1['DWD (max)'] = dwd['dwd_max'] - dwd['dwd_mean']
    print(neu1)
    neu2 = pd.DataFrame()
    neu2['coastdat_min'] = dwd['coastdat_min']
    neu2['coastdat_mean'] = dwd['coastdat_mean'] - dwd['coastdat_min']
    neu2['coastDat-2 (max)'] = dwd['coastdat_max'] - dwd['coastdat_mean']
    axe = plt.subplot(111)
    axe = neu1.plot(kind='bar', stacked=True, ax=axe, color=['#ffffff',
                                                             'green',
                                                             'green'])
    axe = neu2.plot(kind='bar', stacked=True, ax=axe, color=['#ffffff',
                                                             '#286cf8',
                                                             '#286cf8'])
    h, l = axe.get_legend_handles_labels()  # get the handles we want to modify
    for i in range(0, n_df * n_col, n_col):  # len(h) = n_col * n_df
        for j, pa in enumerate(h[i:i+n_col]):
            for rect in pa.patches:  # for each index
                rect.set_x(
                    rect.get_x() + 1 / float(n_df + 1) * i / float(n_col))
                rect.set_width(1 / float(n_df + 5))
    axe.set_xticks((np.arange(0, 2 * n_ind, 2) + 1 / float(n_df + 1)) / 2.)
    axe.set_xticklabels(neu1.index, rotation = 0)
    axe.set_title('Deutschlandweites Jahresmittel im Vergleich '
                  '(DWD - coastDat-2) Quelle:' +
                  'http://www.dwd.de/DE/leistungen/solarenergie/' +
                  'lstrahlungskarten_su.html')
    box = axe.get_position()
    axe.set_position([box.x0, box.y0, box.width * 0.9, box.height])
    h = h[1:2] + h[4:5]
    l = ['DWD', 'coastDat-2']
    l1 = axe.legend(h, l, loc='center left', bbox_to_anchor=(1, 0.5))
    axe.set_ylabel('Globalstrahlung (horizontal) [kWh/m2]')
    axe.set_xlabel('Jahr')
    axe.add_artist(l1)
    x = np.arange(-0.19, 16.3, 1)
    axe.plot(x, np.array(dwd['dwd_mean']), 'D', markersize=10, color='#004200')
    x = np.arange(0.15, 17.1, 1)
    axe.plot(x, np.array(dwd['coastdat_mean']), 'D', markersize=10,
             color='#133374')
    plt.show()
    print(round((dwd.dwd_mean.div(dwd.coastdat_mean) - 1) * 100))
    print(((dwd.dwd_mean.div(dwd.coastdat_mean) - 1) * 100).sum() / len(dwd))
    exit(0)


def something():
    c = config.get_configuration()
    cap = pd.read_csv(
        os.path.join(c.paths['analysis'], 'pv_data.csv'),
        header=1, index_col='year')
    print(cap.columns)
    cap['inst_mean'] = cap.inst - (cap.inst - cap.inst.shift(1)) / 2
    cap['diff'] = cap.inst - cap.inst.shift(1)
    cap['VLSt'] = (cap.inst_mean / cap.erzeug) * 1000
    cap['factor'] = cap['VLSt'] / cap['mean']
    print(cap)
    print(cap.sum() / 5)


if __name__ == "__main__":
    # initialise logger
    logger.define_logging()
    weather_statistics()
    something()
    # analyse_optimal_orientation_file()
    # get_maximum_value('performance_ratio.csv', icol=[0, 1, 2])
    # get_maximum_value('orientation_feedin_dc_high_resolution.csv')
    # analyse_performance_ratio(2003, 1129087)
    # analyse_pv_capacity()
    # analyse_feedin_de(2014)
    # get_full_load_hours()
    # analyse_pv_types(2003, 1129087, orientation={'azimuth': 180, 'tilt': 32})
    # analyse_pv_orientation(2003, 1129087, 'LG_LG290N1C_G3__2013_')
    # analyse_inverter(2003, 1129087, 'BP_Solar_BP2150S__2000__E__',
    #                  orientation={'azimuth': 180, 'tilt': 35})
    # single_pv_set(2003, 1129087, 'LG_LG290N1C_G3__2013_',
    #               'SMA_America__SB9000TL_US_12__240V__240V__CEC_2012_',
    #               orientation={'azimuth': 180, 'tilt': 35})
