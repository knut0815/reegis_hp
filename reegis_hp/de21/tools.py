import pandas as pd
from matplotlib import pyplot as plt
from oemof.tools import logger
from shapely.wkt import loads as wkt_loads
import os
import calendar


def read_seq_file():
    seq_file = 'scenarios/reegis_de_21_test_neu_seq.csv'
    seq_neu = 'scenarios/reegis_de_21_test_neu_neu_seq.csv'

    tmp_csv = pd.read_csv(seq_file, header=[0, 1, 2, 3, 4],
                          parse_dates=True, index_col=0)

    tmp_csv.to_csv(seq_neu)
    print(tmp_csv.index)


def postgis2shapely(postgis):
    geometries = list()
    for geo in postgis:
        geometries.append(wkt_loads(geo))
    return geometries


def sorter():
    b_path = '/home/uwe/express/reegis/data/feedin/solar/'
    lg_path = b_path + 'M_LG290G3__I_ABB_MICRO_025_US208/'
    sf_path = b_path + 'M_SF160S___I_ABB_MICRO_025_US208/'
    pattern = "{0}_feedin_coastdat_de_normalised_solar.h5"
    full = os.path.join(b_path, pattern)
    full_new_lg = os.path.join(lg_path, pattern)
    full_new_sf = os.path.join(sf_path, pattern)
    for year in range(1999, 2015):
        if os.path.isfile(full.format(year)):
            print(full.format(year))
            print(year, calendar.isleap(year))
            if calendar.isleap(year):
                n = 8784
            else:
                n = 8760
            f = pd.HDFStore(full.format(year), mode='r')
            new_lg = pd.HDFStore(full_new_lg.format(year), mode='w')
            new_sf = pd.HDFStore(full_new_sf.format(year), mode='w')
            for key in f.keys():
                ls_lg = list()
                ls_sf = list()
                for col in f[key].columns:
                    if 'LG' in col:
                        ls_lg.append(col)
                    elif 'SF' in col:
                        ls_sf.append(col)
                    else:
                        print(col)
                        print('Oh noo!')
                        exit(0)
                new_lg[key] = f[key][ls_lg][:n]
                new_sf[key] = f[key][ls_sf][:n]

            f.close()
            new_lg.close()
            new_sf.close()
    

if __name__ == "__main__":
    # plot_geocsv(os.path.join('geometries', 'federal_states.csv'),
    #             idx_col='iso',
    #             coord_file='data_basic/label_federal_state.csv')
    # plot_geocsv('/home/uwe/geo.csv', idx_col='gid')
    logger.define_logging()
    # sorter()
    # fetch_coastdat2_year_from_db()
