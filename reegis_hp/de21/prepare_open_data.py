"""
Getting the renewable power plants of Germany.

To use this script you have to download the
renewable_power_plants_DE.info.csv file and copy it to the data folder.

Get information about the used csv-file.
csv = pd.read_csv(
    os.path.join('data_original', 'renewable_power_plants_DE.info.csv'),
    squeeze=True, index_col=[0])
print(csv.download)
print(csv.info)
print(csv.editor)
print(csv.date)

Or just start the script and follow the instructions.

"""
import pandas as pd
import os
from shapely.geometry import Point
import datetime
from shapely.wkt import loads as wkt_loads
import geopandas as gpd
import requests
import logging
import warnings
import pyproj
from oemof.tools import logger


logger.define_logging()
FIXED = False


def read_original_file(p_type):
    """Read file if exists."""
    global FIXED

    orig_csv_file = os.path.join(
        'data_original', '{0}_power_plants_DE.csv').format(p_type)
    fixed_csv_file = os.path.join(
        'data_original', '{0}_power_plants_DE_fixed.csv').format(p_type)
    info_file = os.path.join(
        'data_basic', '{0}_power_plants_DE.info.csv').format(p_type)

    if not os.path.isdir('data_original'):
        os.makedirs('data_original')

    if os.path.isfile(fixed_csv_file):
        orig_csv_file = fixed_csv_file
        FIXED = True

    if not os.path.isfile(orig_csv_file):
        csv = pd.read_csv(info_file, squeeze=True, index_col=[0])
        req = requests.get(csv.download)
        logging.warning("File not found. Try to download it from server.")
        logging.warning("Check URL if download does not work.")
        with open(orig_csv_file, 'wb') as fout:
            fout.write(req.content)
        logging.warning("Downloaded from {0} and copied to '{1}'.".format(
            csv.download, orig_csv_file))
        logging.warning("This script is tested with the file of {0}.".format(
            csv.date))

    return pd.read_csv(orig_csv_file)


def complete_geometries(df, time=None, fs_column='federal_state'):
    """Use centroid of federal state if geometries does not exist."""

    if time is None:
        time = datetime.datetime.now()

    # Store table of undefined sets to csv-file
    df.loc[df.lon.isnull()].to_csv(os.path.join('data_warnings',
                                                'complete_geometries.csv'))
    logging.debug("Gaps stored to: {0}".format(os.path.join(
        'data_warnings', 'complete_geometries.csv')))

    # Calculate weight of changes
    logging.debug("IDs without coordinates found. Trying to fill the gaps.")

    total_capacity = df.electrical_capacity.sum()
    undefined_cap = df.loc[df.lon.isnull()].electrical_capacity.sum()
    logging.debug("{0} percent of capacity is undefined.".format(
        undefined_cap / total_capacity * 100))

    # *** Convert utm if present ***
    df_utm = df.loc[(df.lon.isnull()) & (df.utm_zone.notnull())]

    utm_zones = df_utm.utm_zone.unique()
    for zone in utm_zones:
        my_utm = pyproj.Proj(
            "+proj=utm +zone={0},+north,+ellps=WGS84,".format(str(int(zone))) +
            "+datum=WGS84,+units=m,+no_defs")
        utm_df = df_utm.loc[df_utm.utm_zone == int(zone),
                            ('utm_east', 'utm_north')]
        coord = my_utm(utm_df.utm_east.values, utm_df.utm_north.values,
                       inverse=True)
        df.loc[(df.lon.isnull()) & (df.utm_zone == int(zone)), 'lat'] = coord[1]
        df.loc[(df.lon.isnull()) & (df.utm_zone == int(zone)), 'lon'] = coord[0]

    logging.debug("Reduced undefined plants by utm conversion.")
    undefined_cap = df.loc[df.lon.isnull()].electrical_capacity.sum()
    logging.debug("{0} percent of capacity is undefined.".format(
        undefined_cap / total_capacity * 100))

    # *** Use postcode
    # As 98% of the undefined plant are offshore plants it may not help

    # *** Use municipal_code and federal_state to define coordinates ***
    if 'municipality_code' in df:
        df.loc[df.municipality_code == 'AWZ', 'federal_state'] = 'AWZ_NS'
    if 'municipality_code' in df:
        df.loc[(df.postcode == '000XX'), 'federal_state'] = 'AWZ'
    states = df.loc[df.lon.isnull()].groupby(
        'federal_state').sum().electrical_capacity
    logging.debug("Fraction of undefined capacity by federal state (percent):")
    for (state, capacity) in states.iteritems():
        logging.debug("{0}: {1:.4f}".format(
            state, capacity / total_capacity * 100))
    f2c = pd.read_csv(os.path.join('data_basic', 'centroid_federal_state'),
                      index_col='name')
    f2c = f2c.applymap(wkt_loads).centroid
    for l in df.loc[df.lon.isnull()].index:
        df.loc[l, 'lon'] = f2c[df.loc[l, fs_column]].x
        df.loc[l, 'lat'] = f2c[df.loc[l, fs_column]].y

    logging.debug("Reduced undefined plants by federal_state centroid.")
    undefined_cap = df.loc[df.lon.isnull()].electrical_capacity.sum()
    logging.debug("{0} percent of capacity is undefined.".format(
        undefined_cap / total_capacity * 100))

    geo_check = not df.lon.isnull().any()
    if not geo_check:
        logging.warning("Plants with unknown geometry.")
    logging.info('Geometry check: {0}'.format(str(geo_check)))
    logging.info("Geometry supplemented: {0}".format(
        str(datetime.datetime.now() - time)))
    return df


def remove_cols(df, cols):
    """Safely remove columns from dict."""
    for key in cols:
        try:
            del df[key]
        except KeyError:
            pass
    return df


def clean_df(df, rmv_ls=None, str_columns=None, float_columns=None, time=None):
    """Remove obsolete columns and set consistent type to columns."""
    if time is None:
        time = datetime.datetime.now()

    if rmv_ls is not None:
        df = remove_cols(df, rmv_ls)

    if str_columns is not None:
        df.loc[:, str_columns] = df[str_columns].applymap(str)

    if float_columns is not None:
        df.loc[:, float_columns] = df[float_columns].applymap(float)
    logging.info("Cleaned: {0}".format(str(datetime.datetime.now() - time)))
    return df


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['lon'], df['lat'])


def create_geo_df(df, time=None):
    """Convert pandas.DataFrame to geopandas.geoDataFrame"""
    if time is None:
        time = datetime.datetime.now()
    df['geom'] = df.apply(lat_lon2point, axis=1)
    logging.info("Geom: {0}".format(str(datetime.datetime.now() - time)))

    return gpd.GeoDataFrame(df, crs='epsg:4326', geometry='geom')


def add_spatial_name(gdf, path_spatial_file, name, icol='gid', time=None):
    """Add name of containing region to new column for all points."""
    logging.info("Add spatial name for column: {0}".format(name))
    if time is None:
        time = datetime.datetime.now()
    spatial_df = pd.read_csv(path_spatial_file, index_col=icol)
    length = len(spatial_df.index)
    gdf_invalid = gdf.loc[~gdf.is_valid].copy()
    if len(gdf_invalid) > 0 and not FIXED:
        gdf_invalid.to_csv('invalid.csv')
        logging.warning("Power plants with invalid geometries present.")
        logging.warning("See 'invalid.csv' file for more information")
        logging.warning("You have to fix the original file manually.")
        logging.warning("Rename original file from '...something.csv' to " +
                        "'something_fixed.csv' to skip this error and continue")
        exit(0)
    if len(gdf_invalid) > 0:
        logging.warning("Power plants with invalid geometries will be ignored")
    gdf_valid = gdf.loc[gdf.is_valid].copy()
    for i, v in spatial_df.geom.iteritems():
        length -= 1
        logging.info("Remains: {0}".format(str(length)))
        gdf_valid.loc[gdf_valid.intersects(wkt_loads(v)), name] = i
    logging.info("Spatial name added to {0}: {1}".format(name,
                 str(datetime.datetime.now() - time)))

    if len(gdf_valid.loc[gdf_valid[name].isnull()]) > 0:
        logging.info("Some plants do not intersect. Buffering {0}...".format(
            name
        ))
        gdf_valid = find_intersection_with_buffer(gdf_valid, spatial_df, name)
    else:
        logging.info("All plants intersect. No buffering necessary.")
    return gdf_valid


def fill_region_with_coastdat(df, time=None):
    """If region name is None use location of coastdat point."""
    if time is None:
        time = datetime.datetime.now()
    t = pd.read_csv('data_basic/coastdat2region.csv', index_col='id',
                    squeeze=True)
    for i, v in df.region.iteritems():
        if v == 'None':
            df.loc[i, 'region'] = t[df.loc[i, 'coastdat_id']]
    logging.info("Filled region with coastdat: {0}".format(
        str(datetime.datetime.now() - time)))
    return df


def find_intersection_with_buffer(gdf, spatial_df, column):
    """Find intersection of points outside the regions by buffering the point
    until the buffered point intersects with a region.
    """

    gdf.loc[gdf[column].isnull()].to_csv('buffer.csv')
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
                    row[1].id))
    logging.warning("Some points needed buffering to fit. " +
                    "See debug file for more information.")
    return gdf


def prepare_conventional_power_plants():
    str_cols = ['id', 'country_code', 'company', 'name_bnetza', 'block_bnetza',
                'name_uba', 'postcode', 'city', 'street', 'state',
                'commissioned_original', 'status', 'fuel',
                'energy_source_level_1', 'energy_source_level_2',
                'energy_source_level_3', 'technology', 'type', 'eeg', 'chp',
                'merge_comment', 'efficiency_source', 'network_node', 'voltage',
                'network_operator', 'geom', 'region']

    start = datetime.datetime.now()

    # Read original file or download it from original source
    cpp = read_original_file('conventional')
    logging.info("File read: {0}".format(str(datetime.datetime.now() - start)))

    # Create GeoDataFrame from original DataFrame
    gcpp = create_geo_df(cpp, start)

    # Add region column (DE01 - DE21)
    geo_file = os.path.join('geometries', 'polygons_de21_vg.csv')
    gcpp = add_spatial_name(gcpp, geo_file, 'region', time=start)

    # Add column with name of the federal state (Bayern, Berlin,...)
    geo_file = os.path.join('geometries', 'federal_states.csv')
    gcpp = add_spatial_name(gcpp, geo_file, 'federal_state', time=start,
                            icol='iso')

    # Write new table to shape-file
    gcpp['region'] = gcpp['region'].apply(str)
    gcpp.to_file(os.path.join('data', 'conv_powerplants.shp'))

    # Write new table to csv file
    cpp['region'] = gcpp['region']
    cpp['federal_state'] = gcpp['federal_state']
    cpp.to_csv(os.path.join('data', 'conv_power_plants_DE.edited.csv'))

    # Write new table to hdf file
    cpp = clean_df(cpp, str_columns=str_cols)
    cpp.to_hdf(os.path.join('data', 'conv_power_plants_DE.edited.hdf'),
               'data', mode='w')


def prepare_re_power_plants():
    remove_list = ['tso', 'dso', 'dso_id', 'eeg_id', 'bnetza_id',
                   'federal_state', 'postcode', 'municipality_code',
                   'municipality', 'address', 'address_number', 'utm_zone',
                   'utm_east', 'utm_north', 'data_source', 'comment']

    str_cols = ['commissioning_date', 'decommissioning_date',
                'energy_source_level_1', 'energy_source_level_2',
                'energy_source_level_3', 'technology', 'voltage_level']

    float_cols = ['electrical_capacity', 'thermal_capacity']

    start = datetime.datetime.now()

    # Read original file or download it from original source
    ee = read_original_file('renewable')
    logging.info("File read: {0}".format(str(datetime.datetime.now() - start)))

    # Trying to supplement missing coordinates
    ee = complete_geometries(ee, start)

    # Remove unnecessary column and fix column types.
    ee = clean_df(ee, rmv_ls=remove_list, str_columns=str_cols,
                  float_columns=float_cols)

    # Create GeoDataFrame from original DataFrame
    gee = create_geo_df(ee, start)

    # Add region column (DE01 - DE21)
    gee = add_spatial_name(gee, os.path.join(
        'geometries', 'polygons_de21_vg.csv'), 'region', time=start)

    # Add column with coastdat id
    gee = add_spatial_name(gee, os.path.join('geometries', 'coastdat_grid.csv'),
                           'coastdat_id', time=start)

    # Fix type of columns
    gee['region'] = gee['region'].apply(str)
    gee['coastdat_id'] = gee['coastdat_id'].apply(int)

    # Write new table to shape-file
    gee.to_file(os.path.join('data', 'ee_powerplants.shp'))

    # Write new table to csv file
    ee = remove_cols(ee, ['geom', 'lat', 'lon'])
    ee['region'] = gee['region']
    ee['coastdat_id'] = gee['coastdat_id']
    ee.to_csv(os.path.join('data', 'renewable_power_plants_DE.edited.csv'))

    # Write new table to hdf file
    ee.to_hdf(os.path.join('data', 'renewable_power_plants_DE.edited.hdf'),
              'data', mode='w')


if __name__ == "__main__":
    prepare_conventional_power_plants()
    prepare_re_power_plants()
