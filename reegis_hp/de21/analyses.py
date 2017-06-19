__copyright__ = "Uwe Krien"
__license__ = "GPLv3"


import pandas as pd
import configuration as config
import logging
import os
import feedin as f
import pvlib
import datetime
from oemof.tools import logger
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
    df.to_csv(os.path.join(c.paths['analyses'], 'full_load_hours.csv'))


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
        name = smod  #.replace('__', '_')
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
    df.to_csv(os.path.join(c.paths['analyses'], 'module_feedin.csv'))
    df_ts_ac.to_csv(os.path.join(c.paths['analyses'],
                                 'module_feedin_ac_ts.csv'))


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
    # df_ts.to_csv(os.path.join(paths['analyses'], 'orientation_feedin.csv'))
    df_dc.to_csv(os.path.join(c.paths['analyses'], 'orientation_feedin_dc.csv'))
    df_ac.to_csv(os.path.join(c.paths['analyses'], 'orientation_feedin_ac.csv'))


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
    inv.to_csv(os.path.join(c.paths['analyses'],
                            'sapm_inverters_feedin_full2.csv'))
    failed.to_csv(os.path.join(c.paths['analyses'],
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
    wind.to_csv(os.path.join(c.paths['analyses'], 'wind_de.csv'))

    # read solar feedin time series (feedin_solar)
    feedin_solar = pd.read_csv(
        os.path.join(
            c.paths['feedin'], 'solar', 'de21',
            c.pattern['feedin_de21'].format(year=year, type='solar')),
        index_col=0, header=[0, 1, 2], parse_dates=True)

    set_name = {
        'M_STP280S__I_GEPVb_5000_NA_240': 0.2,
        'M_BP2150S__I_P235HV_240': 0.3,
        'M_LG290G3__I_ABB_MICRO_025_US208': 0.3,
        'M_SF160S___I_ABB_MICRO_025_US208': 0.2,
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
    solar.to_csv(os.path.join(c.paths['analyses'], 'solar_de.csv'))

    re_file = os.path.join(c.paths['time_series'],
                           c.files['renewables_time_series'])

    start = datetime.datetime(year, 1, 1, 0, 0)
    end = datetime.datetime(year, 12, 31, 23, 0)

    ts = pd.read_csv(re_file, index_col='cet', parse_dates=True).loc[start:end]
    print(ts['DE_solar_generation'].sum())
    print(solar[:8760].sum() / 2)
    print((solar[:8760].sum() / 2) / (34.93 * 1000000))
    new = pd.DataFrame()
    new['own'] = solar[:8760]
    new['other'] = ts['DE_solar_generation']
    new.plot()

    plt.show()


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
        print(y, cap.loc['Solar', y]['capacity'].sum())

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
    exit(0)


if __name__ == "__main__":
    # initialise logger
    logger.define_logging()
    # analyse_pv_capacity()
    analyse_feedin_de(2014)
    # get_full_load_hours()
    # analyse_pv_types(2003, 1129087, orientation={'azimuth': 180, 'tilt': 32})
    # analyse_pv_orientation(2003, 1129087, 'LG_LG290N1C_G3__2013_')
    # analyse_inverter(2003, 1129087, 'BP_Solar_BP2150S__2000__E__',
    #                  orientation={'azimuth': 180, 'tilt': 35})
    # single_pv_set(2003, 1129087, 'LG_LG290N1C_G3__2013_',
    #               'SMA_America__SB9000TL_US_12__240V__240V__CEC_2012_',
    #               orientation={'azimuth': 180, 'tilt': 35})
