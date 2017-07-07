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


def plz2ireg():
    geopath = '/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/geometries/'
    geofile = 'postcode_polygons.csv'
    plzgeo = pd.read_csv(os.path.join(geopath, geofile), index_col='zip_code',
                         squeeze=True)
    iregpath = '/home/uwe/'
    iregfile = 'plzIreg.csv'
    plzireg = pd.read_csv(os.path.join(iregpath, iregfile), index_col='plz',
                          squeeze=True)
    plzireg = plzireg.groupby(plzireg.index).first()
    ireggeo = pd.DataFrame(pd.concat([plzgeo, plzireg], axis=1))
    ireggeo.to_csv(os.path.join(iregpath, 'ireg_geo.csv'))
    import geopandas as gpd
    import geoplot
    ireggeo = ireggeo[ireggeo['geom'].notnull()]
    ireggeo['geom'] = geoplot.postgis2shapely(ireggeo.geom)
    geoireg = gpd.GeoDataFrame(ireggeo, crs='epsg:4326', geometry='geom')
    geoireg.to_file(os.path.join(iregpath, 'ireg_geo.shp'))
    # import plots
    # plots.plot_geocsv('/home/uwe/ireg_geo.csv', [0], labels=False)
    exit(0)


def testerich():
    spath = '/home/uwe/chiba/Promotion/Kraftwerke und Speicher/'
    sfile = 'Pumpspeicher_in_Deutschland.csv'
    storage = pd.read_csv(os.path.join(spath, sfile), header=[0, 1])
    storage.sort_index(1, inplace=True)
    print(storage)
    print(storage['ZFES', 'energy'].sum())
    print(storage['Wikipedia', 'energy'].sum())


def decode_wiki_geo_string(gstr):
    replist = [('°', ';'), ('′', ';'), ('″', ';'), ('N.', ''), ('O', ''),
               ('\xa0', ''), (' ', '')]
    if isinstance(gstr, str):
        for rep in replist:
            gstr = gstr.replace(rep[0], rep[1])
        gstr = gstr.split(';')
        lat = float(gstr[0]) + float(gstr[1]) / 60 + float(gstr[2]) / 3600
        lon = float(gstr[3]) + float(gstr[4]) / 60 + float(gstr[5]) / 3600
    else:
        lat = None
        lon = None
    return lat, lon


def offshore():
    spath = '/home/uwe/chiba/Promotion/Kraftwerke und Speicher/'
    sfile = 'offshore_windparks_prepared.csv'
    offsh = pd.read_csv(os.path.join(spath, sfile), header=[0, 1],
                        index_col=[0])
    print(offsh)
    # offsh['Wikipedia', 'geom'] = offsh['Wikipedia', 'geom_str'].apply(
    #     decode_wiki_geo_string)
    # offsh[[('Wikipedia', 'latitude'), ('Wikipedia', 'longitude')]] = offsh[
    #     'Wikipedia', 'geom'].apply(pd.Series)
    # offsh.to_csv(os.path.join(spath, 'offshore_windparks_prepared.csv'))


def bmwe():
    spath = '/home/uwe/chiba/Promotion/Kraftwerke und Speicher/'
    sfile1 = 'installation_bmwe.csv'
    sfile2 = 'strom_bmwe.csv'
    sfile3 = 'hydro.csv'
    inst = pd.read_csv(os.path.join(spath, sfile1), index_col=[0]).astype(float)
    strom = pd.read_csv(os.path.join(spath, sfile2), index_col=[0]).astype(float)
    # hydro = pd.read_csv(os.path.join(spath, sfile3), index_col=[0], squeeze=True).astype(float)
    cols = pd.MultiIndex(levels=[[], []], labels=[[], []],
                         names=['type', 'value'])
    df = pd.DataFrame(index=inst.index, columns=cols)
    for col in inst.columns:
        df[col, 'capacity'] = inst[col]
        df[col, 'energy'] = strom[col]
    df.to_csv('/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/static/energy_capacity_bmwi_readme.csv')


if __name__ == "__main__":
    # plot_geocsv(os.path.join('geometries', 'federal_states.csv'),
    #             idx_col='iso',
    #             coord_file='data_basic/label_federal_state.csv')
    # plot_geocsv('/home/uwe/geo.csv', idx_col='gid')
    logger.define_logging()
    # offshore()
    bmwe()
    exit(0)
    plz2ireg()
    # sorter()
    # fetch_coastdat2_year_from_db()
