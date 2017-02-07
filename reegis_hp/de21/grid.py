import pandas as pd
import os
import math
import geoplot
from matplotlib import pyplot as plt


grid = pd.read_csv(os.path.join('data_basic', 'de21_grid_data.csv'))

f_security = 0.7
current_max = 2720


def get_grid_capacity(plus, minus):
    line_exists = False
    tmp_grid = grid.query("plus_region_id == {:0d} & ".format(plus) +
                          "minus_region_id == {:1d} & ".format(minus) +
                          "scenario_name == 'status_quo_2012_distance'")

    line_id = 'DE{:02.0f}-DE{:02.0f}'.format(minus - 11000, plus - 11000)
    de_grid.loc[line_id, 'id_A'] = 'DE{:02.0f}'.format(minus - 11000)
    de_grid.loc[line_id, 'id_B'] = 'DE{:02.0f}'.format(plus - 11000)
    if len(tmp_grid) > 0:
        line_exists = True
        de_grid.loc[line_id, 'capacity_MW'] = tmp_grid.capacity_calc.sum()
        de_grid.loc[line_id, 'distance_km'] = tmp_grid.distance.iloc[0]
    else:
        de_grid.loc[line_id, 'capacity_MW'] = 0
        de_grid.loc[line_id, 'distance_km'] = 0
    return line_exists


# renpass F.Wiese (page 49)
grid['capacity_calc'] = (grid.circuits * current_max * grid.voltage *
                         f_security * math.sqrt(3) / 1000)

de_grid = pd.DataFrame()

lines = pd.read_csv(os.path.join('geometries', 'lines_de21.csv'),
                    index_col='name')

for l in lines.index:
    split = l.split('-')
    a = ('110{0}'.format(split[0][2:]))
    b = ('110{0}'.format(split[1][2:]))
    # print(a, b)
    a_b_exists = get_grid_capacity(int(a), int(b))
    b_a_exists = get_grid_capacity(int(b), int(a))

    line_id_a = 'DE{0}-DE{1}'.format(split[0][2:], split[1][2:])
    line_id_b = 'DE{0}-DE{1}'.format(split[1][2:], split[0][2:])

    if not a_b_exists and not b_a_exists:
        de_grid = de_grid[de_grid.index != line_id_a]
    elif a_b_exists and not b_a_exists:
        de_grid = de_grid[de_grid.index != line_id_a]
    elif not a_b_exists and b_a_exists:
        de_grid = de_grid[de_grid.index != line_id_b]
    else:
        print("Error in {0}".format(l))

# print(de_grid)

background = pd.read_csv('geometries/polygons_de21_simple.csv', index_col='gid')
poly = geoplot.postgis2shapely(background.geom)
plotter = geoplot.GeoPlotter(poly, (3, 16, 47, 56))
plt.show()

de_grid.to_csv(os.path.join('data', 'de_grid.csv'))
for l in lines.index:
    print(l)



