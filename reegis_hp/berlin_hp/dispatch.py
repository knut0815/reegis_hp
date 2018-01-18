# -*- coding: utf-8 -*-
"""
Dispatch optimisation using oemof's csv-reader.
"""

import os
import logging
import pandas as pd
import networkx as nx

from oemof.tools import logger
from oemof import graph
from oemof import solph
from oemof import outputlib
from matplotlib import pyplot as plt


class NodeDict(dict):
    __slots__ = ()

    def __setitem__(self, key, item):
        if super().get(key) is None:
            super().__setitem__(key, item)
        else:
            msg = ("Key '{0}' already exists. ".format(key) +
                   "Duplicate keys are not allowed in a node dictionary.")
            raise KeyError(msg)


def draw_graph(grph, edge_labels=True, node_color='#AFAFAF',
               edge_color='#CFCFCF', plot=True, node_size=2000,
               with_labels=True, arrows=True, layout='neato'):
    """
    Draw a graph. This function will be removed in future versions.

    Parameters
    ----------
    grph : networkxGraph
        A graph to draw.
    edge_labels : boolean
        Use nominal values of flow as edge label
    node_color : dict or string
        Hex color code oder matplotlib color for each node. If string, all
        colors are the same.

    edge_color : string
        Hex color code oder matplotlib color for edge color.

    plot : boolean
        Show matplotlib plot.

    node_size : integer
        Size of nodes.

    with_labels : boolean
        Draw node labels.

    arrows : boolean
        Draw arrows on directed edges. Works only if an optimization_model has
        been passed.
    layout : string
        networkx graph layout, one of: neato, dot, twopi, circo, fdp, sfdp.
    """
    if type(node_color) is dict:
        node_color = [node_color.get(g, '#AFAFAF') for g in grph.nodes()]

    # set drawing options
    options = {
     'prog': 'dot',
     'with_labels': with_labels,
     'node_color': node_color,
     'edge_color': edge_color,
     'node_size': node_size,
     'arrows': arrows
    }

    # draw graph
    pos = nx.drawing.nx_agraph.graphviz_layout(grph, prog=layout)

    nx.draw(grph, pos=pos, **options)

    # add edge labels for all edges
    if edge_labels is True and plt:
        labels = nx.get_edge_attributes(grph, 'weight')
        nx.draw_networkx_edge_labels(grph, pos=pos, edge_labels=labels)

    # show output
    if plot is True:
        plt.show()


def nodes_from_excel(filename):
    xls = pd.ExcelFile(filename)
    commodity_sources = xls.parse('commodity_sources', index_col=[0])
    transformers = xls.parse('transformers')
    renewables = xls.parse('re_sources', index_col=[0])
    demand = xls.parse('demand', index_col=[0])
    timeseries = xls.parse('time series')

    # Create demand objects and their buses from demand table
    xls_nodes = NodeDict()
    for i, b in demand.iterrows():
        # Bus
        bus_label = i + '_bus'
        xls_nodes[bus_label] = solph.Bus(label=bus_label)

        # Excess
        if b['allow excess']:
            excess_label = i + '_excess'
            xls_nodes[excess_label] = solph.Sink(label=excess_label, inputs={
                xls_nodes[bus_label]: solph.Flow()})

        # Shortage
        if b['allow shortage']:
            shortage_label = i + '_shortage'
            xls_nodes[shortage_label] = solph.Source(
                label=shortage_label, outputs={xls_nodes[bus_label]: solph.Flow(
                    variable_costs=b['shortage costs'])})

        # Demand
        demand_label = i + '_demand'
        xls_nodes[demand_label] = solph.Sink(
            label=demand_label, inputs={xls_nodes[bus_label]: solph.Flow(
                actual_value=timeseries[i], nominal_value=1, fixed=True)})

    # Create Source objects from table 'commodity sources'
    for i, cs in commodity_sources.iterrows():
        bus_label = i + '_bus'
        if bus_label not in xls_nodes:
            xls_nodes[bus_label] = solph.Bus(label=bus_label)
        cs_label = i + '_source'
        xls_nodes[cs_label] = solph.Source(
            label=cs_label, outputs={xls_nodes[bus_label]: solph.Flow(
                variable_costs=cs['costs'])})

    # Create Source objects with fixed time series from 'renewables' table
    for i, re in renewables.iterrows():

        xls_nodes[i] = solph.Source(
            label=i, outputs={xls_nodes[re['bus'] + '_bus']: solph.Flow(
                actual_value=timeseries[i], nominal_value=re['capacity'],
                fixed=True)})

    # Create Transformer objects from 'transformers' table
    for i, t in transformers.iterrows():
        outputs = {}
        conversion_factors = {}

        # heat output
        if isinstance(t['heat_bus'], str):
            outputs[xls_nodes[t['heat_bus'] + '_bus']] = solph.Flow(
                nominal_value=t['capacity'])
            conversion_factors[xls_nodes[t['heat_bus'] + '_bus']] = t[
                'therm_efficiency']
        if isinstance(t['electricity_bus'], str):
            outputs[xls_nodes[t['electricity_bus'] + '_bus']] = solph.Flow(
                nominal_value=t['capacity'])
            conversion_factors[xls_nodes[t['electricity_bus'] + '_bus']] = t[
                'elec_efficiency']

        xls_nodes[i] = solph.Transformer(
            label=i,
            inputs={xls_nodes[t['resource'] + '_bus']: solph.Flow()},
            outputs=outputs, conversion_factors=conversion_factors)

    # for i, s in storages.iterrows():
    #     xls_nodes[i] = solph.components.GenericStorage(
    #         label=i,
    #         inputs={xls_nodes[s['bus']]: solph.Flow(
    #             nominal_value=s['capacity pump'], max=s['max'])},
    #         outputs={xls_nodes[s['bus']]: solph.Flow(
    #             nominal_value=s['capacity turbine'], max=s['max'])},
    #         nominal_capacity=s['capacity storage'],
    #         capacity_loss=s['capacity loss'],
    #         initial_capacity=s['initial capacity'],
    #         capacity_max=s['cmax'], capacity_min=s['cmin'],
    #         inflow_conversion_factor=s['efficiency pump'],
    #         outflow_conversion_factor=s['efficiency turbine'])
    return xls_nodes


logger.define_logging()
datetime_index = pd.date_range(
    '2030-01-01 00:00:00', '2030-01-14 23:00:00', freq='60min')

# model creation and solving
logging.info('Starting optimization')

# adding all nodes and flows to the energy system
# (data taken from excel-file)
nodes = nodes_from_excel(
    os.path.join('/home/uwe/express/reegis/berlin_hp/scenarios', 'test.xlsx',))

es = solph.EnergySystem(timeindex=datetime_index)
es.add(*nodes.values())

# my_graph = graph.create_nx_graph(es, filename="/home/uwe/my_graph")
# draw_graph(my_graph, plot=True, layout='neato', node_size=300, arrows=True)


print("********************************************************")
print("The following objects has been created from excel sheet:")
for n in es.nodes:
    oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
    print(oobj + ':', n.label)
print("********************************************************")

# creation of a least cost model from the energy system
om = solph.Model(energysystem=es)
om.receive_duals()

# solving the linear problem using the given solver
om.solve(solver='cbc', solve_kwargs={'tee': True})

results = outputlib.processing.results(om)

electricity = outputlib.views.node(results, 'electricity_bus')
# region1 = outputlib.views.node(results, 'R1_bus_el')
print(electricity)

print(electricity['sequences'].sum())
# print(region1['sequences'].sum())
electricity['sequences'].plot()
plt.show()

logging.info("Done!")
