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
import configuration as config


def normalised_feedin_by_region_wind(pp, feedin_de21, feedin_coastdat,
                                     overwrite):
    vtype = 'Wind'

    # Check for existing in-files and non-existing out-files
    years = list()
    for y in range(1990, 2025):
        outfile = feedin_de21.format(year=y, type=vtype.lower())
        infile = feedin_coastdat.format(year=y, type=vtype.lower(),
                                        sub='coastdat')
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

    # Loop over all years according to the file check above
    for year in years:
        logging.info("Processing {0}...".format(year))
        pwr = pd.HDFStore(feedin_coastdat.format(year=year,
                                                 type=vtype.lower(),
                                                 sub='coastdat'))
        my_index = pwr[pwr.keys()[0]].index
        feedin = pd.DataFrame(index=my_index)

        # Loop over all aggregation regions
        for region in sorted(
                pp.loc[(vtype, year)].index.get_level_values(0).unique()):

            # Create an temporary DataFrame to collect the results
            temp = pd.DataFrame(index=my_index)
            logging.debug("{0} - {1}".format(year, region))

            # Multiply normalised time series (normalised to 1kW_peak) with peak
            # capacity(kW).
            for coastdat in pp.loc[(vtype, year, region)].index:
                tmp = pwr['/A' + str(int(coastdat))].multiply(
                    float(pp.loc[(vtype, year, region, coastdat)]))
                temp[coastdat] = tmp
            if str(region) == 'nan':
                region = 'unknown'

            # Sum up time series for one region and divide it by the
            # capacity of the region to get a normalised time series.
            feedin[region] = temp.sum(axis=1).divide(
                    float(pp.loc[(vtype, year, region)].sum()))

        # Write table into a csv-file
        feedin.to_csv(feedin_de21.format(year=year, type=vtype.lower()))
        pwr.close()


def normalised_feedin_by_region_solar(pp, feedin_de21, feedin_coastdat,
                                      overwrite):
    vtype = 'Solar'
    de21_dir = os.path.dirname(feedin_de21.format(type=vtype.lower(),
                                                  year=2000))
    if not os.path.isdir(de21_dir):
        os.mkdir(de21_dir)

    set_list = config.get_list('solar', 'solar_sets_list')
    set_names = list()
    for my_set in set_list:
        set_names.append(cfg.get(my_set, 'pv_set_name'))

    # Check for existing output and input files
    # Only years with all sets will be used
    years = list()
    for y in range(1990, 2025):
        outfile = feedin_de21.format(year=y, type=vtype.lower())
        infiles_exist = True
        if not os.path.isfile(outfile) or overwrite:
            for name_set in set_names:
                infile = feedin_coastdat.format(year=y, type=vtype.lower(),
                                                sub=name_set)
                if not os.path.isfile(infile):
                    infiles_exist = False
            if infiles_exist:
                years.append(y)

    # Display logging warning of files will be overwritten
    if overwrite:
        logging.warning("Existing files will be overwritten.")
    else:
        logging.info("Existing files are skipped.")
    logging.info(
        "Will create {0} time series for the following years: {1}".format(
            vtype.lower(), years))

    pwr = dict()
    columns = dict()
    for year in years:
        logging.info("Processing {0}...".format(year))
        name_of_set = None
        for name_of_set in set_names:
            pwr[name_of_set] = pd.HDFStore(
                feedin_coastdat.format(year=year, sub=name_of_set,
                                       type=vtype.lower()))
            columns[name_of_set] = pwr[name_of_set]['/A1129087'].columns

        # Create DataFrame with MultiColumns to take the results
        my_index = pwr[name_of_set]['/A1129087'].index
        my_cols = pd.MultiIndex(levels=[[], [], []], labels=[[], [], []],
                                names=[u'region', u'set', u'subset'])
        feedin = pd.DataFrame(index=my_index, columns=my_cols)

        # Loop over all aggregation regions
        for region in sorted(
                pp.loc[(vtype, year)].index.get_level_values(0).unique()):
            coastdat_ids = pp.loc[(vtype, year, region)].index
            logging.info("{0} - {1} ({2})".format(
                year, region, len(coastdat_ids)))
            logging.debug("{0}".format(pp.loc[(vtype, year, region)].index))

            # Loop over all coastdat ids, that intersect with the region
            for name in set_names:
                for col in columns[name]:
                    temp = pd.DataFrame(index=my_index)
                    for coastdat in pp.loc[(vtype, year, region)].index:
                        coastdat_id = '/A{0}'.format(int(coastdat))
                        pp_inst = float(pp.loc[(vtype, year, region, coastdat)])
                        temp[coastdat_id] = (
                            pwr[name][coastdat_id][col][:8760].multiply(
                                pp_inst))
                    colname = '_'.join(col.split('_')[-3:])
                    feedin[region, name, colname] = (
                        temp.sum(axis=1).divide(float(
                            pp.loc[(vtype, year, region)].sum())))

            # Sum up time series for one region and divide it by the
            # capacity of the region to get a normalised time series.

        feedin.to_csv(feedin_de21.format(year=year, type=vtype.lower()))
        for name_of_set in set_names:
            pwr[name_of_set].close()


def normalised_feedin_by_region_hydro(c, feedin_de21, regions, overwrite=False):
    hydro_energy = pd.read_csv(
        os.path.join(c.paths['static'], 'energy_capacity_bmwi.csv'),
        header=[0, 1], index_col=[0])['Wasserkraft']['energy']

    hydro_capacity = pd.read_csv(
        os.path.join(c.paths['powerplants'], c.files['sources']),
        index_col=[0, 1, 2]).loc['Hydro'].groupby(
            'year').sum().loc[hydro_energy.index].capacity

    full_load_hours = (hydro_energy / hydro_capacity).multiply(1000)

    hydro_path = os.path.abspath(os.path.join(
        *feedin_de21.format(year=0, type='hydro').split('/')[:-1]))

    if not os.path.isdir(hydro_path):
        os.makedirs(hydro_path)

    skipped = list()
    for year in full_load_hours.index:
        filename = feedin_de21.format(year=year, type='hydro')
        if not os.path.isfile(filename) or overwrite:
            idx = pd.date_range(start="{0}-01-01 00:00".format(year),
                                end="{0}-12-31 23:00".format(year),
                                freq='H',tz='Europe/Berlin')
            feedin = pd.DataFrame(columns=regions, index=idx)
            feedin[feedin.columns] = full_load_hours.loc[year] / len(feedin)
            feedin.to_csv(filename)
        else:
            skipped.append(year)

    if len(skipped) > 0:
        logging.warning("Hydro feedin. Skipped the following years:\n" +
                        "{0}.\n".format(skipped) +
                        " Use overwrite=True to replace the files.")

    # https://shop.dena.de/fileadmin/denashop/media/Downloads_Dateien/esd/
    # 9112_Pumpspeicherstudie.pdf
    # S. 110ff


def normalised_feedin_by_region(c, overwrite=False):
    feedin_de21 = os.path.join(c.paths['feedin'], '{type}', 'de21',
                               c.pattern['feedin_de21'])
    feedin_coastdat = os.path.join(c.paths['feedin'], '{type}', '{sub}',
                                   c.pattern['feedin'])
    category = 'renewable'
    powerplants = os.path.join(c.paths[category],
                               c.pattern['grouped'].format(cat=category))

    pp = pd.read_csv(powerplants, index_col=[0, 1, 2, 3])

    regions = pp.index.get_level_values(2).unique().sort_values()

    # normalised_feedin_by_region_solar(pp, feedin_de21, feedin_coastdat,
    #                                   overwrite)
    # normalised_feedin_by_region_wind(pp, feedin_de21, feedin_coastdat,
    #                                  overwrite)
    normalised_feedin_by_region_hydro(c, feedin_de21, regions, overwrite)


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
        tilt = system['surface_tilt']

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


def create_pv_sets(set_name):
    # get module and inverter parameter from sandia database
    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    module_names = config.get_list(set_name, 'module_name')
    module_keys = config.get_list(set_name, 'module_key')
    modules = {module_keys[n]: module_names[n] for n in range(len(module_keys))}
    inverters = config.get_list(set_name, 'inverter_name')
    azimuth_angles = config.get_list(set_name, 'surface_azimuth')
    tilt_angles = config.get_list(set_name, 'surface_tilt')
    albedo_values = config.get_list(set_name, 'albedo')

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


def normalised_feedin_pv(c, weather, year, feedin_file):
    """pass"""
    if not os.path.isdir(os.path.dirname(feedin_file)):
        os.mkdir(os.path.dirname(feedin_file))
    pv_systems = create_pv_sets(c.general['solar_set'])

    pwr = pd.HDFStore(feedin_file.format(year, 'solar'), mode='w')

    latlon = pd.read_csv(os.path.join(c.paths['geometry'],
                                      c.files['grid_centroid']),
                         index_col='gid')

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


def normalised_feedin_wind(c, weather, year, feedin_file):
    """pass"""
    if not os.path.isdir(os.path.dirname(feedin_file)):
        os.mkdir(os.path.dirname(feedin_file))
    pwr = pd.HDFStore(feedin_file, mode='w')
    average_wind_speed = pd.read_csv(
        os.path.join(c.paths['weather'], c.files['average_wind_speed']),
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


def normalised_feedin_one_year(c, year, overwrite):
    """pass"""
    start = time.now()
    weather = None
    fileopen = False
    set_name = cfg.get(c.general['solar_set'], 'pv_set_name')
    feedin_pattern = os.path.join(c.paths['feedin'], '{type}', '{sub}',
                                  c.pattern['feedin'])

    f_wind = feedin_pattern.format(year=year, type='wind', sub='coastdat')
    f_solar = feedin_pattern.format(year=year, type='solar', sub=set_name)

    if not os.path.isfile(f_wind) or not os.path.isfile(f_solar) or overwrite:
        weather = pd.HDFStore(os.path.join(
            c.paths['weather'], c.pattern['weather'].format(year=year)),
            mode='r')
        fileopen = True

    txt_create = "Creating normalised {0} feedin time series for {1}."
    txt_skip = "File '{0}' exists. Skipped. "

    if not os.path.isfile(f_wind) or overwrite:
        logging.info(txt_create.format('wind', year))
        normalised_feedin_wind(c, weather, year, f_wind)
    else:
        logging.info(txt_skip.format(f_wind))

    if not os.path.isfile(f_solar) or overwrite:
        logging.info(txt_create.format('solar', year))
        normalised_feedin_pv(c, weather, year, f_solar)
    else:
        logging.info(txt_skip.format(f_solar))

    if fileopen:
        weather.close()
        logging.info("Normalised time series created: {0} - {1}".format(
            year, time.now() - start))


def normalised_feedin_by_weather(c, years=None, overwrite=False):
    """pass"""
    # Finding existing weather files.
    if years is None:
        filelist = (os.listdir(c.paths['weather']))
        years = list()
        for y in range(1970, 2020):
            if c.pattern['weather'].format(year=y) in filelist:
                years.append(y)

    for year in years:
        normalised_feedin_one_year(c, year, overwrite)


if __name__ == "__main__":
    logger.define_logging()
    cfg = config.get_configuration()
    normalised_feedin_by_region(cfg, overwrite=True)
