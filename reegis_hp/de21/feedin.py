__copyright__ = "Uwe Krien"
__license__ = "GPLv3"

import pandas as pd
from datetime import datetime as time
import os
from windpowerlib import wind_turbine as wt
from windpowerlib import modelchain
import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain
import bisect
try:
    import oemof.db as db
except ImportError:
    db = None
import logging
from oemof.tools import logger
import config as cfg


def normalised_feedin_by_region(paths, pattern, overwrite=False):
    feedin_de21 = os.path.join(paths['feedin'], '{type}',
                               pattern['feedin_de21'])
    feedin_coastdat = os.path.join(paths['feedin'], '{type}', pattern['feedin'])
    category = 'renewable'
    powerplants = os.path.join(paths[category],
                               pattern['grouped'].format(cat=category))

    pp = pd.read_csv(powerplants, index_col=[0, 1, 2, 3])

    for vtype in ['Wind', 'Solar']:
        years = list()
        for y in range(1990, 2025):
            outfile = feedin_de21.format(year=y, type=vtype.lower())
            infile = feedin_coastdat.format(year=y, type=vtype.lower())
            if not os.path.isfile(outfile) or overwrite:
                if os.path.isfile(infile):
                    years.append(y)
        if overwrite:
            logging.warning("Existing files will be overwritten.")
        else:
            logging.info("Existing files are skipped.")
        logging.info(
            "Will create {0} time series for the following years: {1}".format(
                vtype.lower(), years))
        for year in years:
            logging.info("Processing {0}...".format(year))
            pwr = pd.HDFStore(feedin_coastdat.format(year=year,
                                                     type=vtype.lower()))
            try:
                columns = pwr['/A1129087'].columns
            except AttributeError:
                columns = (pwr['/A1129087'].name, )
            my_index = pwr[pwr.keys()[0]].index
            my_cols = pd.MultiIndex(levels=[[], []], labels=[[], []],
                                    names=[u'region', u'set'])
            feedin = pd.DataFrame(index=my_index, columns=my_cols)
            for region in sorted(
                    pp.loc[(vtype, year)].index.get_level_values(0).unique()):
                temp = dict()
                for col in columns:
                    temp[col] = pd.DataFrame(index=my_index)
                logging.debug("{0} - {1}".format(year, region))

                for coastdat in pp.loc[(vtype, year, region)].index:
                    # Multiply time series (normalised to 1kW) with capacity(kW)
                    tmp = pwr['/A' + str(int(coastdat))].multiply(
                        float(pp.loc[(vtype, year, region, coastdat)]))
                    for col in columns:
                        try:
                            temp[col][coastdat] = tmp[col]
                        except KeyError:
                            temp[col][coastdat] = tmp
                if str(region) == 'nan':
                    region = 'unknown'

                # Sum up time series for one region and divide it by the
                # capacity of the region to get a normalised time series.
                for col in columns:
                    feedin[region, col] = temp[col].sum(axis=1).divide(
                        float(pp.loc[(vtype, year, region)].sum()))

            feedin.to_csv(feedin_de21.format(year=year, type=vtype.lower()))
            pwr.close()


def normalised_feedin_wind_single(polygons, key, weather):
    coastdat2 = {
        'dhi': 0,
        'dirhi': 0,
        'pressure': 0,
        'temp_air': 2,
        'v_wind': 10,
        'Z0': 0}

    wind_power_plants = {
        1: {'hub_height': 135,
            'd_rotor': 127,
            'turbine_name': 'ENERCON E 126 7500',
            'nominal_power': 7500000},
        2: {'hub_height': 78,
            'd_rotor': 82,
            'turbine_name': 'ENERCON E 82 3000',
            'nominal_power': 3000000},
        3: {'hub_height': 98,
            'd_rotor': 82,
            'turbine_name': 'ENERCON E 82 2300',
            'nominal_power': 2300000},
        4: {'hub_height': 138,
            'd_rotor': 82,
            'turbine_name': 'ENERCON E 82 2300',
            'nominal_power': 2300000},
    }

    avg_wind2type = pd.Series({
        1.5: 4,
        2.5: 3,
        3.5: 2,
        4.5: 1,
        5.5: 1,
        100: 1,
    })

    avg_wind_speed = polygons.loc[int(key[2:]), 'v_wind_avg']
    wka_class = avg_wind2type.iloc[
        bisect.bisect_right(list(avg_wind2type.index), avg_wind_speed)]
    wpp = wt.WindTurbine(**wind_power_plants[wka_class])

    # add information about converter type and class to the polygons table
    polygons.loc[int(key[2:]), 'turbine_name'] = wind_power_plants[wka_class][
        'turbine_name']
    polygons.loc[int(key[2:]), 'wind_conv_class'] = wka_class

    modelchain_data = {
        'obstacle_height': 0,
        'wind_model': 'logarithmic',
        'rho_model': 'ideal_gas',
        'power_output_model': 'p_values',
        'density_corr': True,
        'hellman_exp': None}

    mcwpp = modelchain.ModelChain(wpp, **modelchain_data).run_model(
        weather, coastdat2)
    return mcwpp.power_output.div(wind_power_plants[wka_class]['nominal_power'])


def feedin_pvlib_modelchain(location, system, weather, tilt=None,
                            orientation_strategy=None):
    if tilt is None:
        tilt = system['tilt']

    # pvlib's ModelChain
    pvsys = PVSystem(inverter_parameters=system['inverter_parameters'],
                     module_parameters=system['module_parameters'],
                     surface_tilt=tilt,
                     surface_azimuth=system['surface_azimuth'],
                     albedo=system['albedo'])

    mc = ModelChain(pvsys, Location(**location),
                    orientation_strategy=orientation_strategy)
    mc.run_model(weather.index, weather=weather)
    return mc


def get_optimal_pv_angle(lat):
    """
    About 27° to 34° from ground in Germany.
    The pvlib uses tilt angles horizontal=90° and up=0°. Therefore 90° minus the
    angle from the horizontal."""
    return lat - 20


def create_pv_sets():
    # get module and inverter parameter from sandia database
    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    def get_list(section, parameter):
        try:
            my_list = cfg.get(section, parameter).replace(' ', '').split(',')
        except AttributeError:
            my_list = list((cfg.get(section, parameter),))
        return my_list

    module_names = get_list('solar', 'module_name')
    module_keys = get_list('solar', 'module_key')
    modules = {module_keys[n]: module_names[n] for n in range(len(module_keys))}
    inverters = get_list('solar', 'inverter_name')
    azimuth_angles = get_list('solar', 'surface_azimuth')
    tilt_angles = get_list('solar', 'surface_tilt')
    albedo_values = get_list('solar', 'albedo')

    set_number = 0
    pv_systems = dict()
    for mk, mn in modules.items():
        for i in inverters:
            for t in tilt_angles:
                if t == '0':
                    az_angles = (0,)
                else:
                    az_angles = azimuth_angles
                for a in az_angles:
                    for alb in albedo_values:
                        set_number += 1
                        pv_systems[set_number] = {
                            'module_parameters': sandia_modules[mn],
                            'inverter_parameters': sapm_inverters[i],
                            'surface_azimuth': float(a),
                            'surface_tilt': t,
                            'albedo': float(alb)}
                        pv_systems[set_number]['p_peak'] = (
                            pv_systems[set_number]['module_parameters'].Impo *
                            pv_systems[set_number]['module_parameters'].Vmpo)
                        pv_systems[set_number]['name'] = "_".join([
                            mk,
                            i[:3],
                            "tlt{}".format(t[:3].rjust(3, '0')),
                            "az{}".format(str(a).rjust(3, '0')),
                            "alb{}".format(str(alb).replace('.', ''))
                        ])
                        logging.info("PV set: {}".format(
                            pv_systems[set_number]['name']))
    return pv_systems


def adapt_weather_to_pvlib(w, location):
    loc = Location(**location)
    w['temp_air'] = w.temp_air - 273.15
    w['ghi'] = w.dirhi + w.dhi
    clearskydni = loc.get_clearsky(w.index).dni
    w['dni'] = pvlib.irradiance.dni(
        w['ghi'], w['dhi'], pvlib.solarposition.get_solarposition(
            w.index, loc.latitude, loc.longitude).zenith,
        clearsky_dni=clearskydni, clearsky_tolerance=1.1)
    return w


def normalised_feedin_pv(paths, pattern, files, weather, year):
    """pass"""
    feedin_file = os.path.join(
        paths['feedin'], 'solar',
        pattern['feedin'].format(year=year, type='solar'))
    pwr = pd.HDFStore(feedin_file.format(year, 'solar'), mode='w')

    latlon = pd.read_csv(os.path.join(paths['geometry'],
                                      files['grid_centroid']), index_col='gid')

    pv_systems = create_pv_sets()
    keys = weather.keys()
    length = len(keys)
    logging.info('Remaining polygons for {0}: {1}'.format(year, length))

    for key in keys:
        one_region = pd.DataFrame()
        length -= 1
        # if length % 100 == 0:
        logging.info('Remaining polygons for {0}: {1}'.format(year, length))
        location = {
            # 'altitude': 34,
            'latitude': latlon.loc[int(key[2:]), 'st_y'],
            'longitude': latlon.loc[int(key[2:]), 'st_x'],
            }

        w = adapt_weather_to_pvlib(weather[key], location)

        for pv_system in pv_systems.values():
            if pv_system['surface_tilt'] == 'optimal':
                tilt = get_optimal_pv_angle(location['latitude'])
            else:
                tilt = float(pv_system['surface_tilt'])
            mc = feedin_pvlib_modelchain(location, pv_system, w, tilt=tilt)
            one_region[pv_system['name']] = mc.ac.fillna(0).clip(0).div(
                pv_system['p_peak'])
        pwr[key] = one_region
    pwr.close()


def normalised_feedin_wind(paths, pattern, files, weather, year):
    """pass"""
    feedin_file = os.path.join(paths['feedin'], 'wind',
                               pattern['feedin'].format(year=year, type='wind'))
    pwr = pd.HDFStore(feedin_file.format(year, 'wind'), mode='w')
    average_wind_speed = pd.read_csv(os.path.join(paths['weather'],
                                                  files['average_wind_speed']),
                                     index_col='gid')

    keys = weather.keys()
    length = len(keys)
    logging.info('Remaining polygons for {0}: {1}'.format(year, length))
    for key in keys:
        length -= 1
        if length % 100 == 0:
            logging.info('Remaining polygons for {0}: {1}'.format(year, length))
        weather_df = weather[key]
        pwr[key] = normalised_feedin_wind_single(average_wind_speed, key,
                                                 weather_df)
    pwr.close()


def normalised_feedin_one_year(paths, pattern, files, year, overwrite):
    """pass"""
    start = time.now()
    weather = None
    fileopen = False
    feedin_pattern = os.path.join(paths['feedin'], '{type}', pattern['feedin'])
    f_wind = feedin_pattern.format(year=year, type='wind')
    f_solar = feedin_pattern.format(year=year, type='solar')

    if not os.path.isfile(f_wind) or not os.path.isfile(f_solar) or overwrite:
        weather = pd.HDFStore(os.path.join(
            paths['weather'], pattern['weather'].format(year=year)),
            mode='r')
        fileopen = True

    txt_create = "Creating normalised {0} feedin time series for {1}."
    txt_skip = "File '{0}' exists. Skipped. "

    if not os.path.isfile(f_wind) or overwrite:
        logging.info(txt_create.format('wind', year))
        normalised_feedin_wind(paths, pattern, files, weather, year)
    else:
        logging.info(txt_skip.format(f_wind))

    if not os.path.isfile(f_solar) or overwrite:
        logging.info(txt_create.format('solar', year))
        normalised_feedin_pv(paths, pattern, files, weather, year)
    else:
        logging.info(txt_skip.format(f_solar))

    if fileopen:
        weather.close()
        logging.info("Normalised time series created: {0} - {1}".format(
            year, time.now() - start))


def normalised_feedin_by_weather(paths, pattern, files, years=None,
                                 overwrite=False):
    """pass"""
    # Finding existing weather files.
    if years is None:
        filelist = (os.listdir(paths['weather']))
        years = list()
        for y in range(1970, 2020):
            if pattern['weather'].format(year=y) in filelist:
                years.append(y)

    for year in years:
        normalised_feedin_one_year(paths, pattern, files, year, overwrite)


if __name__ == "__main__":
    logger.define_logging()
