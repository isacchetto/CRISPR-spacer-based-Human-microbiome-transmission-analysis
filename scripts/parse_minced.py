#!/usr/bin/env python3

import os
import sys
import glob
import re
import pandas as pd
import time
from datetime import datetime
import argparse
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp
import subprocess
from threading import Lock
import itertools



# parse_minced.py
# Version 0.1
# 03/05/2024
# by isacchetto


# Argument parser
parser = argparse.ArgumentParser(description="Parse minced output files into a single TSV file")
parser.add_argument("input_directory", type=str, help="The input directory of the MinCED output files (file.crispr)")
parser.add_argument("-out", "--output", type=str, help="The output file, default is 'out/<input_directory>_parsed.tsv' (see --inplace for more info)", default=None, dest="out")
parser.add_argument("-i", "--inplace", action="store_true", help="Created output file near the input directory instead into the 'out' directory of the current working directory")
parser.add_argument("-t", "--threads", type=int, help="Number of threads to use", default=int(mp.cpu_count()/3), dest="num_cpus")
parser.add_argument("-n", "--dry-run", action="store_true", help="Print information about what would be done without actually doing it")
args = parser.parse_args()

# Check if input directory exists or not
if os.path.exists(args.input_directory):
    input_dir = os.path.abspath(args.input_directory)
else:
    print("The input directory does not exist", file=sys.stderr)
    exit()

# Create output file
if args.inplace:
    if args.out==None:
        # Create output file with unique name near the input directory
        output_file = f"{input_dir}_parsed.tsv"
    else:
        # Create output file with name specified by the user near the input directory
        output_file = os.path.join(input_dir.removesuffix(os.path.basename(input_dir)), os.path.basename(args.out))
else:
    if args.out==None:
        # Create output file with unique name in the out directory of the current working directory
        output_file = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_dir)}_parsed.tsv")
    else:
        # Create output file with name specified by the user in the out directory of the current working directory
        output_file = os.path.join(os.getcwd(), "out", os.path.basename(args.out))

# Check if output file exists and ask the user if they want to overwrite it
if os.path.exists(output_file) and not args.dry_run:
    print("The output file already exists, OVERWRITING IT? [y/N]", file=sys.stderr)
    overwrite = input()
    if overwrite.lower() != 'y':
        exit()
    else:
        os.remove(output_file)


class CRISPR(object):
    def __init__(self, contig_name, file_name):
        self.contig_name = contig_name.rstrip() # sequence = nome del contig
        self.repeats = []
        self.spacers = []
        self.file_name = file_name
    def setPos(self, start, end):
        self.start = int(start.rstrip())
        self.end = int(end.rstrip())
    def addRepeat(self, repeat):
        self.repeats.append(repeat.rstrip())
    def addSpacer(self, spacer):
        put_spacer = spacer.rstrip()
        if len(put_spacer) > 0:
            self.spacers.append(put_spacer)

def parse_minced(path):
    with open(path, 'r') as f:
        crisprs = []
        for ll in f:
            # Record sequence accession
            if ll.startswith('Sequence'):
                sequence_current = re.sub('\' \(.*', '', re.sub('Sequence \'', '', ll))
            # Create instance of CRISPR and add positions
            if ll.startswith('CRISPR'):
                crisp_tmp = CRISPR(sequence_current, path.split('/')[-1].split('.')[0])
                pos = re.sub('.*Range: ', '', ll)
                start = re.sub(' - .*', '', pos)
                end = re.sub('.* - ', '', pos)
                crisp_tmp.setPos(start, end)
            # Add Repeats and Spacers to the current instance
            if ll[:1].isdigit():
                lll = ll.split()
                if len(lll) == 7:
                    crisp_tmp.addRepeat(lll[1])
                    crisp_tmp.addSpacer(lll[2])
                if len(lll) == 2:
                    crisp_tmp.addRepeat(lll[1])
            # Save the instance
            if ll.startswith('Repeats'):
                crisprs.append(crisp_tmp)
    return crisprs

if __name__ == '__main__':

    basedir = '/shares/CIBIO-Storage/CM/scratch/users/matteo.ciciani/MetaRefSGB_Cas_mining/omegaRNA'
    outdir = '/shares/CIBIO-Storage/CM/scratch/users/matteo.ciciani/MetaRefSGB_Cas_mining/omegaRNA_preprocessed'
    releases = ['Sep22']

    files = [os.path.join(dirpath,filename) 
             for dirpath, _, filenames in os.walk(input_dir) 
             for filename in filenames 
             if filename.endswith('.crispr')
            ]
    tasks_total = len(files)
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    logging.info("Input: " + input_dir)
    logging.info("Output: " + output_file)
    logging.info(f"Found {tasks_total} files")
    # logging.info(f"Using {args.num_cpus} threads")

    if args.dry_run:
        logging.info('Dry run, exiting...')
        exit()


    for rel in releases:
        print('Processing {}...'.format(rel))
        rel_dfs = [] # lista di dataframe
        for chunk in os.listdir(os.path.join(basedir, rel)):
            crispr_paths = glob.glob(os.path.join(basedir, rel, chunk, '*.crispr')) 
            chunk_arrays = [array for path in crispr_paths for array in parse_minced(path)]
            chunk_array_df = pd.DataFrame([[a.mag, a.sequence, a.start, a.end, ','.join(a.spacers), ','.join(a.repeats)] for a in chunk_arrays])
            if chunk_array_df.shape[1]==6:
                chunk_array_df.columns = ['MAG', 'contig', 'start', 'end', 'spacers', 'repeats']
                rel_dfs.append(chunk_array_df)
        rel_data = pd.concat(rel_dfs).reset_index(drop=True)
        rel_data.to_csv(os.path.join(outdir, rel+'_CRISPR.tsv'), sep='\t')
        