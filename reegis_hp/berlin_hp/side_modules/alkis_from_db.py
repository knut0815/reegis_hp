import logging
import datetime
import os
import pandas as pd
import oemof.db as db
from oemof.tools import logger
from reegis_hp.berlin_hp import config as cfg


def sql_string(spacetype, space_gid=None):
    """
    spacetype (string): Type of space (berlin, bezirk, block, planungsraum...)
    space_gid (tuple): chosen gids for
    """
    if space_gid is None:
        space_gid = "everything"
    logging.info("From table berlin.{1} get {0}.".format(
        space_gid, spacetype))
    if spacetype != "berlin":
        if isinstance(space_gid, int):
            space_gid = "({0})".format(space_gid)
        where_space = "space.gid in {0} AND".format(space_gid)
    else:
        where_space = ''

    return '''
        SELECT DISTINCT ag.gid, ew.ew_ha2014, block.schluessel,
            ag.anzahldero, ag.strassen_n,
            ag.hausnummer, ag.pseudonumm, st_area(st_transform(ag.geom, 3068)),
            st_perimeter(st_transform(ag.geom, 3068)), ag.gebaeudefu,
            sn.typklar, hz."PRZ_NASTRO", hz."PRZ_FERN", hz."PRZ_GAS",
            hz."PRZ_OEL", hz."PRZ_KOHLE", plr.schluessel, st_astext(ag.geom),
            ag.year_of_construction
        FROM berlin.{0} as space, berlin.alkis_gebaeude ag
        INNER JOIN berlin.stadtnutzung sn ON st_within(
            st_centroid(ag.geom), sn.geom)
        INNER JOIN berlin.einwohner ew ON st_within(
            st_centroid(ag.geom), ew.geom)
        INNER JOIN berlin.heizungsarten_geo hz ON st_within(
            st_centroid(ag.geom), hz.geom)
        INNER JOIN berlin.block block ON st_within(
            st_centroid(ag.geom), block.geom)
        INNER JOIN berlin.planungsraum  plr ON st_within(
            st_centroid(ag.geom), plr.geom)
        WHERE
            {1}
            ag.bauart_sch is NULL AND
            space.geom && ag.geom AND
            st_contains(space.geom, st_centroid(ag.geom))
        ;
    '''.format(spacetype, where_space)


def get_buildings_from_db():
    start_db = datetime.datetime.now()
    conn = db.connection()
    logging.debug("SQL query: {0}".format(sql))
    logging.info("Retrieving data from db...")
    logging.info(sql)
    results = (conn.execute(sql))
    logging.info("Success.")
    db_data = pd.DataFrame(results.fetchall(), columns=[
        'gid', 'population_density', 'spatial_na', 'floors', 'name_street',
        'number', 'alt_number', 'area', 'perimeter', 'building_function',
        'blocktype', 'frac_off-peak_electricity_heating',
        'frac_district_heating', 'frac_natural_gas_heating',
        'frac_oil_heating', 'frac_coal_stove', 'plr_key', 'geom',
        'age_from_scan'])

    db_data.number.fillna(db_data.alt_number, inplace=True)
    db_data.drop('alt_number', 1, inplace=True)

    # Convert objects from db to floats:
    db_data.floors = db_data.floors.astype(float)
    db_data.population_density = db_data.population_density.astype(float)
    db_data.building_function = db_data.building_function.astype(int)

    # Dump data into file
    path = cfg.get('paths', 'fis_broker')
    db_data.to_csv(os.path.join(path,
                                cfg.get('fis_broker', 'alkis_buildings_csv')))
    db_data.to_hdf(os.path.join(path,
                                cfg.get('fis_broker', 'alkis_buildings_hdf')),
                   'alkis')

    logging.info("DB time: {0}".format(datetime.datetime.now() - start_db))
    return db_data


logger.define_logging()
start = datetime.datetime.now()

# Select region
level, selection = ('berlin', None)
# level, selection = ('bezirk', 6)
# level, selection = ('planungsraum', 384)
# level, selection = ('block', (5812, 9335))
overwrite = False

sql = sql_string(level, selection)

data = get_buildings_from_db()