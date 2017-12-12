# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 18:28:05 2016

@author: uwe
"""

import shapefile
from owslib.wms import WebMapService

sf = shapefile.Reader("/home/uwe/berlin_bbox.shp")
shapes = sf.shapes()
bbox = tuple(shapes[0].bbox)  # Retrieves the bounding box of the first shape

print(bbox)

wms = WebMapService(
    # 'http://fbinter.stadt-berlin.de/fb/wms/senstadt/gebaeudealter',
    'http://fbinter.stadt-berlin.de/fb/wms/senstadt/step_fernw',
    version='1.1.1')
print(wms.identification.type)
print(wms.identification.title)
print('Content:', list(wms.contents))
print(wms['0'].title)
print(wms['0'].queryable)
print(wms['0'].opaque)
print(wms['0'].boundingBox)
print(wms['0'].boundingBoxWGS84)
print(wms['0'].crsOptions)
print(wms['0'].styles)
print([op.name for op in wms.operations])
print(wms.getOperationByName('GetMap').methods)
print(wms.getOperationByName('GetMap').formatOptions)
#print(wms.getfeatureinfo(layers=['0'],
#                 styles=['default'],
#                 srs='EPSG:3068',
#                 format='image/png',
#                 info_format='text/html',
#                 bbox=(19800, 20000, 21000, 21000),
#                 size=(6000, 5000),
#                 xy=(20168, 20168)))
# https://geopython.github.io/OWSLib/#wms
img = wms.getmap(layers=['0'],
                 styles=['gdi_default'],
                 srs='EPSG:4326',
                 bbox=bbox,
                 # size=(1578, 1778),
                 format='image/png',
                 transparent=True
                 )

out = open('alter.png', 'wb')
out.write(img.read())
out.close()