import pandas as pd
import os
import math

grid = pd.read_csv(os.path.join('data_basic', 'de21_grid_data.csv'))

f_security = 0.7
current_max = 2720

# renpass F.Wiese (page 49)
grid['capacity_calc'] = (grid.circuits * current_max * grid.voltage *
                         f_security * math.sqrt(3) / 1000)

de_grid = pd.DataFrame()

for plus in range(11001, 11022):
    for minus in range(11001, 11022):
        tmp_grid = grid.query("plus_region_id == {:0d} & ".format(plus) +
                              "minus_region_id == {:1d} & ".format(minus) +
                              "scenario_name == 'status_quo_2012_distance'")
        if len(tmp_grid) > 0:
            line_id = 'DE{:02.0f}_DE{:02.0f}'.format(minus - 11000,
                                                     plus - 11000)

            de_grid.loc[line_id, 'id_A'] = 'DE{:02.0f}'.format(minus - 11000)
            de_grid.loc[line_id, 'id_B'] = 'DE{:02.0f}'.format(plus - 11000)
            de_grid.loc[line_id, 'capacity_MW'] = tmp_grid.capacity_calc.sum()
            de_grid.loc[line_id, 'distance_km'] = tmp_grid.distance.iloc[0]

print(de_grid)
de_grid.to_csv(os.path.join('data', 'de_grid.csv'))
