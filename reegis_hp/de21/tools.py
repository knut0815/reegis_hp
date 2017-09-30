import pandas as pd
from matplotlib import pyplot as plt
from oemof.tools import logger
import os
import calendar
import logging
import requests
from shapely.geometry import Point
import datetime
from shapely.wkt import loads as wkt_loads
import geopandas as gpd
import warnings
from reegis_hp.de21 import config as cfg


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


def download_file(filename, url, overwrite=False):
    """
    Check if file exist and download it if necessary.

    Parameters
    ----------
    filename : str
        Full filename with path.
    url : str
        Full URL to the file to download.
    overwrite : boolean (default False)
        If set to True the file will be downloaded even though the file exits.
    """
    if not os.path.isfile(filename) or overwrite:
        logging.warning("File not found. Try to download it from server.")
        req = requests.get(url)
        with open(filename, 'wb') as fout:
            fout.write(req.content)
        logging.info("Downloaded from {0} and copied to '{1}'.".format(
            url, filename))
        r = req.status_code
    else:
        r = 1
    return r


def get_bmwi_energiedaten_file():
    filename = os.path.join(cfg.get('paths', 'general'),
                            cfg.get('general_sources', 'bmwi_energiedaten'))
    logging.debug("Return status from energiedaten file: {0}".format(
        download_file(filename, cfg.get('download', 'url_bmwi_energiedaten'))))
    return filename


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['lon'], df['lat'])


def create_geo_df(df, wkt_column=None, time=None, keep_wkt=False):
    """Convert pandas.DataFrame to geopandas.geoDataFrame"""
    if time is None:
        time = datetime.datetime.now()
    if wkt_column is not None:
        df['geom'] = df[wkt_column].apply(wkt_loads)
        if not keep_wkt:
            del df[wkt_column]
    if 'geom' not in df:
        df['geom'] = df.apply(lat_lon2point, axis=1)
    logging.info("Geom: {0}".format(str(datetime.datetime.now() - time)))

    return gpd.GeoDataFrame(df, crs='epsg:4326', geometry='geom')


def create_intersection_table():
    state_polygon_file = os.path.join(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))
    germany_polygon_file = os.path.join(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'germany_polygon'))
    coastdat_centroid_file = os.path.join(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'coastdatgrid_centroid'))
    coastdat_centroid = pd.read_csv(coastdat_centroid_file, index_col=[0])
    coastdat_centroid.rename(columns={'st_x': 'lon', 'st_y': 'lat'},
                             inplace=True)

    gdf = create_geo_df(coastdat_centroid)
    gdf = add_spatial_name(gdf, germany_polygon_file, 'country',
                           'coastdat2state', icol='gid', buffer=False)
    gdf = gdf.loc[gdf.state.notnull()]
    gdf = add_spatial_name(gdf, state_polygon_file, 'state', 'coastdat2state',
                           icol='iso', buffer=True)
    gdf = gdf.loc[gdf.state.notnull()]
    gdf.to_file('test.shp')


def add_spatial_name(gdf, path_spatial_file, name, category, icol='gid',
                     time=None, ignore_invalid=False, buffer=True):
    """Add name of containing region to new column for all points."""
    logging.info("Add spatial name for column: {0}".format(name))
    if time is None:
        time = datetime.datetime.now()

    # Read spatial file (with polygons).
    spatial_df = pd.read_csv(path_spatial_file, index_col=icol)

    # Use the length to create an output.
    length = len(spatial_df.index)

    # Write datasets without coordinates to a file for later analyses.
    gdf_invalid = gdf.loc[~gdf.is_valid].copy()

    if len(gdf_invalid) > 0 and not ignore_invalid:
        path = os.path.join(cfg.get('paths', 'messages'),
                            '{0}_{1}_invalid.csv'.format(category, name))
        gdf_invalid.to_csv(path)
        logging.warning("Power plants with invalid geometries present.")
        logging.warning("See '{0}' file for more information.".format(path))
        logging.warning("It is possible to fix the original file manually.")
        logging.warning("Repair file and rename it from '...something.csv'" +
                        " to 'something_fixed.csv' to skip this message.")
        logging.warning(
            "Or set ignore_invalid=True to ignore invalid geometries.")

    # Find points that intersect with polygon and pass name of the polygon to
    # a new column (name of the new column is defined by 'name' parameter.
    gdf_valid = gdf.loc[gdf.is_valid].copy()
    for i, v in spatial_df.geom.iteritems():
        length -= 1
        logging.info("Remains: {0}".format(str(length)))
        gdf_valid.loc[gdf_valid.intersects(wkt_loads(v)), name] = i
    logging.info("Spatial name added to {0}: {1}".format(name,
                 str(datetime.datetime.now() - time)))

    # If points do not intersect with any polygon, a buffer around the point is
    # created.
    if len(gdf_valid.loc[gdf_valid[name].isnull()]) > 0 and buffer:
        logging.info("Some points do not intersect. Buffering {0}...".format(
            name
        ))
        gdf_valid = find_intersection_with_buffer(gdf_valid, spatial_df, name)
    else:
        logging.info("All points intersect. No buffering necessary.")
    return gdf_valid


def find_intersection_with_buffer(gdf, spatial_df, column):
    """Find intersection of points outside the regions by buffering the point
    until the buffered point intersects with a region.
    """
    for row in gdf.loc[gdf[column].isnull()].iterrows():
        point = row[1].geom
        intersec = False
        reg = 0
        buffer = 0
        for n in range(500):
            if not intersec:
                for i, v in spatial_df.iterrows():
                    if not intersec:
                        my_poly = wkt_loads(v.geom)
                        if my_poly.intersects(point.buffer(n / 100)):
                            intersec = True
                            reg = i
                            buffer = n
                            gdf.loc[gdf.id == row[1].id, column] = reg
        if intersec:
            logging.debug("Region found for {0}: {1}, Buffer: {2}".format(
                row[1].id, reg, buffer))
        else:
            warnings.warn(
                "{0} does not intersect with any region. Please check".format(
                    row[1]))
    logging.warning("Some points needed buffering to fit. " +
                    "See debug file for more information.")
    return gdf


def geo_csv_from_shp(shapefile, outfile, id_col, tmp_file='tmp.csv'):
    tmp = gpd.read_file(shapefile)
    tmp.to_csv(tmp_file)
    tmp = pd.read_csv(tmp_file)
    new = pd.DataFrame()
    new['gid'] = tmp[id_col]
    # # Special column manipulations
    # new['gid'] = new['gid'].apply(lambda x: x.replace('Ã¼', 'ü'))
    # new['region'] = new['gid'].apply(lambda x: x.split('_')[1])
    # new['state'] = new['gid'].apply(lambda x: x.split('_')[0])
    new['geom'] = tmp['geometry']
    new.set_index('gid', inplace=True)
    new.to_csv(outfile)
    os.remove(tmp_file)


def read_bmwi_sheet_7(a=False):
    filename = get_bmwi_energiedaten_file()
    if a:
        sheet = '7a'
    else:
        sheet = '7'
    fs = pd.DataFrame()
    n = 4
    while 2014 not in fs.columns:
        n += 1
        fs = pd.read_excel(filename, sheet, skiprows=n)

    # Convert first column to string
    fs['Unnamed: 0'] = fs['Unnamed: 0'].apply(str)

    # Create 'A' column with sector name (shorten the name)
    fs['A'] = fs['Unnamed: 0'].apply(
        lambda x: x.replace('nach Anwendungsbereichen ', '')
        if 'Endenergie' in x else float('nan'))
    fs['A'] = fs['A'].fillna(method='ffill')
    fs = fs[fs['A'].notnull()]
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch in der ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch im ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch in den ', ''))
    fs['A'] = fs['A'].apply(lambda x: x.replace('Sektor ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('privaten Haushalten', 'private Haushalte'))

    # Create 'B' column with type
    fs['B'] = fs['Unnamed: 0'].apply(
        lambda x: x if '-' not in x else float('nan'))
    fs['B'] = fs['B'].fillna(method='ffill')

    fs['B'] = fs['B'].apply(lambda x: x if 'nan' not in x else float('nan'))
    fs = fs[fs['B'].notnull()]

    # Create 'C' column with fuel
    fs['C'] = fs['Unnamed: 0'].apply(lambda x: x if '-' in x else float('nan'))
    fs['C'] = fs['C'].fillna(fs['B'])

    # Delete first column and set 'A', 'B', 'C' columns to index
    del fs['Unnamed: 0']

    # Set new columns to index
    fs = fs.set_index(['A', 'B', 'C'], drop=True)
    return fs


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


def prices():
    # from matplotlib import pyplot as plt
    spath = '/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/static/'
    sfile = 'commodity_sources_prices.csv'
    price = pd.read_csv(os.path.join(spath, sfile), index_col=[0], header=[0, 1])
    print(price)
    price['Erdgas'].plot()
    plt.show()


def load_energiebilanzen():
    spath = '/home/uwe/chiba/Promotion/Energiebilanzen/2014/'
    sfile = 'Energiebilanz RheinlandPfalz 2014.xlsx'
    sfile = 'Energiebilanz BadenWuerttemberg2014.xls'
    filename = os.path.join(spath, sfile)
    header = pd.read_excel(filename, 0, index=[0, 1, 2, 3, 4], header=None
                           ).iloc[:3, 5:].ffill(axis=1)

    eb = pd.read_excel(filename, 0, skiprows=3, index_col=[0, 1, 2, 3, 4], skip_footer=2)
    eb.columns = pd.MultiIndex.from_arrays(header.values)
    # print(eb)
    # print(eb.loc[pd.IndexSlice[
    #     'ENDENERGIEVERBRAUCH',
    #     :,
    #     :,
    #     84]].transpose())
    eb.sort_index(0, inplace=True)
    eb.sort_index(1, inplace=True)
    #
    print(eb.loc[(slice(None), slice(None), slice(None), 84), 'Braunkohlen'])
    # print(eb.columns)


if __name__ == "__main__":
    # plot_geocsv(os.path.join('geometries', 'federal_states.csv'),
    #             idx_col='iso',
    #             coord_file='data_basic/label_federal_state.csv')
    # plot_geocsv('/home/uwe/geo.csv', idx_col='gid')
    logger.define_logging()
    # offshore()
    # load_energiebilanzen()
    create_intersection_table()
    # prices()
    exit(0)
    plz2ireg()
    # sorter()
    # fetch_coastdat2_year_from_db()
