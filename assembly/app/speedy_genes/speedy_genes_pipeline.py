'''
AssemblyGenie (c) University of Manchester 2018

All rights reserved.

@author: neilswainston
'''
from collections import defaultdict
import itertools
import os
import sys
from time import gmtime, strftime

from synbiochem import utils

from assembly import pipeline, worklist
from assembly.app.speedy_genes.block import InnerBlockPoolWriter, \
    BlockPcrWriter
from assembly.app.speedy_genes.dilution import OligoDilutionWriter
from assembly.app.speedy_genes.gene import GenePcrWriter
from assembly.app.speedy_genes.pool import WtOligoPoolWriter


def run(plate_dir, n_mutated, n_blocks, out_dir_parent, exp_name):
    '''run method.'''
    dte = strftime("%y%m%d", gmtime())

    input_plates = pipeline.get_input_plates(plate_dir)
    oligos, mutant_oligos = _read_plates(input_plates)
    designs = _combine(oligos, mutant_oligos, n_mutated, n_blocks)

    writers = [
        OligoDilutionWriter(oligos, 10, 190, 'wt_5'),
        WtOligoPoolWriter(mutant_oligos, 10, 'nnk_5_pooled'),
        InnerBlockPoolWriter(designs, 5, 'pooled_templates'),
        BlockPcrWriter(designs, 1.2, 3, 22.8, 'pcr1'),
        GenePcrWriter(designs, 1.5, 3, 14.5, 'pcr2')
    ]

    out_dir_name = os.path.join(out_dir_parent, dte + exp_name)

    pipeline.run(writers, input_plates, parent_out_dir_name=out_dir_name)

    worklist.format_worklist(out_dir_name)


def _read_plates(input_plates):
    '''Read plates.'''
    oligos = utils.sort(
        [obj['id'] for obj in input_plates['wt'].get_all().values()])

    mutant_oligos = defaultdict(list)

    for obj in input_plates['mut'].get_all().values():
        mutant_oligos[obj['parent']].append(obj['id'])

    return oligos, mutant_oligos


def _combine(oligos, mutant_oligos, n_mutated, n_blocks):
    '''Design combinatorial assembly.'''

    # Assertion sanity checks:
    assert len(oligos) % 2 == 0
    assert len(oligos) / n_blocks >= 2
    assert mutant_oligos if n_mutated > 0 else True

    designs = []

    # Get combinations:
    for combi in itertools.combinations(list(mutant_oligos), n_mutated):
        design = list(oligos)

        for wt_id in combi:
            design[design.index(wt_id)] = wt_id + 'm'

        block_lengths = [0] * n_blocks

        for idx in itertools.cycle(range(0, n_blocks)):
            block_lengths[idx] = block_lengths[idx] + 2

            if sum(block_lengths) == len(design):
                break

        idx = 0
        blocks = []

        for val in block_lengths:
            blocks.append(design[idx: idx + val])
            idx = idx + val

        designs.append(blocks)

    return designs


def main(args):
    '''main method.'''
    import cProfile

    pr = cProfile.Profile()
    pr.enable()

    run(args[0], int(args[1]), int(args[2]), args[3], args[4])

    pr.disable()

    pr.print_stats(sort='cumtime')


if __name__ == '__main__':
    main(sys.argv[1:])