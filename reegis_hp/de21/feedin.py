import pandas as pd
from matplotlib import pyplot as plt
from datetime import datetime as time
import os
import geoplot
from matplotlib.colors import LinearSegmentedColormap
from windpowerlib import basicmodel
import bisect


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
            a = store[year][key]['v_wind']
            wind_speed_avg = wind_speed_avg.append(store[year][key]['v_wind'],
                                                   verify_integrity=True)
        polygons.loc[weather_id, 'v_wind_avg'] = wind_speed_avg.mean()
    years.append(firstyear)
    print(polygons.v_wind_avg.max())
    for year in years:
        store[year].close()
    polygons.to_pickle('data/average_wind_speed_coastdat.pkl')
    polygons.v_wind_avg.to_csv('data/average_wind_speed_coastdat.csv')


def get_capacity():
    my = pd.read_hdf('data/renewable_power_plants_DE.edited.hdf', 'data')
    p_installed_by_coastdat_id = my.groupby(
        ['coastdat_id', 'energy_source_level_2']).electrical_capacity.sum()

    for cd2_id, new_df in p_installed_by_coastdat_id.groupby(level=0):
        a = new_df.loc[cd2_id, :]
        b = a.get('Solar', 0)


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
    coastdat_plot.data = polygons[column] / lmax
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


def normalised_feedin():
    years = [1998, 2003, 2007, 2010, 2011, 2012, 2013, 2014]
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

    pv_power_plantsite = {
        'module_name': 'Yingli_YL210__2008__E__',
        'azimuth': 0,
        'tilt': 30,
        'albedo': 0.2,
    }

    avg_wind2type = pd.Series({
        1.5: 4,
        2.5: 3,
        3.5: 2,
        4.5: 1,
        5.5: 1,
        100: 1,
    })

    filename = 'data/average_wind_speed_coastdat.pkl'
    polygons = pd.read_pickle(filename)
    start = time.now()
    for year in years:
        print(year)
        load = pd.HDFStore('weather/coastDat2_de_{0}.h5'.format(year))
        store = pd.HDFStore('weather/wind_power_de_{0}.h5'.format(year))
        keys = load.keys()
        for key in keys:
            avg_wind_speed = polygons.loc[int(key[2:]), 'v_wind_avg']
            wka_class = avg_wind2type.iloc[
                bisect.bisect_right(list(avg_wind2type.index), avg_wind_speed)]
            wpp = basicmodel.SimpleWindTurbine(**wind_power_plants[wka_class])
            weather_df = load[key]
            store[key] = (wpp.turbine_power_output(weather=weather_df,
                                                   data_height=coastdat2))
            polygons.loc[int(key[2:]), 'full_load_hours'] = (
                store[key].sum() /
                wind_power_plants[wka_class]['nominal_power'])
        print(year, time.now() - start)
        load.close()
        store.close()
        polygons.to_pickle('data/full_load_hours_{0}.pkl'.format(year))


# get_average_wind_speed()
plot_pickle('data/full_load_hours_2007.pkl', 'full_load_hours', lmax=9000, n=5)
plot_pickle('data/average_wind_speed_coastdat.pkl', 'v_wind_avg', lmax=7, n=7)
# normalised_feedin()
