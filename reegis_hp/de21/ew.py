# http://www.geodatenzentrum.de/auftrag1/archiv/vektor/vg250_ebenen/2015/vg250-ew_2015-12-31.geo84.shape.ebenen.zip

import os
import pandas as pd
import geopandas as gpd
from oemof.tools import logger
from shapely.wkt import loads as wkt_loads
from reegis_hp.de21 import tools as t
import configuration as config
import zipfile
import shutil
import glob
import logging


def get_ew_shp_file(c, year):
    url = ('http://www.geodatenzentrum.de/auftrag1/archiv/vektor/' +
           'vg250_ebenen/{0}/vg250-ew_{0}-12-31.geo84.shape'.format(year) +
           '.{0}.zip')
    filename_zip = os.path.join(c.paths['general'], c.files['vg250_ew_zip'])
    msg = t.download_file(filename_zip, url.format('ebene'))
    if msg == 404:
        logging.warning("Wrong URL. Try again with different URL.")
        t.download_file(filename_zip, url.format('ebenen'), overwrite=True)
    zip_ref = zipfile.ZipFile(filename_zip, 'r')
    zip_ref.extractall(c.paths['general'])
    zip_ref.close()
    subs = next(os.walk(c.paths['general']))[1]
    mysub = None
    for sub in subs:
        if 'vg250' in sub:
            mysub = sub
    pattern_path = os.path.join(c.paths['general'],
                                mysub,
                                'vg250-ew_ebenen',
                                'VG250_VWG*')
    for file in glob.glob(pattern_path):
        file_new = os.path.join(c.paths['general'],
                                'VG250_VWG_' + str(year) + file[-4:])
        shutil.copyfile(file, file_new)

    shutil.rmtree(os.path.join(c.paths['general'], mysub))

    os.remove(filename_zip)


def get_ew_by_region(c, spatial, year):
    filename_shp = os.path.join(c.paths['general'],
                                'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(filename_shp):
        get_ew_shp_file(c, year)

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
        if n % 10 == 0:
            print()
    print()
    if vwg.EWZ.sum() - ewz.sum() > 0:
        logging.warning(
            "Overall sum {0} is higher than localised sum {1}.".format(
                ewz.sum(), vwg.EWZ.sum()))
    return ewz

if __name__ == "__main__":
    logger.define_logging()
    cfg = config.get_configuration()
    spatial_file = os.path.join(cfg.paths['geometry'],
                                cfg.files['federal_states_polygon'])
    spatial_dfs = pd.read_csv(spatial_file, index_col='gen')
    print(get_ew_by_region(cfg, spatial_dfs, 2014))
