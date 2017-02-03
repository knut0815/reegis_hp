# http://www.geodatenzentrum.de/auftrag1/archiv/vektor/vg250_ebenen/2015/vg250-ew_2015-12-31.geo84.shape.ebenen.zip

import os
import pandas as pd
import geopandas as gpd
from oemof.tools import logger
from shapely.wkt import loads as wkt_loads

logger.define_logging()
url = ('http://www.geodatenzentrum.de/auftrag1/archiv/vektor/vg250_ebenen/' +
       '2015/vg250-ew_2015-12-31.geo84.shape.ebenen.zip')

if os.path.isfile('shp-files/VG250_VWG.shp'):
    vwg = (gpd.read_file('shp-files/VG250_VWG.shp'))
else:
    vwg = None
    print('File does not exits.')
    print('Download maps from {0}'.format(url))
    print('Unzip and copy VG250_VWG map to folder "shp-file".')
    exit(0)

# replace polygon geometry by its centroid
vwg['geometry'] = vwg.centroid

path_spatial_file = os.path.join('geometries', 'polygons_de21_vg.csv')
# path_spatial_file = os.path.join('geometries', 'federal_states.csv')

spatial_df = pd.read_csv(path_spatial_file, index_col='gid')

ewz = pd.Series(index=spatial_df.index)

print("Gesamt:", vwg.EWZ.sum() / 1000000)
for i, v in spatial_df.iterrows():
    ewz[i] = vwg.loc[vwg.intersects(wkt_loads(v.geom)), 'EWZ'].sum()
    print(i, end=', ', flush=True)
print()
print(ewz)
print('Check difference:', vwg.EWZ.sum() - ewz.sum())
