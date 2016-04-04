# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import pandas as pd
from oemof import db
from Open_eQuarterPy.stat_util import energy_demand as ed
from Open_eQuarterPy.stat_util import building_evaluation as be

#conn = db.connection()
#
#
#
#sql = '''
#select
#    st_area(st_transform(geom, 3068)),
#    st_perimeter(st_transform(geom, 3068))
#from berlin.hausumringe
#where gid=360186;
#'''
#results = (conn.execute(sql))
#columns = results.keys()
#result1_df = pd.DataFrame(results.fetchall(), columns=columns)
#print(result1_df)
#print()
#
#sql = '''
#SELECT ag.* FROM berlin.alkis_gebaeude as ag, berlin.hausumringe as haus
#WHERE ST_contains(ag.geom, st_centroid(haus.geom)) AND haus.gid=360186;
#'''
#results = (conn.execute(sql))
#columns = results.keys()
#result2_df = pd.DataFrame(results.fetchall(), columns=columns)
#print("Anzahl der Obergeschosse:", result2_df.anzahldero[0])
#print("Adresse:", result2_df.strassen_n[0], result2_df.hausnummer[0])

#pp.pprint(ed.evaluate_building(
#    population_density=pd.Series([52, 52, 52, 52]),
#    area=pd.Series([166.7, 228.136, 314.468, 236.846]),
#    floors=pd.Series([3.5, 3.5, 5.5, 3.5]),
#    year_of_construction=pd.Series([2004, 1937, 1884, 2004])
#    ))
gid = pd.Series([11, 12, 13, 14, 15], name='gid')
population_density = pd.Series([52, 52, 52, 52, 52], name='population_density')
area = pd.Series([166.7, 228.136, 314.468, 236.846, 86.9251], name='area')
floors = pd.Series([3.5, 3.5, 5.5, 3.5, 3.5], name='floors')
year_of_construction = pd.Series([2004, 1937, 1884, 2004, 2004],
                                 name='year_of_construction')
length = pd.Series([None, 30.278, None, None, None], name='length')
perimeter = pd.Series([61.166, 60.281, 74.821, 62.175, 38.65817], name='perimeter')

data = pd.concat([gid, population_density, area, floors, year_of_construction,
                  perimeter],
                 axis=1)

data.set_index('gid', drop=True, inplace=True)


result = be.evaluate_building(data)
result.to_csv("/home/uwe/haus.csv")
print(result)
#print(be.evaluate_building(15000, 10000, year_of_construction=1970))
