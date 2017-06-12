__copyright__ = "Uwe Krien"
__license__ = "GPLv3"


import pandas as pd
import configuration as config
import logging
import os
import feedin as f
import pvlib
from oemof.tools import logger
# import plots


def get_full_load_hours():
    """pass"""
    paths, pattern, files, general = config.get_configuration()
    feedinpath = os.path.join(paths['feedin'], '{type}', pattern['feedin'])

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
    df.to_csv(os.path.join(paths['analyses'], 'full_load_hours.csv'))


def analyse_pv_types(year, key, orientation):
    paths, pattern, files, general = config.get_configuration()
    weatherpath = os.path.join(paths['weather'], pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(paths['geometry'],
                                      files['grid_centroid']),
                         index_col='gid').loc[key]
    location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}

    weather = f.adapt_weather_to_pvlib(weather, location)

    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    invertername = 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_'

    df_ts_ac = pd.DataFrame()
    df_dc = pd.Series()
    df_ac = pd.Series()
    length = len(sandia_modules.keys())
    for smod in sandia_modules.keys():
        name = smod.replace('__', '_')
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
        df_ac.loc[name] = df_ts_ac[name][:8760].sum()
        df_dc.loc[name] = mc.dc.p_mp.clip(0).div(p_peak).sum()
    # df_ts.to_csv(os.path.join(paths['analyses'], 'orientation_feedin.csv'))
    df_dc.to_csv(os.path.join(paths['analyses'], 'module_feedin_dc.csv'))
    df_ac.to_csv(os.path.join(paths['analyses'], 'module_feedin_ac.csv'))
    df_ts_ac.to_csv(os.path.join(paths['analyses'], 'module_feedin_ac_ts.csv'))


def analyse_pv_orientation(year, key, module_name):
    paths, pattern, files, general = config.get_configuration()
    weatherpath = os.path.join(paths['weather'], pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(paths['geometry'],
                                      files['grid_centroid']),
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
    df_dc.to_csv(os.path.join(paths['analyses'], 'orientation_feedin_dc.csv'))
    df_ac.to_csv(os.path.join(paths['analyses'], 'orientation_feedin_ac.csv'))


def analyse_inverter(year, key, module_name, orientation):
    paths, pattern, files, general = config.get_configuration()
    weatherpath = os.path.join(paths['weather'], pattern['weather'])
    weather = pd.read_hdf(weatherpath.format(year=year), 'A' + str(key))
    latlon = pd.read_csv(os.path.join(paths['geometry'],
                                      files['grid_centroid']),
                         index_col='gid').loc[key]
    location = {'latitude': latlon['st_y'], 'longitude': latlon['st_x']}
    weather = f.adapt_weather_to_pvlib(weather, location)
    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    inv = pd.DataFrame()
    failed = pd.Series()
    length = len(sapm_inverters.keys())
    for sinv in sapm_inverters.keys():
        name = sinv.replace('__', '_')
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
    inv.to_csv(os.path.join(paths['analyses'], 'sapm_inverters_feedin_full.csv'))
    failed.to_csv(os.path.join(paths['analyses'], 'sapm_inverters_failed.csv'))


if __name__ == "__main__":
    # initialise logger
    logger.define_logging()
    get_full_load_hours()
    # analyse_pv_types(2003, 1129087, orientation={'azimuth': 180, 'tilt': 32})
    # analyse_pv_orientation(2003, 1129087, 'LG_LG290N1C_G3__2013_')
    # analyse_inverter(2003, 1129087, 'LG_LG290N1C_G3__2013_',
    #                  orientation={'azimuth': 180, 'tilt': 45})
