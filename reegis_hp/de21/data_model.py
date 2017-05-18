import os
import weather
import oemof.tools
import config as cfg
import logging
from shutil import copyfile


def load_ini_file():
    default_ini = os.path.join(os.path.dirname(__file__), 'reegis_default.ini')
    target_ini = os.path.join(os.path.expanduser("~"), '.oemof', 'reegis.ini')
    if not os.path.isfile(target_ini):
        copyfile(default_ini, target_ini)
    cfg.load_config(target_ini)


def check_path(pathname):
    if pathname is None:
        pathname = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.isdir(pathname):
        os.makedirs(pathname)
    return pathname


def extend_path(ex_path, name):
    return check_path(os.path.join(ex_path, name))


def weather_data(paths, grid_geometry,
                 weather_file, region_geometry, avg_wind_file, ovw):

    if not os.path.isdir('data'):
        os.makedirs('data')

    # Fetch non-existing weather data from a file. Use overwrite or a new
    # pattern if the region geometry changed.
    weather.fetch_coastdat2_year_from_db(paths['weather'], paths['geometry'],
                                         weather_file, region_geometry,
                                         overwrite=ovw)

    # Calculate the average wind speed for all available weather data sets.
    weather.get_average_wind_speed(paths['weather'], grid_geometry,
                                   paths['geometry'], weather_file,
                                   avg_wind_file)


if __name__ == "__main__":
    # initialise logger
    oemof.tools.logger.define_logging()

    # load ini file, copy default ini file if necessary
    load_ini_file()

    # set variable from ini file
    de21_path = dict()
    overwrite = cfg.get('general', 'overwrite')
    skip_weather = cfg.get('general', 'skip_weather')
    de21_path['basic'] = check_path(cfg.get('paths', 'basic'))
    de21_path['data'] = check_path(cfg.get('paths', 'data'))
    de21_path['weather'] = extend_path(
        de21_path[cfg.get('weather', 'path')], cfg.get('weather', 'dir'))
    de21_path['geometry'] = extend_path(
        de21_path[cfg.get('geometry', 'path')], cfg.get('geometry', 'dir'))
    grid_geometry_file = cfg.get('weather', 'grid_polygons')
    weather_file_pattern = cfg.get('weather', 'file_pattern')
    region_geometry_file = cfg.get('weather', 'clip_geometry')
    average_wind_speed_file_pattern = cfg.get('weather',
                                              'avg_wind_speed_pattern')

    # Store weather data
    if not skip_weather:
        weather_data(de21_path, grid_geometry_file, weather_file_pattern,
                     region_geometry_file, average_wind_speed_file_pattern,
                     overwrite)
