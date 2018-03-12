'''
AssemblyGenie (c) University of Manchester 2018

All rights reserved.

@author: neilswainston
'''
# pylint: disable=not-an-iterable
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
# pylint: disable=ungrouped-imports
# pylint: disable=unsubscriptable-object
from operator import itemgetter

from scipy.spatial.distance import cityblock

from assembly import plate
import pandas as pd
from synbiochem.utils.graph_utils import get_roots


class WorklistGenerator(object):
    '''Class to generate worklists.'''

    def __init__(self, graph):
        self.__graph = graph
        self.__worklist = None
        self.__plates = {}

    def get_worklist(self, plates=None):
        '''Gets worklist and plates.'''
        if not self.__worklist:
            self.__create_worklist(plates)

        return self.__worklist, self.__plates

    def __create_worklist(self, plates):
        '''Creates worklist and plates.'''
        data = []

        if plates:
            self.__plates.update(plates)

        for root in get_roots(self.__graph):
            self.__traverse(root, 0, data)

        self.__worklist = pd.DataFrame(data)

        self.__write_plates()
        self.__add_locations()

    def __write_plates(self):
        '''Writes plates from worklist.'''
        # Write input plate:
        if 'src_well' not in self.__worklist:
            self.__worklist['src_well'] = None

        if 'dest_well' not in self.__worklist:
            self.__worklist['dest_well'] = None

        inpt = \
            self.__worklist.loc[self.__worklist['src_is_input']
                                ][['src_name', 'src_well']].values

        for val in inpt:
            plate.add_component(val[0], 'input', False, self.__plates,
                                val[1])

        # Write reagents plate:
        reags = \
            self.__worklist.loc[self.__worklist['src_is_reagent']
                                ][['src_name', 'src_well']].values

        for val in sorted(reags, key=itemgetter(0)):
            plate.add_component(val[0], 'MastermixTrough', True,
                                self.__plates, val[1])

        # Write intermediates:
        intrm = self.__worklist[~(self.__worklist['src_is_input']) &
                                ~(self.__worklist['src_is_reagent'])]

        for _, row in intrm.sort_values('level', ascending=False).iterrows():
            plate.add_component(row['src_name'], row['level'], False,
                                self.__plates, row['src_well'])

        # Write products:
        for _, row in self.__worklist.iterrows():
            if row['level'] == 0:
                plate.add_component(row['dest_name'], 'output', False,
                                    self.__plates, row['dest_well'])

    def __add_locations(self):
        '''Add locations to worklist.'''
        locations = self.__worklist.apply(lambda row: self.__get_location(
            row['src_name'], row['dest_name']), axis=1)

        loc_df = locations.apply(pd.Series)
        loc_df.index = self.__worklist.index
        loc_df.columns = ['SourcePlateBarcode', 'SourcePlateWell',
                          'DestinationPlateBarcode', 'DestinationPlateWell']

        self.__worklist = pd.concat([self.__worklist, loc_df], axis=1)
        self.__worklist.sort_values(['level', 'src_is_reagent',
                                     'DestinationPlateWell'],
                                    ascending=[False, False, True],
                                    inplace=True)
        self.__worklist.to_csv('worklist.csv', index=False)

    def __get_location(self, src_name, dest_name):
        '''Get location.'''
        srcs = plate.find(self.__plates, src_name)
        dests = plate.find(self.__plates, dest_name)

        shortest_dist = float('inf')
        optimal_pair = None

        for src_plate, src_wells in srcs.iteritems():
            for dest_plate, dest_wells in dests.iteritems():
                for src_well in src_wells:
                    for dest_well in dest_wells:
                        dist = cityblock(plate.get_indices(src_well),
                                         plate.get_indices(dest_well))

                        if dist < shortest_dist:
                            shortest_dist = dist
                            optimal_pair = [src_plate, src_well,
                                            dest_plate, dest_well]
        return optimal_pair

    def __traverse(self, dest, level, data):
        '''Traverse tree.'''
        for src in dest.predecessors():
            edge_idx = self.__graph.get_eid(src.index, dest.index)
            edge = self.__graph.es[edge_idx]

            opr = edge.attributes()

            for key, val in src.attributes().iteritems():
                opr['src_' + key] = val

            for key, val in dest.attributes().iteritems():
                opr['dest_' + key] = val

            opr['level'] = level
            opr['src_is_input'] = not src.indegree() and not src['is_reagent']

            data.append(opr)
            self.__traverse(src, level + 1, data)
