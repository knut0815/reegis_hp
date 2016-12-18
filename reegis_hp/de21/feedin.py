import pandas as pd
from matplotlib import pyplot as plt
from datetime import datetime as time
import os
import geoplot
from matplotlib.colors import LinearSegmentedColormap
from windpowerlib import basicmodel
import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.tools import cosd
import bisect
import oemof.db as db


def get_average_wind_speed():

    start = time.now()
    polygons_wkt = pd.read_csv(os.path.join(os.path.dirname(__file__),
                                            'geometries', 'coastdat_grid.csv'))
    polygons = pd.DataFrame(geoplot.postgis2shapely(polygons_wkt.geom),
                            index=polygons_wkt.gid, columns=['geom'])
    years = [1998, 2003, 2007, 2010, 2011, 2012, 2013, 2014]
    store = dict()
    for year in years:
        store[year] = pd.HDFStore('weather/coastDat2_de_{0}.h5'.format(year))
    print("Files loaded", time.now() - start)
    keys = store[1998].keys()
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
            wind_speed_avg = wind_speed_avg.append(store[year][key]['v_wind'],
                                                   verify_integrity=True)
        polygons.loc[weather_id, 'v_wind_avg'] = wind_speed_avg.mean()
    years.append(firstyear)
    print(polygons.v_wind_avg.max())
    for year in years:
        store[year].close()
    polygons.to_pickle('data/average_wind_speed_coastdat.pkl')
    polygons.v_wind_avg.to_csv('data/average_wind_speed_coastdat.csv')


def get_capacity(year):
    wind_pwr = pd.HDFStore('weather/wind_power_de_{0}.h5'.format(year))
    pv_pwr = pd.HDFStore('weather/pv_power_de_{0}.h5'.format(year))

    # my = pd.read_hdf('data/renewable_power_plants_DE.edited.hdf', 'data')
    my = pd.read_csv('data/renewable_power_plants_DE.edited.csv')
    my_index = wind_pwr[wind_pwr.keys()[0]].index
    feedin_pv = pd.DataFrame(index=my_index)
    feedin_pv_cap = pd.Series()
    feedin_wind = pd.DataFrame(index=my_index)
    feedin_wind_cap = pd.Series()

    for region in my.region.sort_values().unique():
        wind_temp = pd.DataFrame(index=my_index)
        wind_cap_temp = pd.Series()
        pv_temp = pd.DataFrame(index=my_index)
        pv_cap_temp = pd.Series()

        print(region)
        p_installed_by_coastdat_id = my.loc[my.region == region].groupby(
            ['coastdat_id', 'energy_source_level_2']).electrical_capacity.sum()

        for cd2_id, new_df in p_installed_by_coastdat_id.groupby(level=0):
            electrical_capacity = new_df.loc[cd2_id, :]
            pv_cap_temp.loc[cd2_id] = electrical_capacity.get('Solar', 0)
            pv_temp[cd2_id] = (pv_pwr['/A' + str(cd2_id)] *
                               pv_cap_temp.loc[cd2_id])
            wind_cap_temp.loc[cd2_id] = electrical_capacity.get('Wind', 0)
            wind_temp[cd2_id] = (wind_pwr['/A' + str(cd2_id)] *
                                 wind_cap_temp.loc[cd2_id])
        if str(region) == 'nan':
            region = 'unknown'
        feedin_pv_cap[region] = pv_cap_temp.sum()
        feedin_pv[region] = pv_temp.sum(axis=1) / feedin_pv_cap[region]
        feedin_wind_cap[region] = wind_cap_temp.sum()
        feedin_wind[region] = wind_temp.sum(axis=1) / feedin_wind_cap[region]

    filename = 'weather/{0}_de_{1}.csv'
    feedin_pv.to_csv(filename.format('feedin_pv', year))
    feedin_pv_cap.to_csv(filename.format('feedin_pv_cap', year))
    feedin_wind.to_csv(filename.format('feedin_wind', year))
    feedin_wind_cap.to_csv(filename.format('feedin_wind_cap', year))
    wind_pwr.close()
    pv_pwr.close()


def plot_pickle(filename, column, lmin=0, lmax=1, n=5):
    polygons = pd.read_pickle(filename)
    # my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#e0f3db'),
    #                                                        (0.5, '#338e7a'),
    #                                                        (1, '#304977')])
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#ffffff'),
                                                           (1 / 6, '#ffeb00'),
                                                           (2 / 6, '#26a926'),
                                                           (3 / 6, '#c946e5'),
                                                           (4 / 6, '#06ffff'),
                                                           (5 / 6, '#f24141'),
                                                           (6 / 6, '#1a2663')])

    coastdat_plot = geoplot.GeoPlotter(polygons.geom, (3, 16, 47, 56))
    coastdat_plot.data = (polygons[column] - lmin) / (lmax - lmin)
    coastdat_plot.plot(facecolor='data', edgecolor='data', cmap=my_cmap)
    coastdat_plot.draw_legend((lmin, lmax), integer=True, extend='max',
                              cmap=my_cmap,
                              legendlabel="Average wind speed [m/s]",
                              number_ticks=n)
    coastdat_plot.geometries = geoplot.postgis2shapely(
        pd.read_csv(os.path.join(os.path.dirname(__file__),
                                 'geometries', 'polygons_de21.csv')).geom)
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


def write_feedin_to_scenario(name, path, year):
    pv_cap = pd.read_csv(
        os.path.join('weather', 'feedin_pv_cap_de_{0}.csv'.format(year)),
        header=None, index_col=0, squeeze=True)
    pv_seq = pd.read_csv(
        os.path.join('weather', 'feedin_pv_de_{0}.csv'.format(year)))
    wind_cap = pd.read_csv(
        os.path.join('weather', 'feedin_wind_cap_de_{0}.csv'.format(year)),
        header=None, index_col=0, squeeze=True)
    wind_seq = pd.read_csv(
        os.path.join('weather', 'feedin_wind_de_{0}.csv'.format(year)))

    scenario = pd.read_csv(os.path.join(path, name + '.csv'), index_col='class')

    full_path_seq = os.path.join(path, name + '_seq')
    columns = pd.read_csv(full_path_seq + '.csv', header=1, nrows=1).columns
    tmp_csv = pd.read_csv(full_path_seq + '.csv', skiprows=5, names=columns,
                          index_col='label', parse_dates=True)
    regions = list(pv_cap.index)
    regions.remove('unknown')

    for region in regions:
        scenario.loc[scenario.label == '{0}_solar'.format(region),
                     'nominal_value'] = pv_cap[region] * 1000
        scenario.loc[scenario.label == '{0}_wind'.format(region),
                     'nominal_value'] = wind_cap[region] * 1000
        tmp_csv[region + '_solar'] = list(pv_seq[region])
        tmp_csv[region + '_wind'] = list(wind_seq[region])
    scenario.to_csv(os.path.join(path, name + '.csv'))
    add2seq(tmp_csv, full_path_seq, path)


def add2seq(tmp_csv, full_path_seq, path):
    tmp_csv.to_csv(full_path_seq + '~.csv', header=False)

    # read the current contents of the file
    f = open(full_path_seq + '~.csv')
    text = f.read()
    f.close()

    # reader header
    f = open(os.path.join(path, 'reegis_de_21.header'))
    header = f.read()
    f.close()

    # open a different file for writing
    f = open(full_path_seq + '~.csv', 'w')
    f.write(header)
    f.write(text)
    f.close()
    os.rename(full_path_seq + '~.csv', full_path_seq + '.csv')


def coastdat_id2coord():
    conn = db.connection()
    sql = "select gid, st_x(geom), st_y(geom) from coastdat.spatial;"
    results = (conn.execute(sql))
    columns = results.keys()
    data = pd.DataFrame(results.fetchall(), columns=columns)
    data.set_index('gid', inplace=True)
    data.to_csv(os.path.join('data_basic', 'id2latlon.csv'))


def normalised_feedin():
    years = [1998, 2003, 2007, 2010, 2011, 2012, 2013, 2014]

    latlon = pd.read_csv(os.path.join('data_basic', 'id2latlon.csv'),
                         index_col='gid')
    filename = 'data/average_wind_speed_coastdat.pkl'
    polygons = pd.read_pickle(filename)
    start = time.now()
    for year in years:
        print(year)
        load = pd.HDFStore('weather/coastDat2_de_{0}.h5'.format(year))
        wind_pwr = pd.HDFStore('weather/wind_power_de_{0}.h5'.format(year))
        pv_pwr = pd.HDFStore('weather/pv_power_de_{0}.h5'.format(year))

        keys = load.keys()
        for key in keys:
            weather_df = load[key]
            wind_pwr[key] = normalised_wind_power(polygons, key, weather_df)
            polygons.loc[int(key[2:]), 'full_load_hours_wka'] = (
                wind_pwr[key].sum())
            pv_pwr[key] = normalised_pv_power(latlon, key, weather_df)
            polygons.loc[int(key[2:]), 'full_load_hours_pv'] = (
                pv_pwr[key].sum())

        print(year, time.now() - start)
        load.close()
        wind_pwr.close()
        pv_pwr.close()
        polygons.to_pickle('data/full_load_hours_{0}.pkl'.format(year))

# get_average_wind_speed()
# plot_pickle('data/full_load_hours_2007.pkl', 'full_load_hours_wka', lmax=5000,
#             n=5)
plot_pickle('data/full_load_hours_1998.pkl', 'full_load_hours_pv', lmax=1000,
            lmin=700, n=4)
# plot_pickle('data/average_wind_speed_coastdat.pkl', 'v_wind_avg', lmax=7, n=7)
# normalised_feedin()
# coastdat_id2coord()
# s_name = 'reegis_de_21_test'
# s_path = 'scenarios'
# write_feedin_to_scenario(s_name, s_path, 2014)
# get_capacity(2014)
