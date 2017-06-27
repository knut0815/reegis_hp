import pandas as pd
import numpy as np
import os
import geoplot
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as path_effects
import configuration as config


def add_grid_labels(data, plotter, label=None,
                    coord_file=None):
    p = pd.read_csv(coord_file, index_col='name')

    data['point'] = p.geom
    data['rotation'] = p.rotation

    for row in data.iterrows():
        point = geoplot.postgis2shapely([row[1].point, ])[0]
        (x, y) = plotter.basemap(point.x, point.y)
        textcolour = 'black'

        if label is None:
            text = row[0][2:4] + row[0][7:9]
        else:
            try:
                text = '  ' + str(round(row[1][label] / 1000, 1)) + '  '
            except TypeError:
                text = str(row[1][label])

            if row[1][label] == 0:
                    textcolour = 'red'

        plotter.ax.text(
            x, y, text, color=textcolour, fontsize=9.5,
            rotation=row[1].rotation,
            path_effects=[path_effects.withStroke(linewidth=3, foreground="w")])


def de21_region():
    """
    Plot of the de21 regions (offshore=blue, onshore=green).
    """
    c = config.get_configuration()
    my_df = pd.read_csv(
        os.path.join(c.paths['geometry'], c.files['region_polygons']),
        index_col='gid').sort_index()

    label_coord = os.path.join(c.paths['geometry'], c.files['region_labels'])

    offshore = geoplot.postgis2shapely(my_df.iloc[18:21].geom)
    onshore = geoplot.postgis2shapely(my_df.iloc[0:18].geom)
    plotde21 = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotde21.plot(facecolor='#badd69', edgecolor='white')
    plotde21.geometries = offshore
    plotde21.plot(facecolor='#a5bfdd', edgecolor='white')
    add_labels(my_df, plotde21, coord_file=label_coord,
               textcolour='black')
    draw_line(plotde21, (9.7, 53.4), (10.0, 53.55))
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


def de21_grid():
    c = config.get_configuration()

    plt.figure(figsize=(7, 8))
    plt.rc('legend', **{'fontsize': 16})
    plt.rcParams.update({'font.size': 16})
    plt.style.use('grayscale')

    data = pd.read_csv(os.path.join(c.paths['reegis'],
                                    c.files['data_electricity_grid']),
                       index_col='Unnamed: 0')

    geo = pd.read_csv(os.path.join(c.paths['geometry'],
                                   c.files['powerlines_lines']),
                      index_col='name')

    lines = pd.DataFrame(pd.concat([data, geo], axis=1, join='inner'))

    background = pd.read_csv(os.path.join(c.paths['geometry'],
                                          c.files['region_polygons']),
                             index_col='gid').sort_index()

    onshore = geoplot.postgis2shapely(
        background.iloc[0:18].geom)
    plotter_poly = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotter_poly.plot(facecolor='#d5ddc2', edgecolor='#7b987b')

    onshore = geoplot.postgis2shapely(
        background.iloc[18:21].geom)
    plotter_poly = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotter_poly.plot(facecolor='#ccd4dd', edgecolor='#98a7b5')

    plotter_lines = geoplot.GeoPlotter(geoplot.postgis2shapely(lines.geom),
                                       (3, 16, 47, 56))
    # plotter_lines.cmapname = 'RdBu'
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#860808'),
                                                           (1, '#3a3a48')])
    plotter_lines.data = lines.capacity
    plotter_lines.plot(edgecolor='data', linewidth=2, cmap=my_cmap)
    filename = os.path.join(c.paths['geometry'], c.files['powerlines_labels'])
    add_grid_labels(lines, plotter_lines, 'capacity', coord_file=filename)
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


def draw_line(plot_obj, start, end, color='black'):
    start_line = plot_obj.basemap(start[0], start[1])
    end_line = plot_obj.basemap(end[0], end[1])
    plt.plot([start_line[0], end_line[0]], [start_line[1], end_line[1]], '-',
             color=color)


def add_labels(data, plot_obj, column=None, coord_file=None, textcolour='blue'):
    """
    Add labels to a geoplot.

    Parameters
    ----------
    data : pandas.DataFrame
    plot_obj : geoplot.plotter
    column : str
    coord_file : str
    textcolour : str

    Returns
    -------

    """

    if coord_file is not None:
        p = pd.read_csv(coord_file, index_col='name')
        data = pd.concat([data, p], axis=1)

    for row in data.iterrows():
        if 'point' not in row[1]:
            point = geoplot.postgis2shapely([row[1].geom, ])[0].centroid
        else:
            print(row[1].point)
            point = geoplot.postgis2shapely([row[1].point, ])[0]
        (x, y) = plot_obj.basemap(point.x, point.y)
        if column is None:
            text = str(row[0])
        else:
            text = str(row[1][column])

        plot_obj.ax.text(x, y, text, color=textcolour, fontsize=12,
                         path_effects=[path_effects.withStroke(
                             linewidth=3, foreground="w")])


def plot_geocsv(filepath, idx_col, facecolor=None, edgecolor='#aaaaaa',
                bbox=(3, 16, 47, 56), labels=True, **kwargs):
    df = pd.read_csv(filepath, index_col=idx_col)

    plotter = geoplot.GeoPlotter(geoplot.postgis2shapely(df.geom), bbox)
    plotter.plot(facecolor=facecolor, edgecolor=edgecolor)

    if labels:
        add_labels(df, plotter, **kwargs)

    plt.tight_layout()
    plt.box(on=None)
    plt.show()


def coastdat_plot(data, data_col=None, lmin=0, lmax=1, n=5, digits=50,
                  legendlabel=''):
    paths, pattern, files, general = config.get_configuration()
    polygons = pd.read_csv(os.path.join(paths['geometry'], 'coastdat_grid.csv'),
                           index_col='gid')
    polygons['geom'] = geoplot.postgis2shapely(polygons.geom)

    if isinstance(data, pd.DataFrame):
        data = data[data_col]
    else:
        data_col = data.name

    polygons = pd.DataFrame(pd.concat([polygons, data], axis=1))
    polygons = polygons[pd.notnull(polygons['geom'])]

    # my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#e0f3db'),
    #                                                        (0.5, '#338e7a'),
    #                                                        (1, '#304977')])
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#ffffff'),
                                                           (1 / 7,
                                                            '#c946e5'),
                                                           (2 / 7,
                                                            '#ffeb00'),
                                                           (3 / 7,
                                                            '#26a926'),
                                                           (4 / 7,
                                                            '#c15c00'),
                                                           (5 / 7,
                                                            '#06ffff'),
                                                           (6 / 7,
                                                            '#f24141'),
                                                           (7 / 7,
                                                            '#1a2663')])

    coastdatplot = geoplot.GeoPlotter(polygons.geom, (3, 16, 47, 56))
    coastdatplot.data = (polygons[data_col].round(digits) - lmin) / (
        lmax - lmin)
    coastdatplot.plot(facecolor='data', edgecolor='data', cmap=my_cmap)
    coastdatplot.draw_legend((lmin, lmax), integer=True, extend='max',
                             cmap=my_cmap,
                             legendlabel=legendlabel,
                             number_ticks=n)
    coastdatplot.geometries = geoplot.postgis2shapely(
        pd.read_csv(os.path.join(os.path.dirname(__file__), 'data',
                                 'geometries',
                                 'polygons_de21_simple.csv')).geom)
    coastdatplot.plot(facecolor=None, edgecolor='white')
    plt.tight_layout()
    plt.box(on=None)
    return coastdatplot


def heatmap_pv_orientation():
    # import seaborn as sns
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    c = config.get_configuration()
    df = pd.read_csv(os.path.join(c.paths['analyses'],
                                  'sun.csv'),
                     index_col='Unnamed: 0')
    df = df.transpose()
    df.index = df.index.map(int)
    df = df.sort_index(ascending=False)
    # df = df.div(df.max().max())
    print(df)
    print(df.max().max())
    plt.title('year: 2003, coastDat-2 region: 1129087, ' +
              'module type: LG_LG290N1C_G3__2013_, ' +
              'inverter: ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_')
    ax = plt.gca()
    im = ax.imshow(df)  # vmin=0
    n = 10
    plt.yticks(np.arange(0, len(df.index), n), reversed(range(0, 91, 10)))
    plt.xticks(np.arange(0, len(df.columns), n), df.columns * n)
    plt.ylabel('tilt angle')
    plt.xlabel('azimuth angle')
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.2)
    plt.colorbar(im, cax=cax)
    plt.show()


def plot_module_comparison():
    c = config.get_configuration()
    df = pd.read_csv(os.path.join(c.paths['analyses'],
                                  'module_feedin.csv'),
                     index_col=0)['dc_norm']
    print(df)
    print(df.sort_values())
    # df = df[df > 943]
    df.sort_values().plot(linewidth=5, ylim=(0, df.max() + 20))
    print('avg:', df.mean())
    print('std div:', df.std())
    plt.plot((0, len(df)), (df.mean(), df.mean()), 'k-')
    plt.plot((0, len(df)), (df.mean() - df.std(), df.mean() - df.std()), 'k-.')
    plt.plot((0, len(df)), (df.mean() + df.std(), df.mean() + df.std()), 'k-.')
    plt.plot((253, 253), (0,  df.max() + 20), 'k-')
    plt.plot((479, 479), (0,  df.max() + 20), 'r-')
    plt.plot((394, 394), (0,  df.max() + 20), 'r-')
    plt.xticks(np.arange(0, len(df), 20), range(0, len(df), 20))
    plt.show()


def plot_module_comparison_ts():
    c = config.get_configuration()
    df = pd.read_csv(os.path.join(c.paths['analyses'],
                                  'module_feedin_ac_ts.csv'),
                     index_col='Unnamed: 0')

    df[['LG_LG290N1C_G3_2013_', 'Solar_Frontier_SF_160S_2013_']].plot()
    plt.show()


def plot_inverter_comparison():
    c = config.get_configuration()
    df = pd.read_csv(os.path.join(c.paths['analyses'],
                                  'sapm_inverters_feedin_full2.csv'),
                     index_col=[0])['ac']
    pv_module = df.index.name

    print(df.fillna(0).sort_values())
    len1 = len(df)
    print(df)
    df = df[df > 1]
    print(len(df) - len1)
    df.sort_values().plot(linewidth=5, ylim=(0, df.max() + 20))
    print(df.mean())
    print(df.std())
    plt.plot((0, len(df)), (df.mean(), df.mean()), 'k-')
    plt.plot((0, len(df)), (1253, 1253), 'g-')
    plt.plot((0, len(df)), (df.mean() - df.std(), df.mean() - df.std()), 'k-.')
    plt.plot((0, len(df)), (df.mean() + df.std(), df.mean() + df.std()), 'k-.')
    plt.xlabel('Number of inverters')
    plt.title("AC-output of {0} with different inverters".format(pv_module))
    plt.plot((651, 651), (0,  df.max() + 20), 'k-')
    plt.plot((1337, 1337), (0,  df.max() + 20), 'r-')
    # plt.plot((496, 496), (0,  df.max() + 20), 'r-')
    plt.xticks(np.arange(0, len(df), 50), range(0, len(df), 50))
    plt.show()


def plot_full_load_hours(year):
    paths, pattern, files, general = config.get_configuration()
    df = pd.read_csv(os.path.join(paths['analyses'], 'full_load_hours.csv'),
                     index_col=[0, 1])

    plt.figure(figsize=(8, 10))
    plt.rc('legend', **{'fontsize': 19})
    plt.rcParams.update({'font.size': 19})
    title = "Full load hours for wind in the year {0}[h].".format(year)
    coastdat_plot(df.loc[year, :]['wind'], lmax=3500, n=8, legendlabel=title)
    plt.savefig(os.path.join(paths['plots'],
                             'full_load_hours_{0}_{1}.svg'.format(year,
                                                                  'wind')))
    columns = list(df.columns)
    columns.remove('wind')

    for col in columns:
        print(col)
        plt.figure(figsize=(8, 10))
        plt.rc('legend', **{'fontsize': 19})
        plt.rcParams.update({'font.size': 19})
        title = "Full load hours for {0} [h].".format(col)
        coastdat_plot(df.loc[year, :][col], lmax=1200, lmin=500, n=8,
                      legendlabel=title)
        plt.savefig(os.path.join(paths['plots'],
                                 'full_load_hours_{0}_{1}.svg'.format(
                                     year, col)))

    fig = plt.figure(figsize=(18, 10))
    plt.rc('legend', **{'fontsize': 14})
    plt.rcParams.update({'font.size': 14})
    ax = fig.add_subplot(1, 1, 1)

    columns = ['wind', 'LG290G3_ABB_tltopt_az180_alb02',
               'SF160S_ABB_tltopt_az180_alb02']
    reg = 1129087
    one_region = df.swaplevel(0, 1, axis=0).loc[reg][columns]
    maximum = one_region.max()
    minimum = one_region.min()
    print(maximum, minimum)
    one_region.plot(kind='bar', ax=ax)
    plt.ylabel('Full load hours')
    plt.title("Full load hours in different years in region {0}".format(reg))
    lgnd = plt.legend()
    n = 0
    for col in columns:
        lgnd.get_texts()[n].set_text('{0}, min: {1}, max: {2}'.format(
            col, int(round(minimum[n] / 10) * 10),
            int(round(maximum[n] / 10) * 10)))
        n += 1
    plt.tight_layout()
    plt.savefig(os.path.join(paths['plots'],
                             'full_load_hours_region_{0}.svg'.format(reg)))

    colors = ['#6e6ead', '#ed943c', '#da7411']
    n = 0
    for col in columns:
        fig = plt.figure(figsize=(16, 9))
        ax = fig.add_subplot(1, 1, 1)
        one_region_sort = df.swaplevel(0, 1, axis=0).loc[reg][col].sort_values()
        avg = one_region_sort[0]
        one_region_sort.drop(0, inplace=True)
        one_region_sort.plot(kind='bar', ax=ax, color=colors[n])
        title = "Sorted full load hours for {0} in region {1}".format(col, reg)
        plt.title(title)
        ax.plot((-1, 18), (avg, avg), 'r-')
        n += 1
        plt.savefig(os.path.join(paths['plots'],
                                 'full_load_hours_{0}_region_{1}.svg'.format(
                                    col, reg)))


if __name__ == "__main__":
    heatmap_pv_orientation()
    # plot_full_load_hours(0)
    # plot_module_comparison()
    # de21_grid()
    # de21_region()
    # plot_inverter_comparison()
    # plot_geocsv(os.path.join('data', 'geometries', 'polygons_de21_simple.csv'),
    #             idx_col='gid',
    #             # coord_file=os.path.join('data_basic', 'centroid_region.csv')
    #             )
    # plot_geocsv(os.path.join('geometries', 'federal_states.csv'),
    #             idx_col='iso',
    #             coord_file='data_basic/label_federal_state.csv')
    # plot_geocsv('/home/uwe/geo.csv', idx_col='gid')
    # plot_pickle('data/weather/average_wind_speed_coastdat_geo.pkl',
    #             'v_wind_avg', lmax=7, n=8, digits=50)
