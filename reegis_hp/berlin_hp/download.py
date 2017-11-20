# -*- coding: utf-8 -*-
"""
Created on Tue Mar 15 16:33:38 2016

@author: uwe
"""

import os
from owslib.wfs import WebFeatureService
from reegis_hp.berlin_hp import config as cfg
import subprocess as sub
import geopandas as gpd
import pandas as pd
from shapely.wkt import loads as wkt_loads
import logging
from oemof.tools import logger
from shutil import copyfile
import warnings


def feature2gml(bbox, file, table, wfs11):
    response = wfs11.getfeature(typename='fis:' + table,
                                bbox=bbox, srsname='EPSG:25833')
    out = open(file, 'wb')
    out.write(bytes(response.read(), 'UTF-8'))
    out.close()


def dump_from_wfs(table, server, version='1.1.0'):

    wfs11 = WebFeatureService(url=server + table, version=version, timeout=300)

    logging.info("Download {0} from {1}".format(table, server))
    logging.info(wfs11.identification.title)
    logging.info(list(wfs11.contents))

    x_min = 369097
    y_min = 5799298
    x_max = 416866
    y_max = 5838237

    # number of tiles to split the query in parts
    number_of_tiles_x = 12
    number_of_tiles_y = 10

    # calculate steps
    steps_x = (x_max - x_min) / number_of_tiles_x
    steps_y = (y_max - y_min) / number_of_tiles_y

    path = os.path.join(cfg.get('paths', 'fis_broker'), table)

    if not os.path.isdir(path):
        os.mkdir(path)

    for x_tile in range(number_of_tiles_x):
        for y_tile in range(number_of_tiles_y):
            my_box = (x_min + (x_tile * steps_x),
                      y_max - (y_tile * steps_y),
                      x_min + ((x_tile + 1) * steps_x),
                      y_max - ((y_tile + 1) * steps_y))
            filename = "{0}_{1}_{2}.gml".format(table, x_tile, y_tile)
            fullpath = os.path.join(path, filename)
            if not os.path.isfile(fullpath):
                logging.info("Processing tile {0}-{1}".format(x_tile, y_tile))
                feature2gml(my_box, fullpath, table, wfs11)
    logging.info("Download completed.")


def convert_gml2shp(table):
    logging.info("Convert gml-files to shp-files for {0}".format(table))
    basic_call = 'ogr2ogr -f "ESRI Shapefile" {0} {1}'
    src_path = os.path.join(cfg.get('paths', 'fis_broker'), table)
    trg_path = os.path.join(src_path, 'shp')
    if not os.path.isdir(trg_path):
        os.mkdir(trg_path)
    for f in sorted(os.listdir(src_path)):
        if '.gml' in f:
            logging.debug("Convert {0} to shp".format(f))
            src_file = os.path.join(src_path, f)
            trg_file = os.path.join(trg_path, f[:-4] + '.shp')
            ogr_call = basic_call.format(trg_file, src_file)
            sub.Popen(ogr_call, stderr=open(os.devnull, 'w'), shell=True).wait()
    logging.info("Shp-files created.")


def merge_shapefiles(path, table):
    logging.info("Merge shp-files into {0}".format(table + '.shp'))
    mergefile = os.path.join(path, 'merge.shp')
    fileset = '{0} {1}'.format(mergefile, '{0}')
    basic_call = ('ogr2ogr -f "ESRI Shapefile" -t_srs EPSG:4326 -update -append'
                  ' {0} -nln merge')
    basic_call = basic_call.format(fileset)
    n = 0
    for f in sorted(os.listdir(path)):
        if '.shp' in f and 'merge' not in f:
            f = os.path.join(path, f)
            if os.path.isfile(f[:-4] + '.prj'):
                logging.info("Merge {0}".format(f))
                cmd = basic_call.format(f)
                sub.Popen(cmd, stdout=open(os.devnull, 'w'), shell=True).wait()
            f = f[:-4]
            for s in ['.shx', '.shp', '.prj', '.dbf']:
                if os.path.isfile(f + s):
                    os.remove(f + s)
            n += 1
    # rename
    newfile = os.path.join(path, table)
    for s in ['.shx', '.shp', '.prj', '.dbf']:
        if os.path.isfile(mergefile[:-4] + s):
            copyfile(mergefile[:-4] + s, newfile + s)
            os.rename(mergefile[:-4] + s, newfile + '_orig' + s)
    logging.info("Merge completed.")


def remove_duplicates(shp_file, id_col):
    logging.info("Removing duplicates in {0}".format(shp_file))
    geo_table = gpd.read_file(shp_file)
    orig_crs = geo_table.crs
    geo_table = geo_table.drop_duplicates(id_col)
    geo_table = geo_table.to_crs(orig_crs)
    geo_table.to_file(shp_file)
    logging.info("Duplicates removed.")


def shapefile_from_wfs(table, server, id_col='gml_id', keep_orig=False):
    path = os.path.join(cfg.get('paths', 'fis_broker'), table, 'shp')
    shp_file = os.path.join(path, table + '.shp')
    if not os.path.isfile(shp_file):
        dump_from_wfs(table=table, server=server)
        convert_gml2shp(table)
        merge_shapefiles(path, table)
        remove_duplicates(shp_file, id_col)
    if not keep_orig:
        orig_file = os.path.join(path, table + '_orig')
        for s in ['.shx', '.shp', '.prj', '.dbf']:
                if os.path.isfile(orig_file + s):
                    os.remove(orig_file + s)


def shapefile_from_fisbroker(table, senstadt_server=None):
    if senstadt_server == 'data':
        server = 'http://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/'
    elif senstadt_server == 'geometry':
        server = 'http://fbinter.stadt-berlin.de/fb/wfs/geometry/senstadt/'
    else:
        server = None
    shapefile_from_wfs(table=table, server=server)


def process_alkis_buildings(table='s_wfs_alkis_gebaeudeflaechen'):
    path = os.path.join(cfg.get('paths', 'fis_broker'), table, 'shp')
    shapefile = os.path.join(path, table + '.shp')
    geo_table = gpd.read_file(shapefile)
    logging.info("Length of data set before removing parts: {0}".format(
        len(geo_table)))
    geo_table = geo_table[geo_table['Bauart_sch'] == 0]
    geo_table = geo_table[geo_table['LageZurErd'] != 1200]
    geo_table = geo_table[geo_table['Gebaeudefu'] != 2461]
    geo_table = geo_table[geo_table['Gebaeudefu'] != 2462]
    logging.info("Length of data set after removing parts: {0}".format(
        len(geo_table)))
    logging.info("Calculate perimeter and are of each polygon...")
    geo_table = geo_table.to_crs({'init': 'epsg:3035'})
    geo_table['area'] = geo_table['geometry'].area
    geo_table['perimeter'] = geo_table['geometry'].length
    geo_table = geo_table.to_crs({'init': 'epsg:4326'})
    logging.info("Dump new table to shp-file.")
    geo_table.to_file(shapefile)


def merge_test(tables):
    gdf = {}
    # Filename and path for output files
    filename_poly_layer = os.path.join(
        cfg.get('paths', 'fis_broker'),
        cfg.get('fis_broker', 'merged_blocks_polygon'))

    # Columns to use
    cols = {
        'block': ['gml_id', 'PLR', 'STAT', 'STR_FLGES'],
        'nutz': ['STSTRNAME', 'TYPKLAR', 'WOZ_NAME'],
        'ew': ['EW_HA']}

    logging.info("Read tables to be joined: {0}.".format(tuple(cols.keys())))
    for t in ['block', 'nutz', 'ew']:
        tables[t]['path'] = os.path.join(cfg.get('paths', 'fis_broker'),
                                         tables[t]['table'], 'shp',
                                         tables[t]['table'] + '.shp')
        logging.debug("Reading {0}".format(tables[t]['path']))
        gdf[t] = gpd.read_file(tables[t]['path'])[cols[t] + ['geometry']]

    logging.info("Spatial join of all tables...")

    gdf['block'].rename(columns={'gml_id': 'SCHL5'}, inplace=True)
    # Convert geometry to representative points to simplify the join
    gdf['block']['geometry'] = gdf['block'].representative_point()
    gdf['block'] = gpd.sjoin(gdf['block'], gdf['nutz'], how='inner',
                             op='within')
    del gdf['block']['index_right']
    gdf['block'] = gpd.sjoin(gdf['block'], gdf['ew'], how='left',
                             op='within')
    del gdf['block']['index_right']
    del gdf['block']['geometry']

    # Merge with polygon layer to dump polygons instead of points.
    gdf['block'] = pd.DataFrame(gdf['block'])
    polygons = gpd.read_file(tables['block']['path'])[['gml_id', 'geometry']]
    polygons.rename(columns={'gml_id': 'SCHL5'}, inplace=True)
    polygons = polygons.merge(gdf['block'], on='SCHL5')
    polygons = polygons.set_geometry('geometry')

    logging.info("Dump polygon layer to {0}...".format(filename_poly_layer))
    polygons.to_file(filename_poly_layer)

    logging.info("Read alkis table...")
    alkis_path = os.path.join(cfg.get('paths', 'fis_broker'),
                              tables['alkis']['table'], 'shp',
                              tables['alkis']['table'] + '.shp')
    alkis = gpd.read_file(alkis_path)
    print(alkis.crs)
    print(alkis.iloc[0]['geometry'])

    logging.info("Join alkis buildings with block data...")
    alkis = alkis[['AnzahlDerO', 'Strassen_n', 'Hausnummer', 'PseudoNumm',
                   'area', 'perimeter', 'Gebaeudefu', 'gml_id', 'geometry']]
    block_j = polygons[['SCHL5', 'PLR', 'STAT', 'TYPKLAR', 'EW_HA', 'geometry']]
    alkis['geometry'] = alkis.representative_point()
    alkis = gpd.sjoin(alkis, block_j, how='left', op='within')
    del alkis['index_right']

    # Hier dann noch die Heizungskarte einlesen und damit joinen
    logging.info("Join alkis buildings with heiz data...")
    # heiz = pd.read_csv('/home/uwe/heizungsarten.csv')
    # heiz = heiz.loc[heiz['geometry'].notnull()]
    # heiz['geometry'] = heiz['geometry'].apply(wkt_loads)
    # geoheiz = gpd.GeoDataFrame(heiz, crs={'init': 'epsg:4326'})[[
    #     'PRZ_FERN', 'PRZ_GAS', 'PRZ_KOHLE', 'PRZ_NASTRO', 'PRZ_OEL',
    #     'geometry']]
    geoheiz = gpd.read_file('/home/uwe/heizungsarten.shp')[[
        'PRZ_FERN', 'PRZ_GAS', 'PRZ_KOHLE', 'PRZ_NASTRO', 'PRZ_OEL',
        'geometry']]

    geoheiz = geoheiz[geoheiz.geometry.is_valid]

    # geoheiz.to_file('/home/uwe/heizungsarten_valid.shp')

    alkis = gpd.sjoin(alkis, geoheiz, how='left', op='within')
    del alkis['index_right']

    logging.info("Add block data for non-matching points using buffers.")
    remain = len(alkis.loc[alkis['PLR'].isnull()])
    logging.info("This will take some time. Number of points: {0}".format(
        remain))

    # I think it is possible to make this faster and more elegant but I do not
    # not have the time to think about it. As it has to be done only once it
    # is not really time-sensitive.
    for row in alkis.loc[alkis['PLR'].isnull()].iterrows():
        idx = int(row[0].copy())
        point = row[1].geometry
        intersec = False
        n = 0
        block_id = 0
        while not intersec and n < 500:
            bi = block_j.loc[block_j.intersects(point.buffer(n / 100000))]
            if len(bi) > 0:
                intersec = True
                bi = bi.iloc[0]
                block_id = bi['SCHL5']
                del bi['geometry']
                alkis.loc[idx, bi.index] = bi
            n += 1
        remain -= 1

        if intersec:
            logging.info(
                "Block found for {0}: {1}, Buffer: {2}. Remains: {3}".format(
                    alkis.loc[idx, 'gml_id'][-12:], block_id[-16:], n, remain))
        else:
            warnings.warn(
                "{0} does not intersect with any region. Please check".format(
                    row[1]))

    logging.info("Check: Number of buildings without PLR attribute: {0}".format(
        len(alkis.loc[alkis['PLR'].isnull()])))

    # Merge with polygon layer to dump polygons instead of points.
    logging.info("Merge new alkis layer with alkis polygon layer.")
    alkis = pd.DataFrame(alkis)
    del alkis['geometry']
    alkis_poly = gpd.read_file(alkis_path)[['gml_id', 'geometry']]
    alkis_poly = alkis_poly.merge(alkis, on='gml_id')
    alkis_poly = alkis_poly.set_geometry('geometry')
    logging.info("Dump new alkis layer with additional block data.")
    alkis_poly.to_file('/home/uwe/alkis_polygon.shp')
    alkis_poly.to_csv('/home/uwe/alkis_polygon.csv')
    alkis_poly.to_hdf('/home/uwe/alkis_polygon.hdf', 'buildings')
    exit(0)


if __name__ == "__main__":
    log_file = os.path.join(cfg.get('paths', 'berlin_hp'), 'download.log')
    logger.define_logging()

    # alkis = {'table': 'alkis_test',
    #          'senstadt_server': 'data'}
    maps = {
        'alkis': {'table': 's_wfs_alkis_gebaeudeflaechen',
                  'senstadt_server': 'data'},
        'nutz': {'table': 're_nutz2015_nutzsa',
                 'senstadt_server': 'geometry'},
        'ew': {'table': 's06_06ewdichte2016',
               'senstadt_server': 'data'},
        'block': {'table': 's_ISU5_2015_UA',
                  'senstadt_server': 'data'}}

    for key in maps.keys():
        logging.info("Dump table {0} from {1}".format(
            maps[key]['table'], maps[key]['senstadt_server']))
        shapefile_from_fisbroker(**maps[key])

    # process_alkis_buildings()
    merge_test(maps)
