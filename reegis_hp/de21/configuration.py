__copyright__ = "Uwe Krien"
__license__ = "GPLv3"


import config as cfg
import os
import logging
from shutil import copyfile


def load_ini_file():
    default_ini = os.path.join(os.path.dirname(__file__), 'reegis_default.ini')
    target_ini = os.path.join(os.path.expanduser("~"), '.oemof', 'reegis.ini')
    if not os.path.isfile(target_ini):
        copyfile(default_ini, target_ini)
        logging.info("Default ini file copied to {0}".format(target_ini))
        logging.info("Adapt it to your needs.")
    cfg.load_config(target_ini)


def check_path(pathname):
    if pathname is None:
        pathname = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.isdir(pathname):
        os.makedirs(pathname)
    return pathname


def extend_path(ex_path, name):
    return check_path(os.path.join(ex_path, name))


def get_configuration():
    # load ini file, copy default ini file if necessary
    load_ini_file()

    paths = dict()
    pattern = dict()
    files = dict()
    general = dict()

    # set variables from ini file
    #  ********* general ******************************************************
    general['overwrite'] = cfg.get('general', 'overwrite')
    general['skip_weather'] = cfg.get('general', 'skip_weather')
    general['skip_re_power_plants'] = cfg.get('general', 'skip_re_power_plants')
    general['skip_conv_power_plants'] = cfg.get('general',
                                                'skip_conv_power_plants')
    general['skip_feedin_weather'] = cfg.get('general', 'skip_feedin_weather')
    general['skip_feedin_region'] = cfg.get('general', 'skip_feedin_region')

    # ********* paths ********************************************************
    paths['basic'] = check_path(cfg.get('paths', 'basic'))
    paths['data'] = check_path(cfg.get('paths', 'data'))
    paths['messages'] = extend_path(
        paths[cfg.get('paths', 'msg_path')], cfg.get('paths', 'msg_dir'))

    # ********* weather ******************************************************
    paths['weather'] = extend_path(
        paths[cfg.get('weather', 'path')], cfg.get('weather', 'dir'))
    files['grid_geometry'] = cfg.get('weather', 'grid_polygons')
    files['grid_centroid'] = cfg.get('weather', 'grid_centroid')
    files['region_geometry'] = cfg.get('weather', 'clip_geometry')
    pattern['weather'] = cfg.get('weather', 'file_pattern')
    files['average_wind_speed'] = cfg.get('weather', 'avg_wind_speed_file')

    # ********* geometry *****************************************************
    paths['geometry'] = extend_path(
        paths[cfg.get('geometry', 'path')], cfg.get('geometry', 'dir'))

    # ********* power plants *************************************************
    paths['powerplants'] = extend_path(
        paths[cfg.get('powerplants', 'path')],
        cfg.get('powerplants', 'dir'))
    paths['powerplants_basic'] = extend_path(
        paths[cfg.get('powerplants', 'in_path')],
        cfg.get('powerplants', 'in_dir'))
    paths['conventional'] = extend_path(
        paths[cfg.get('conventional', 'path')],
        cfg.get('conventional', 'dir'))
    paths['renewable'] = extend_path(
        paths[cfg.get('renewable', 'path')],
        cfg.get('renewable', 'dir'))
    pattern['original'] = cfg.get('powerplants', 'original_file_pattern')
    pattern['fixed'] = cfg.get('powerplants', 'fixed_file_pattern')
    pattern['info'] = cfg.get('powerplants', 'info_file_pattern')
    pattern['prepared'] = cfg.get('powerplants', 'prepared_csv_file_pattern')
    pattern['prepared_h5'] = cfg.get('powerplants', 'prepared_hdf_file_pattern')
    pattern['grouped'] = cfg.get('powerplants', 'grouped_file_pattern')
    pattern['readme'] = cfg.get('powerplants', 'readme_file_pattern')
    pattern['json'] = cfg.get('powerplants', 'json_file_pattern')
    pattern['shp'] = cfg.get('powerplants', 'shp_file_pattern')

    # ********* feedin ********************************************************
    paths['feedin'] = extend_path(
        paths[cfg.get('feedin', 'path')],
        cfg.get('feedin', 'dir'))
    pattern['feedin'] = cfg.get('feedin', 'feedin_file_pattern')
    pattern['feedin_de21'] = cfg.get('feedin', 'feedin_de21_pattern')

    # ********* analyses ******************************************************
    paths['analyses'] = extend_path(
        paths[cfg.get('analyses', 'path')],
        cfg.get('analyses', 'dir'))

    # ********* plots *********************************************************
    paths['plots'] = extend_path(
        paths[cfg.get('plots', 'path')],
        cfg.get('plots', 'dir'))

    return paths, pattern, files, general
