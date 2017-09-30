# http://www.geodatenzentrum.de/auftrag1/archiv/vektor/vg250_ebenen/2015/vg250-ew_2015-12-31.geo84.shape.ebenen.zip

import os
import pandas as pd
import geopandas as gpd
from oemof.tools import logger
from shapely.wkt import loads as wkt_loads
from reegis_hp.de21 import tools as t
import zipfile
import shutil
import glob
import logging
from reegis_hp.de21 import config as cfg


STATES = {
    'Baden-Württemberg': 'BW',
    'Bayern': 'BY',
    'Berlin': 'BE',
    'Brandenburg': 'BB',
    'Bremen': 'HB',
    'Hamburg': 'HH',
    'Hessen': 'HE',
    'Mecklenburg-Vorpommern': 'MV',
    'Niedersachsen': 'NI',
    'Nordrhein-Westfalen': 'NW',
    'Rheinland-Pfalz': 'RP',
    'Saarland': 'SL',
    'Sachsen': 'SN',
    'Sachsen-Anhalt': 'ST',
    'Schleswig-Holstein': 'SH',
    'Thüringen': 'TH',
    }


def get_ew_shp_file(year):
    if year < 2009:
        logging.error("Shapefile with inhabitants are available since 2009.")
        logging.error("Try to find another source to get older data sets.")
        raise AttributeError('Years < 2009 are not allowed in this function.')

    outshp = os.path.join(cfg.get('paths', 'general'),
                          'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(outshp):
        url = cfg.get('download', 'url_geodata_ew').format(year=year,
                                                           var1='{0}')
        filename_zip = os.path.join(cfg.get('paths', 'general'),
                                    cfg.get('general_sources', 'vg250_ew_zip'))
        msg = t.download_file(filename_zip, url.format('ebene'))
        if msg == 404:
            logging.warning("Wrong URL. Try again with different URL.")
            t.download_file(filename_zip, url.format('ebenen'), overwrite=True)

        zip_ref = zipfile.ZipFile(filename_zip, 'r')
        zip_ref.extractall(cfg.get('paths', 'general'))
        zip_ref.close()
        subs = next(os.walk(cfg.get('paths', 'general')))[1]
        mysub = None
        for sub in subs:
            if 'vg250' in sub:
                mysub = sub
        pattern_path = list()

        pattern_path.append(os.path.join(cfg.get('paths', 'general'),
                                         mysub,
                                         'vg250-ew_ebenen',
                                         'VG250_VWG*'))
        pattern_path.append(os.path.join(cfg.get('paths', 'general'),
                                         mysub,
                                         'vg250-ew_ebenen',
                                         'vg250_vwg*'))
        pattern_path.append(os.path.join(cfg.get('paths', 'general'),
                                         mysub,
                                         'vg250_ebenen-historisch',
                                         'de{0}12'.format(str(year)[-2:]),
                                         'vg250_vwg*'))

        for pa_path in pattern_path:
            for file in glob.glob(pa_path):
                file_new = os.path.join(cfg.get('paths', 'general'),
                                        'VG250_VWG_' + str(year) + file[-4:])
                shutil.copyfile(file, file_new)

        shutil.rmtree(os.path.join(cfg.get('paths', 'general'), mysub))

        os.remove(filename_zip)


def get_ew_by_region(spatial, year):
    filename_shp = os.path.join(cfg.get('paths', 'general'),
                                'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(filename_shp):
        get_ew_shp_file(year)

    vwg = gpd.read_file(filename_shp)

    # replace polygon geometry by its centroid
    vwg['geometry'] = vwg.representative_point()

    ewz = pd.Series()
    spatial.sort_index(inplace=True)
    n = 0
    for i, v in spatial.iterrows():
        n += 1
        ewz.loc[i] = vwg.loc[vwg.intersects(wkt_loads(v.geom)), 'EWZ'].sum()
        print(i, end=', ', flush=True)
        if n % 5 == 0:
            print()
    print()
    if vwg.EWZ.sum() - ewz.sum() > 0:
        logging.warning(
            "Overall sum {0} is higher than localised sum {1}.".format(
                ewz.sum(), vwg.EWZ.sum()))
    ewz.name = 'ew'
    ewz.index.name = 'id'
    return ewz


def ew_de21_table_to_csv(year, outfile=None):
    infile = os.path.join(cfg.get('paths', 'geometry'),
                          cfg.get('geometry', 'overlap_region_polygon'))
    if outfile is None:
        outfile = os.path.join(cfg.get('paths', 'general'),
                               cfg.get('general_sources', 'ew'))

    overlap_regions = pd.read_csv(infile, index_col=[0])

    ew = pd.DataFrame(get_ew_by_region(overlap_regions, year))

    ew['region'] = ew.index.map(lambda x: x.split('_')[1])
    ew['state'] = ew.index.map(lambda x: x.split('_')[0])
    states = cfg.get_dict('STATES')
    ew['sid'] = ew.state.apply(lambda x: states[x])

    ew.to_csv(outfile.format(year=year))


def get_ew_de21(year):
    filename = os.path.join(cfg.get('paths', 'general'),
                            cfg.get('general_sources', 'ew'))
    filename = filename.format(year=year)
    if not os.path.isfile(filename):
        ew_de21_table_to_csv(year, filename)
    return pd.read_csv(filename, index_col=[0])


if __name__ == "__main__":
    logger.define_logging()

    # print(get_ew_de21(2014).groupby('state').sum().sum())

    spatial_file_fs = os.path.join(cfg.get('paths', 'geometry'),
                                   cfg.get('geometry', 'federalstates_polygon'))
    spatial_dfs = pd.read_csv(spatial_file_fs, index_col='gen')
    print(get_ew_by_region(spatial_dfs, 2009))
