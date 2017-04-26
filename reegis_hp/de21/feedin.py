import pandas as pd
from matplotlib import pyplot as plt
from datetime import datetime as time
import os
try:
    import geoplot
except ImportError:
    geoplot = None
from matplotlib.colors import LinearSegmentedColormap
from windpowerlib import basicmodel
import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.tools import cosd
import bisect
try:
    import oemof.db as db
except ImportError:
    db = None
import logging
from oemof.tools import logger
import calendar


def get_average_wind_speed():
    """
    Get average wind speed over all years for each coastdat region. This can be
    used to select the appropriate wind turbine for each region
    (strong/low wind turbines).
    """
    start = time.now()
    weather_path = os.path.join('data', 'weather')

    # Finding existing weather files.
    filelist = (os.listdir(weather_path))
    years = list()
    for y in range(1970, 2020):
        if 'coastDat2_de_{0}.h5'.format(y) in filelist:
            years.append(y)

    # Loading coastdat-grid as shapely geometries.
    polygons_wkt = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data',
                                            'geometries', 'coastdat_grid.csv'))
    polygons = pd.DataFrame(geoplot.postgis2shapely(polygons_wkt.geom),
                            index=polygons_wkt.gid, columns=['geom'])

    # Opening all weather files
    store = dict()
    for year in years:
        store[year] = pd.HDFStore(os.path.join(
            weather_path, 'coastDat2_de_{0}.h5'.format(year)), mode='r')
    print("Files loaded", time.now() - start)
    keys = store[years[0]].keys()
    print("Keys loaded", time.now() - start)
    firstyear = years[0]
    years.remove(firstyear)
    n = len(list(keys))
    for key in keys:
        n -= 1
        if n % 100 == 0:
            print(n)
        weather_id = int(key[2:])
        wind_speed_avg = store[firstyear][key]['v_wind']
        for year in years:
            # Remove entries if year has to many entries.
            if calendar.isleap(year):
                h_max = 8784
            else:
                h_max = 8760
            ws = store[year][key]['v_wind']
            surplus = h_max - len(ws)
            if surplus < 0:
                ws = ws.ix[:surplus]
            wind_speed_avg = wind_speed_avg.append(ws, verify_integrity=True)
        polygons.loc[weather_id, 'v_wind_avg'] = wind_speed_avg.mean()
    years.append(firstyear)
    print(polygons.v_wind_avg.max())
    for year in years:
        store[year].close()
    polygons.to_pickle(os.path.join(weather_path,
                                    'average_wind_speed_coastdat_geo.pkl'))
    polygons.v_wind_avg.to_csv(os.path.join(
        weather_path, 'average_wind_speed_coastdat.csv'))


def time_series_by_region(overwrite=False):
    source_path = os.path.join('data', 'powerplants', 'grouped',
                               'renewable_cap.csv')
    feedin_in_path = os.path.join('data', 'feedin', 'coastdat')
    feedin_out_path = os.path.join('data', 'feedin', 'de21')
    feedin_in_file = '{0}_feedin_coastdat_de_normalised_{1}.h5'
    feedin_in = os.path.join(feedin_in_path, feedin_in_file)
    feedin_out = os.path.join(feedin_out_path, '{0}_feedin_de21_{1}.csv')
    df = pd.read_csv(source_path, index_col=[0, 1, 2, 3])

    if not os.path.isdir(os.path.join('data', 'feedin', 'de21')):
        os.makedirs(os.path.join('data', 'feedin', 'de21'))

    for vtype in ['Solar', 'Wind']:
        filelist = (os.listdir(feedin_in_path))
        years = list()

        for y in range(1970, 2020):
            if (not os.path.isfile(feedin_out.format(y, vtype.lower()))) or (
                    overwrite):
                if feedin_in_file.format(y, vtype.lower()) in filelist:
                    years.append(y)
        if overwrite:
            logging.warning("Existing files will be overwritten.")
        else:
            logging.info("Existing files are skipped.")
        logging.info(
            "Will create {0} time series for the following years: {1}".format(
                vtype.lower(), years))
        for year in years:
            pwr = pd.HDFStore(feedin_in.format(year, vtype.lower()))
            my_index = pwr[pwr.keys()[0]].index
            feedin = pd.DataFrame(index=my_index)
            for region in sorted(
                    df.loc[(vtype, year)].index.get_level_values(0).unique()):
                temp = pd.DataFrame(index=my_index)
                logging.info(region)
                for coastdat in df.loc[(vtype, year, region)].index:
                    # Multiply time series (normalised to 1kW) with capacity(kW)
                    temp[coastdat] = pwr['/A' + str(int(coastdat))].multiply(
                        float(df.loc[(vtype, year, region, coastdat)]))
                if str(region) == 'nan':
                    region = 'unknown'
                # Sum up time series for one region and divide it by the
                # capacity of the region to get a normalised time series.
                feedin[region] = temp.sum(axis=1).divide(
                    float(df.loc[(vtype, year, region)].sum()))

            feedin.to_csv(feedin_out.format(year, vtype.lower()))
            pwr.close()


def plot_pickle(filename, column, lmin=0, lmax=1, n=5, digits=50):
    polygons = pd.read_pickle(filename)
    print(polygons)
    # my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#e0f3db'),
    #                                                        (0.5, '#338e7a'),
    #                                                        (1, '#304977')])
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#ffffff'),
                                                           (1 / 7, '#c946e5'),
                                                           (2 / 7, '#ffeb00'),
                                                           (3 / 7, '#26a926'),
                                                           (4 / 7, '#c15c00'),
                                                           (5 / 7, '#06ffff'),
                                                           (6 / 7, '#f24141'),
                                                           (7 / 7, '#1a2663')])

    coastdat_plot = geoplot.GeoPlotter(polygons.geom, (3, 16, 47, 56))
    coastdat_plot.data = (polygons[column].round(digits) - lmin) / (lmax - lmin)
    coastdat_plot.plot(facecolor='data', edgecolor='data', cmap=my_cmap)
    coastdat_plot.draw_legend((lmin, lmax), integer=True, extend='max',
                              cmap=my_cmap,
                              legendlabel="Average wind speed [m/s]",
                              number_ticks=n)
    coastdat_plot.geometries = geoplot.postgis2shapely(
        pd.read_csv(os.path.join(os.path.dirname(__file__), 'data',
                                 'geometries', 'polygons_de21_simple.csv')).geom)
    coastdat_plot.plot(facecolor=None, edgecolor='white')
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


def normalised_wind_power(polygons, key, weather_df):
    coastdat2 = {
        'dhi': 0,
        'dirhi': 0,
        'pressure': 0,
        'temp_air': 2,
        'v_wind': 10,
        'Z0': 0}

    wind_power_plants = {
        1: {'h_hub': 135,
            'd_rotor': 127,
            'wind_conv_type': 'ENERCON E 126 7500',
            'nominal_power': 7500000},
        2: {'h_hub': 78,
            'd_rotor': 82,
            'wind_conv_type': 'ENERCON E 82 3000',
            'nominal_power': 3000000},
        3: {'h_hub': 98,
            'd_rotor': 82,
            'wind_conv_type': 'ENERCON E 82 2300',
            'nominal_power': 2300000},
        4: {'h_hub': 138,
            'd_rotor': 82,
            'wind_conv_type': 'ENERCON E 82 2300',
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
    wpp = basicmodel.SimpleWindTurbine(**wind_power_plants[wka_class])
    polygons.loc[int(key[2:]), 'wind_conv_type'] = wind_power_plants[wka_class][
        'wind_conv_type']
    polygons.loc[int(key[2:]), 'wind_conv_class'] = wka_class
    return wpp.turbine_power_output(
        weather=weather_df, data_height=coastdat2).div(
            wind_power_plants[wka_class]['nominal_power'])


def normalised_pv_power(latlon, key, weather_df):
    weather_df['temp_air'] = weather_df.temp_air - 273.15
    times = weather_df.index
    # get module and inverter parameter from sandia database
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    location = {
        # 'altitude': 34,
        'latitude': latlon.loc[int(key[2:]), 'st_y'],
        'longitude': latlon.loc[int(key[2:]), 'st_x'],
        }

    # own module parameters
    invertername = 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_'
    yingli210 = {
        'module_parameters': sandia_modules['Yingli_YL210__2008__E__'],
        'inverter_parameters': sapm_inverters[invertername],
        'surface_azimuth': 180,
        'surface_tilt': 60,
        'albedo': 0.2,
        }
    p_max_power = (sandia_modules['Yingli_YL210__2008__E__'].Impo *
                   sandia_modules['Yingli_YL210__2008__E__'].Vmpo)
    weather_df['ghi'] = weather_df.dirhi + weather_df.dhi

    if weather_df.get('dni') is None:
        weather_df['dni'] = (weather_df.ghi - weather_df.dhi) / cosd(
            Location(**location).get_solarposition(times).zenith.clip(upper=90))

    # pvlib's ModelChain
    mc = ModelChain(PVSystem(**yingli210),
                    Location(**location),
                    orientation_strategy='south_at_latitude_tilt')
    mc.complete_irradiance(weather_df.index, weather=weather_df)
    mc.run_model(times)
    mc.ac.fillna(0).clip(0)
    return mc.ac.fillna(0).clip(0).div(p_max_power)


def coastdat_id2coord():
    """
    Creating a file with the latitude and longitude for all coastdat2 data sets.
    """
    conn = db.connection()
    sql = "select gid, st_x(geom), st_y(geom) from coastdat.spatial;"
    results = (conn.execute(sql))
    columns = results.keys()
    data = pd.DataFrame(results.fetchall(), columns=columns)
    data.set_index('gid', inplace=True)
    data.to_csv(os.path.join('data', 'basic', 'id2latlon.csv'))


def normalised_feedin(years=None, overwrite=False):
    """pass"""

    # Finding existing weather files.
    weather_path = os.path.join('data', 'weather')
    avg_wind = os.path.join(weather_path, 'average_wind_speed_coastdat_geo.pkl')
    feedin_path = os.path.join('data', 'feedin', 'coastdat')
    feedin_full = os.path.join(
        feedin_path, '{0}_feedin_coastdat_de_normalised_{1}.h5')

    if not os.path.isdir(os.path.join('data', 'feedin')):
        os.makedirs(os.path.join('data', 'feedin'))
    if not os.path.isdir(os.path.join('data', 'feedin', 'coastdat')):
        os.makedirs(os.path.join('data', 'feedin', 'coastdat'))

    if years is None:
        filelist = (os.listdir(weather_path))
        years = list()
        for y in range(1970, 2020):
            if 'coastDat2_de_{0}.h5'.format(y) in filelist:
                years.append(y)

    latlon = pd.read_csv(os.path.join('data', 'basic', 'id2latlon.csv'),
                         index_col='gid')

    polygons = pd.read_pickle(avg_wind)
    start = time.now()
    logging.info("Creating normalised feedin time series.")
    for year in years:
        file1 = feedin_full.format(year, 'wind')
        file2 = feedin_full.format(year, 'solar')
        if not os.path.isfile(file1) or not os.path.isfile(file2) or overwrite:
            load = pd.HDFStore(os.path.join(
                weather_path, 'coastDat2_de_{0}.h5').format(year), mode='r')
            wind_pwr = pd.HDFStore(feedin_full.format(year, 'wind'), mode='w')
            pv_pwr = pd.HDFStore(feedin_full.format(year, 'solar'), mode='w')

            keys = load.keys()
            length = len(keys)
            for key in keys:
                length -= 1
                if length % 100 == 0:
                    logging.info('{0} - {1}'.format(year, length))
                weather_df = load[key]
                wind_pwr[key] = normalised_wind_power(polygons, key, weather_df)
                polygons.loc[int(key[2:]), 'full_load_hours_wka'] = (
                    wind_pwr[key].sum())
                pv_pwr[key] = normalised_pv_power(latlon, key, weather_df)
                polygons.loc[int(key[2:]), 'full_load_hours_solar'] = (
                    pv_pwr[key].sum())

            logging.info("Normalised time series created: {0} - {1}".format(
                year, time.now() - start))
            load.close()
            wind_pwr.close()
            pv_pwr.close()
            polygons.to_pickle(os.path.join(
                feedin_path, '{0}_full_load_hours_solar_wind.pkl'.format(year)))


def merge_tables(overwrite):
    feedin_in_path = os.path.join('data', 'feedin', 'de21')
    feedin_in_file = '{0}_feedin_de21_{1}.csv'
    feedin_in = os.path.join(feedin_in_path, feedin_in_file)

    filelist = (os.listdir(feedin_in_path))
    years = list()

    for y in range(1970, 2020):
        if (not os.path.isfile(feedin_in.format(y, 'all'))) or (
                overwrite):
            if (feedin_in_file.format(y, 'wind') in filelist) and (
                   feedin_in_file.format(y, 'solar') in filelist):
                years.append(y)
    pwr = dict()
    logging.info("Merging feedin files of the following years: {0}".format(
        years))
    for year in years:
        for vtype in ['wind', 'solar']:
            pwr[vtype] = pd.read_csv(feedin_in.format(year, vtype),
                                     index_col='Unnamed: 0')
        my_index = pwr['wind'][pwr['wind'].keys()[0]].index
        my_cols = pd.MultiIndex(
            levels=[[1], [2]], labels=[[0], [0]], names=['vtype',
                                                         'region'])

        feedall = pd.DataFrame(index=my_index, columns=my_cols)

        del feedall[1, 2]
        for vtype in ['wind', 'solar']:
            for reg in pwr['wind'].columns:
                try:
                    feedall[(vtype, reg)] = pwr[vtype][reg]
                except KeyError:
                    pass

        feedall.to_csv(feedin_in.format(year, 'all'))


def create_feedin_series(overwrite=False):
    """pass"""
    start = time.now()
    weather_path = os.path.join('data', 'weather')

    # Creating file with average wind speed for each coastdat id
    avg1 = os.path.join(weather_path, 'average_wind_speed_coastdat_geo.pkl')
    avg2 = os.path.join(weather_path, 'average_wind_speed_coastdat.csv')
    logging.info("Average wind speed: {0}".format(time.now() - start))
    if not os.path.isfile(avg1) or not os.path.isfile(avg2) or overwrite:
        get_average_wind_speed()

    normalised_feedin(overwrite=overwrite)
    time_series_by_region(overwrite=overwrite)
    merge_tables(overwrite=overwrite)


def feedin_source_region(year):
    feedin_out = os.path.join('data', 'feedin', 'de21',
                              '{0}_feedin_de21_all.csv')
    return pd.read_csv(feedin_out.format(year), header=[0, 1], parse_dates=True,
                       index_col=0)

if __name__ == "__main__":
    logger.define_logging()
    # get_average_wind_speed()
    # create_feedin_series(overwrite=False)
    # plot_pickle('data/feedin/coastdat/2007_full_load_hours_solar_wind.pkl',
    #             'full_load_hours_wka',
    #             lmax=5000, n=5)
    # plot_pickle('data/full_load_hours_1998.pkl', 'full_load_hours_pv',
    #             lmax=1000, lmin=700, n=4)
    plot_pickle('data/weather/average_wind_speed_coastdat_geo.pkl',
                'v_wind_avg', lmax=7, n=8, digits=50)
    # coastdat_id2coord()
    # s_name = 'reegis_de_21_test'
    # s_path = 'scenarios'
    # write_feedin_to_scenario(s_name, s_path, 2014)
