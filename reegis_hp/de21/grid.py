import pandas as pd
import os
import math
import geoplot
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import scenario_writer as sw


grid = pd.read_csv(os.path.join('data_basic', 'de21_grid_data.csv'))

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
               coord_file='geometries/coord_lines.csv'):
    p = pd.read_csv(coord_file, index_col='name')

    data['point'] = p.geom
    data['rotation'] = p.rotation

    for row in data.iterrows():
        point = geoplot.postgis2shapely([row[1].point, ])[0]
        (x, y) = plotter.basemap(point.x, point.y)
        # print(row[1])
        # exit(0)

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


# renpass F.Wiese (page 49)
grid['capacity_calc'] = (grid.circuits * current_max * grid.voltage *
                         f_security * math.sqrt(3) / 1000)

lines = pd.read_csv(os.path.join('geometries', 'lines_de21.csv'),
                    index_col='name')

for l in lines.index:
    split = l.split('-')
    a = ('110{0}'.format(split[0][2:]))
    b = ('110{0}'.format(split[1][2:]))
    # print(a, b)
    cap1, dist1 = get_grid_capacity(int(a), int(b))
    cap2, dist2 = get_grid_capacity(int(b), int(a))

    if cap1 == 0 and cap2 == 0:
        lines.loc[l, 'capacity'] = 0
        lines.loc[l, 'distance'] = 0
    elif cap1 == 0 and cap2 != 0:
        lines.loc[l, 'capacity'] = cap2
        lines.loc[l, 'distance'] = dist2
    elif cap1 != 0 and cap2 == 0:
        lines.loc[l, 'capacity'] = cap1
        lines.loc[l, 'distance'] = dist1
    else:
        print("Error in {0}".format(l))

# fig = plt.figure(figsize=(10, 14))
# plt.rc('legend', **{'fontsize': 19})
# plt.rcParams.update({'font.size': 19})
# plt.style.use('grayscale')


background = pd.read_csv('geometries/polygons_de21_simple.csv', index_col='gid')

onshore = geoplot.postgis2shapely(background[background['Unnamed: 0'] > 2].geom)
plotter_poly = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
plotter_poly.plot(facecolor='#aab9aa', edgecolor='#7b987b')

onshore = geoplot.postgis2shapely(background[background['Unnamed: 0'] < 3].geom)
plotter_poly = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
plotter_poly.plot(facecolor='#d8e4ef', edgecolor='#98a7b5')

plotter_lines = geoplot.GeoPlotter(geoplot.postgis2shapely(lines.geom),
                                   (3, 16, 47, 56))
plotter_lines.cmapname = 'RdBu'
my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, '#860808'),
                                                       (1, '#3a3a48')])
plotter_lines.data = lines.capacity
plotter_lines.plot(edgecolor='data', linewidth=2, cmap=my_cmap)
add_labels(lines, plotter_lines, 'capacity')
plt.tight_layout()
plt.box(on=None)
# plt.show()

tmp = lines.capacity
tmp.index = (tmp.index.str.replace('-', '_'))

values = tmp.copy()


def id_inverter(name):
    return '_'.join([name.split('_')[1], name.split('_')[0]])

tmp.index = tmp.index.map(id_inverter)
values = pd.concat([values, tmp])

sw.update_parameter('reegis_de_21_writer', '{0}_powerline', 'source',
                    'nominal_value', values, 'grid')
