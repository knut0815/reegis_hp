__copyright__ = "Uwe Krien"
__license__ = "GPLv3"


import config as cfg
import os


class ConfigurationDe21:
    def __init__(self):
        self.paths = dict()
        self.pattern = dict()
        self.files = dict()
        self.general = dict()
        self.url = dict()
        self.pv = dict()

        target_ini = list()
        target_ini.append(os.path.join(os.path.dirname(__file__),
                                       'de21_default.ini'))
        target_ini.append(os.path.join(os.path.dirname(__file__),
                                       'de21_scenario_default.ini'))
        target_ini.append(os.path.join(os.path.expanduser("~"),
                                       '.oemof', 'de21.ini'))
        target_ini.append(os.path.join(os.path.expanduser("~"),
                                       '.oemof', 'de21_scenario.ini'))
        cfg.load_config(target_ini)


def check_path(pathname):
    if pathname is None:
        pathname = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.isdir(pathname):
        os.makedirs(pathname)
    return pathname


def extend_path(ex_path, name):
    return check_path(os.path.join(ex_path, name))


def get_single_value(section, value):
    ConfigurationDe21()
    return cfg.get(section, value)


def get_list(section, parameter):
    try:
        my_list = cfg.get(section, parameter).split(',')
        my_list = [x.strip() for x in my_list]

    except AttributeError:
        my_list = list((cfg.get(section, parameter),))
    return my_list


def create_entries_from_list(dc, section, list_name):
    names = get_list(section, list_name)
    dc[list_name] = names
    for name in names:
        dc[name] = cfg.get(section, name)


def get_configuration():
    # initialise class
    c = ConfigurationDe21()

    # set variables from ini file
    #  ********* general ******************************************************
    c.general['overwrite'] = cfg.get('general', 'overwrite')
    c.general['skip_weather'] = cfg.get('general', 'skip_weather')
    c.general['skip_re_power_plants'] = cfg.get('general',
                                                'skip_re_power_plants')
    c.general['skip_conv_power_plants'] = cfg.get('general',
                                                  'skip_conv_power_plants')
    c.general['skip_feedin_weather'] = cfg.get('general', 'skip_feedin_weather')
    c.general['skip_feedin_region'] = cfg.get('general', 'skip_feedin_region')
    c.general['skip_time_series'] = cfg.get('general', 'skip_time_series')

    # ********* download *****************************************************
    c.url['conventional_data'] = cfg.get('download', 'url_conventional_data')
    c.url['conventional_readme'] = cfg.get('download',
                                           'url_conventional_readme')
    c.url['conventional_json'] = cfg.get('download', 'url_conventional_json')
    c.url['renewable_data'] = cfg.get('download', 'url_renewable_data')
    c.url['renewable_readme'] = cfg.get('download', 'url_renewable_readme')
    c.url['renewable_json'] = cfg.get('download', 'url_renewable_json')
    c.url['time_series_data'] = cfg.get('download', 'url_timeseries_data')
    c.url['time_series_readme'] = cfg.get('download', 'url_timeseries_readme')
    c.url['time_series_json'] = cfg.get('download', 'url_timeseries_json')
    c.url['bmwi_energiedaten'] = cfg.get('download', 'url_bmwi_energiedaten')

    # ********* paths ********************************************************
    c.paths['basic'] = check_path(cfg.get('paths', 'basic'))
    c.paths['data'] = check_path(cfg.get('paths', 'data'))
    c.paths['messages'] = extend_path(
        c.paths[cfg.get('paths', 'msg_path')], cfg.get('paths', 'msg_dir'))

    # ********* general sources **********************************************
    c.paths['general'] = extend_path(
        c.paths[cfg.get('general_sources', 'path')],
        cfg.get('general_sources', 'dir'))
    c.files['bmwi_energiedaten'] = cfg.get(
        'general_sources', 'bmwi_energiedaten')
    c.files['vg250_ew_shp'] = cfg.get('general_sources', 'vg250_ew_shp')
    c.files['vg250_ew_zip'] = cfg.get('general_sources', 'vg250_ew_zip')

    # ********* static sources ************************************************
    c.paths['static'] = extend_path(
        c.paths[cfg.get('static_sources', 'path')],
        cfg.get('static_sources', 'dir'))
    c.files['demand_share'] = cfg.get('static_sources', 'demand_share')
    c.files['data_electricity_grid'] = cfg.get('static_sources',
                                               'data_electricity_grid')
    c.files['patch_offshore_wind'] = cfg.get('static_sources',
                                             'patch_offshore_wind')
    c.files['znes_flens'] = cfg.get('static_sources', 'znes_flens_data')

    # ********* weather ******************************************************
    c.paths['weather'] = extend_path(
        c.paths[cfg.get('weather', 'path')], cfg.get('weather', 'dir'))
    c.files['grid_geometry'] = cfg.get('weather', 'grid_polygons')
    c.files['region_geometry'] = cfg.get('weather', 'clip_geometry')
    c.pattern['weather'] = cfg.get('weather', 'file_pattern')
    c.files['average_wind_speed'] = cfg.get('weather', 'avg_wind_speed_file')

    # ********* geometry *****************************************************
    c.paths['geometry'] = extend_path(
        c.paths[cfg.get('geometry', 'path')], cfg.get('geometry', 'dir'))
    c.files['federal_states_centroid'] = cfg.get('geometry',
                                                 'federalstates_centroid')
    c.files['federal_states_polygon'] = cfg.get('geometry',
                                                'federalstates_polygon')
    c.files['region_polygons'] = cfg.get('geometry',
                                         'region_polygons')
    c.files['region_polygons_simple'] = cfg.get('geometry',
                                                'region_polygons_simple')
    c.files['region_labels'] = cfg.get('geometry', 'region_labels')
    c.files['powerlines_lines'] = cfg.get('geometry', 'powerlines_lines')
    c.files['powerlines_labels'] = cfg.get('geometry', 'powerlines_labels')
    c.files['coastdatgrid_centroids'] = cfg.get('geometry',
                                                'coastdatgrid_centroids')
    c.files['coastdatgrid_polygons'] = cfg.get('geometry',
                                               'coastdatgrid_polygons')
    c.files['postcode'] = cfg.get('geometry', 'postcode_polygons')

    # ********* power plants *************************************************
    c.paths['powerplants'] = extend_path(
        c.paths[cfg.get('powerplants', 'path')],
        cfg.get('powerplants', 'dir'))
    c.paths['conventional'] = extend_path(
        c.paths[cfg.get('conventional', 'path')],
        cfg.get('conventional', 'dir'))
    c.paths['renewable'] = extend_path(
        c.paths[cfg.get('renewable', 'path')],
        cfg.get('renewable', 'dir'))
    c.pattern['original'] = cfg.get('powerplants', 'original_file_pattern')
    c.pattern['fixed'] = cfg.get('powerplants', 'fixed_file_pattern')
    c.pattern['prepared'] = cfg.get('powerplants', 'prepared_csv_file_pattern')
    c.pattern['grouped'] = cfg.get('powerplants', 'grouped_file_pattern')
    c.pattern['readme'] = cfg.get('powerplants', 'readme_file_pattern')
    c.pattern['json'] = cfg.get('powerplants', 'json_file_pattern')
    c.pattern['shp'] = cfg.get('powerplants', 'shp_file_pattern')
    c.files['transformer'] = cfg.get('powerplants', 'transformer_file')
    c.files['sources'] = cfg.get('powerplants', 'sources_file')

    # ********* storages ******************************************************
    c.paths['storages'] = extend_path(
        c.paths[cfg.get('storages', 'path')],
        cfg.get('storages', 'dir'))
    c.files['hydro_storages'] = cfg.get('storages', 'hydro_storages_file')
    c.files['hydro_storages_de21'] = cfg.get(
        'storages', 'grouped_storages_file')

    # ********* transmission **************************************************
    c.paths['transmission'] = extend_path(
        c.paths[cfg.get('transmission', 'path')],
        cfg.get('transmission', 'dir'))
    c.files['transmission_data'] = cfg.get('transmission',
                                           'transmission_data_file')
    c.files['transmission_de21'] = cfg.get('transmission',
                                           'transmission_de21_file')
    c.general['security_factor'] = cfg.get('transmission', 'security_factor')
    c.general['current_max'] = cfg.get('transmission', 'current_max')

    # ********* commodity sources *********************************************
    c.paths['commodity'] = extend_path(
        c.paths[cfg.get('commodity_sources', 'path')],
        cfg.get('commodity_sources', 'dir'))
    c.files['commodity_sources'] = cfg.get('commodity_sources',
                                           'commodity_sources_file')

    # ********* time series ***************************************************
    c.paths['time_series'] = extend_path(
        c.paths[cfg.get('time_series', 'path')],
        cfg.get('time_series', 'dir'))
    c.files['time_series_original'] = cfg.get('time_series', 'original_file')
    c.files['time_series_de'] = cfg.get('time_series', 'de_file')
    c.files['renewables_time_series'] = cfg.get('time_series',
                                                'renewables_file')
    c.files['load_time_series'] = cfg.get('time_series', 'load_file')
    c.files['time_series_readme'] = cfg.get('time_series', 'readme_file')
    c.files['time_series_json'] = cfg.get('time_series', 'json_file')

    # ********* demand ********************************************************
    c.paths['demand'] = extend_path(
        c.paths[cfg.get('demand', 'path')],
        cfg.get('demand', 'dir'))
    c.files['demand'] = cfg.get('demand', 'demand_file')

    # ********* feedin ********************************************************
    c.paths['feedin'] = extend_path(
        c.paths[cfg.get('feedin', 'path')],
        cfg.get('feedin', 'dir'))
    c.pattern['feedin'] = cfg.get('feedin', 'feedin_file_pattern')
    c.pattern['feedin_de21'] = cfg.get('feedin', 'feedin_de21_pattern')
    c.general['solar_set'] = cfg.get('solar', 'solar_set')

    # ********* analyses ******************************************************
    c.paths['analysis'] = extend_path(
        c.paths[cfg.get('analysis', 'path')],
        cfg.get('analysis', 'dir'))

    # ********* external ******************************************************
    c.paths['external'] = extend_path(
        c.paths[cfg.get('external', 'path')],
        cfg.get('external', 'dir'))

    # ********* plots *********************************************************
    c.paths['plots'] = extend_path(
        c.paths[cfg.get('plots', 'path')],
        cfg.get('plots', 'dir'))

    # ********* scenario_data *************************************************
    c.paths['scenario_data'] = extend_path(
        c.paths[cfg.get('scenario_data', 'path')],
        cfg.get('scenario_data', 'dir'))

    c.general['name'] = cfg.get('general', 'name')
    c.general['year'] = cfg.get('general', 'year')
    c.general['weather_year'] = cfg.get('general', 'weather_year')
    c.general['demand_year'] = cfg.get('general', 'demand_year')
    c.general['optimisation_target'] = cfg.get('general', 'optimisation_target')
    c.general['local_sources'] = get_list('general', 'local_commodity_sources')

    c.files['renewable_capacities'] = cfg.get('files', 'renewable_capacities')

    create_entries_from_list(c.pv, 'pv', 'module_inverter_types')
    create_entries_from_list(c.pv, 'pv', 'orientation_types')

    return c