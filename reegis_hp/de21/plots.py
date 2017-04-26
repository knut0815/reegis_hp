import pandas as pd
import tools
import os
import geoplot
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


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

        plotter.ax.text(x, y, text, color=textcolour, fontsize=11,
                        rotation=row[1].rotation)


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
    # fig = plt.figure(figsize=(10, 14))
    # plt.rc('legend', **{'fontsize': 19})
    # plt.rcParams.update({'font.size': 19})
    # plt.style.use('grayscale')

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
    plotter_poly.plot(facecolor='#aab9aa', edgecolor='#7b987b')

    onshore = geoplot.postgis2shapely(
        background[background['Unnamed: 0'] < 3].geom)
    plotter_poly = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotter_poly.plot(facecolor='#d8e4ef', edgecolor='#98a7b5')

    plotter_lines = geoplot.GeoPlotter(geoplot.postgis2shapely(lines.geom),
                                       (3, 16, 47, 56))
    plotter_lines.cmapname = 'RdBu'
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#860808'),
                                                           (1, '#3a3a48')])
    plotter_lines.data = lines.capacity
    plotter_lines.plot(edgecolor='data', linewidth=2, cmap=my_cmap)
    add_grid_labels(lines, plotter_lines, 'capacity')
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


if __name__ == "__main__":
    de21_grid()
