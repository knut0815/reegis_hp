import pandas as pd
import os
import math

grid = pd.read_csv(os.path.join('data_basic', 'de21_grid_data.csv'))

f_security = 0.7
current_max = 2720


def get_grid_capacity(plus, minus):
    tmp_grid = grid.query("plus_region_id == {:0d} & ".format(plus) +
                          "minus_region_id == {:1d} & ".format(minus) +
                          "scenario_name == 'status_quo_2012_distance'")

    line_id = 'DE{:02.0f}_DE{:02.0f}'.format(minus - 11000, plus - 11000)
    de_grid.loc[line_id, 'id_A'] = 'DE{:02.0f}'.format(minus - 11000)
    de_grid.loc[line_id, 'id_B'] = 'DE{:02.0f}'.format(plus - 11000)
    if len(tmp_grid) > 0:
        de_grid.loc[line_id, 'capacity_MW'] = tmp_grid.capacity_calc.sum()
        de_grid.loc[line_id, 'distance_km'] = tmp_grid.distance.iloc[0]
    else:
        de_grid.loc[line_id, 'capacity_MW'] = 0
        de_grid.loc[line_id, 'distance_km'] = 0


# renpass F.Wiese (page 49)
grid['capacity_calc'] = (grid.circuits * current_max * grid.voltage *
                         f_security * math.sqrt(3) / 1000)

de_grid = pd.DataFrame()

lines = pd.read_csv(os.path.join('geometries', 'lines_de21.csv'),
                    index_col='name')

for l in lines.index:
    split = l.split('-')
    A = ('110{0}'.format(split[0][2:]))
    B = ('110{0}'.format(split[1][2:]))
    print(A, B)
    get_grid_capacity(int(A), int(B))
    get_grid_capacity(int(B), int(A))

# Behalte nur eine Richtung. Wenn eins null dann Wert behalten, sonst egal.

print(de_grid)
de_grid.to_csv(os.path.join('data', 'de_grid.csv'))
