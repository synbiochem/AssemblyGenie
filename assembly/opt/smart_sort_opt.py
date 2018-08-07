'''
AssemblyGenie (c) University of Manchester 2018

All rights reserved.

@author: neilswainston
'''
# pylint: disable=invalid-name
from itertools import cycle

import pandas as pd


def optimise(df):
    '''Optimise.'''
    data = []

    plate_size = list(df['src_plate_size'])[0]

    sort_df = df.sort_values(['dest_idx'])

    group_dfs = {src_idx: group_df
                 for src_idx, group_df in sort_df.groupby('src_idx')}

    for idx in cycle(range(plate_size)):
        group_df = group_dfs.get(idx, None)

        if group_df is not None and not group_df.empty:
            row = list(group_df.iloc[[0]].values[0])
            group_df.drop(group_df.index[0], inplace=True)
            data.append(row)

        if len(data) == len(df):
            break

    return pd.DataFrame(data, columns=df.columns)
