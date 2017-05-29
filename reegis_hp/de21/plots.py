import pandas as pd
import tools
import os
import geoplot
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as path_effects


def add_grid_labels(data, plotter, label=None,
                    coord_file='data/geometries/coord_lines.csv'):
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
            x, y, text, color=textcolour, fontsize=9.5, rotation=row[1].rotation,
            path_effects=[path_effects.withStroke(linewidth=3, foreground="w")])


def de21_region():
    """
    Plot of the de21 regions (offshore=blue, onshore=green).
    """
    my_df = pd.read_csv(
        os.path.join(os.path.dirname(__file__), 'data', 'geometries',
                     'polygons_de21.csv'),
        index_col='gid')

    label_coord = os.path.join(os.path.dirname(__file__),
                                     'data', 'geometries', 'coord_region.csv')

    offshore = geoplot.postgis2shapely(my_df.iloc[18:21].geom)
    onshore = geoplot.postgis2shapely(my_df.iloc[0:18].geom)
    plotde21 = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotde21.plot(facecolor='#badd69', edgecolor='white')
    plotde21.geometries = offshore
    plotde21.plot(facecolor='#a5bfdd', edgecolor='white')
    tools.add_labels(my_df, plotde21, coord_file=label_coord,
                     textcolour='black')
    tools.draw_line(plotde21, (9.7, 53.4), (10.0, 53.55))
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


def de21_grid():
    plt.figure(figsize=(7, 8))
    plt.rc('legend', **{'fontsize': 16})
    plt.rcParams.update({'font.size': 16})
    plt.style.use('grayscale')

    data = pd.read_csv(os.path.join('data', 'grid', 'de21_transmission.csv'),
                       index_col='Unnamed: 0')

    geo = pd.read_csv('data/geometries/lines_de21.csv', index_col='name')

    lines = pd.DataFrame(pd.concat([data, geo], axis=1, join='inner'))
    print(lines)

    background = pd.read_csv('data/geometries/polygons_de21_simple.csv',
                             index_col='gid')

    onshore = geoplot.postgis2shapely(
        background[background['Unnamed: 0'] > 2].geom)
    plotter_poly = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotter_poly.plot(facecolor='#d5ddc2', edgecolor='#7b987b')

    onshore = geoplot.postgis2shapely(
        background[background['Unnamed: 0'] < 3].geom)
    plotter_poly = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotter_poly.plot(facecolor='#ccd4dd', edgecolor='#98a7b5')

    plotter_lines = geoplot.GeoPlotter(geoplot.postgis2shapely(lines.geom),
                                       (3, 16, 47, 56))
    # plotter_lines.cmapname = 'RdBu'
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#860808'),
                                                           (1, '#3a3a48')])
    plotter_lines.data = lines.capacity
    plotter_lines.plot(edgecolor='data', linewidth=2, cmap=my_cmap)
    add_grid_labels(lines, plotter_lines, 'capacity')
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


def plot_pickle(filename, column, lmin=0, lmax=1, n=5, digits=50):
    polygons = pd.read_pickle(filename)
    print(polygons)
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

    coastdat_plot = geoplot.GeoPlotter(polygons.geom, (3, 16, 47, 56))
    coastdat_plot.data = (polygons[column].round(digits) - lmin) / (
    lmax - lmin)
    coastdat_plot.plot(facecolor='data', edgecolor='data', cmap=my_cmap)
    coastdat_plot.draw_legend((lmin, lmax), integer=True, extend='max',
                              cmap=my_cmap,
                              legendlabel="Average wind speed [m/s]",
                              number_ticks=n)
    coastdat_plot.geometries = geoplot.postgis2shapely(
        pd.read_csv(os.path.join(os.path.dirname(__file__), 'data',
                                 'geometries',
                                 'polygons_de21_simple.csv')).geom)
    coastdat_plot.plot(facecolor=None, edgecolor='white')
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


if __name__ == "__main__":
    de21_grid()
    de21_region()
    plot_geocsv(os.path.join('data', 'geometries', 'polygons_de21_simple.csv'),
                idx_col='gid',
                # coord_file=os.path.join('data_basic', 'centroid_region.csv')
                )
    # plot_geocsv(os.path.join('geometries', 'federal_states.csv'),
    #             idx_col='iso',
    #             coord_file='data_basic/label_federal_state.csv')
    # plot_geocsv('/home/uwe/geo.csv', idx_col='gid')
