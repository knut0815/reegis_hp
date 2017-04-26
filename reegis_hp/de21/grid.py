import pandas as pd
import os
import math
try:
    import geoplot
except ImportError:
    geoplot = None
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


grid = pd.read_csv(os.path.join('data', 'basic', 'de21_grid_data.csv'))

f_security = 0.7
current_max = 2720


def get_grid_capacity(plus, minus):
    tmp_grid = grid.query("plus_region_id == {:0d} & ".format(plus) +
                          "minus_region_id == {:1d} & ".format(minus) +
                          "scenario_name == 'status_quo_2012_distance'")

    if len(tmp_grid) > 0:
        capacity = tmp_grid.capacity_calc.sum()
        distance = tmp_grid.distance.iloc[0]
    else:
        capacity = 0
        distance = 0
    return capacity, distance


def add_labels(data, plotter, label=None,
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


def get_transmission_lines():
    # renpass F.Wiese (page 49)
    grid['capacity_calc'] = (grid.circuits * current_max * grid.voltage *
                             f_security * math.sqrt(3) / 1000)

    pwr_lines = pd.read_csv(os.path.join('data', 'geometries',
                                         'lines_de21.csv'),
                            index_col='name')

    for l in pwr_lines.index:
        split = l.split('-')
        a = ('110{0}'.format(split[0][2:]))
        b = ('110{0}'.format(split[1][2:]))
        # print(a, b)
        cap1, dist1 = get_grid_capacity(int(a), int(b))
        cap2, dist2 = get_grid_capacity(int(b), int(a))

        if cap1 == 0 and cap2 == 0:
            pwr_lines.loc[l, 'capacity'] = 0
            pwr_lines.loc[l, 'distance'] = 0
        elif cap1 == 0 and cap2 != 0:
            pwr_lines.loc[l, 'capacity'] = cap2
            pwr_lines.loc[l, 'distance'] = dist2
        elif cap1 != 0 and cap2 == 0:
            pwr_lines.loc[l, 'capacity'] = cap1
            pwr_lines.loc[l, 'distance'] = dist1
        else:
            print("Error in {0}".format(l))

    # plot_grid(pwr_lines)
    tmp = pwr_lines[['capacity', 'distance']]
    values = tmp.copy()

    def id_inverter(name):
        return '-'.join([name.split('-')[1], name.split('-')[0]])

    tmp.index = tmp.index.map(id_inverter)
    df = pd.concat([values, tmp])
    if not os.path.isdir(os.path.join('data', 'grid')):
        os.makedirs(os.path.isdir(os.path.join('data', 'grid')))
    df.to_csv(os.path.join('data', 'grid', 'de21_transmission.csv'))
    return df


def get_grid():
    return pd.read_csv(os.path.join('data', 'grid', 'de21_transmission.csv'),
                       index_col='Unnamed: 0')


if __name__ == "__main__":
    # lines = get_transmission_lines()
    plot_grid()
