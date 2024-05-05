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
# Version 1.0
# 03/05/2024
# by isacchetto


# Argument parser
parser = argparse.ArgumentParser(description="Parse minced output files into a single TSV file")
parser.add_argument("input_directory", type=str, help="The input directory of the MinCED output files (file.crispr)")
parser.add_argument("-out", "--output", type=str, help="The output file, default is 'out/<input_directory>_parsed.tsv' (see --inplace for more info)", default=None, dest="out")
parser.add_argument("-i", "--inplace", action="store_true", help="Created output file near the input directory instead into the 'out' directory of the current working directory")
parser.add_argument("-t", "--threads", type=int, help="Number of threads to use", default=mp.cpu_count()//3, dest="num_cpus")
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
    '''
    A class used to represent a CRISPR

    Attributes:
        file_name (str): the name of the file that the CRISPR was found in
        contig_name (str): the name of the contig that the CRISPR was found in
        start (int): the start position of the CRISPR (Position of the first base in the CRISPR)
        end (int): the end position of the CRISPR (position of the last base in the CRISPR)
        spacers (list): a list of the ordered spacers in the CRISPR
        repeats (list): a list of the ordered repeats in the CRISPR
    
    Methods:
        __init__(): Constructor
        __len__(): Returns the length of the CRISPR calculated as the sum of the lengths of the spacers and repeats
        __bool__(): Returns True if the CRISPR is valid, False otherwise
        setFile_name(file_name): Sets the file_name attribute
        setContig_name(contig_name): Sets the contig_name attribute
        setPos(start, end): Sets the start and end attributes
        addRepeat(repeat): Adds a repeat to the repeats list
        addSpacer(spacer): Adds a spacer to the spacers list
    '''
    def __init__(self):
        self.file_name = None 
        self.contig_name = None
        self.start = None
        self.end = None
        self.spacers = []
        self.repeats = []
    def __repr__(self):
        return f'<CRISPR object: (\n{self.file_name}\n{self.contig_name}\n{self.start}\n{self.end}\n{self.spacers}\n{self.repeats})>\n'
    def __str__(self):
        return f'f_name: {self.file_name}\ncontig: {self.contig_name}\nstart: {self.start}\nend: {self.end}\nspacers: {self.spacers}\nrepeats: {self.repeats}\n'
    def __len__(self):
        return sum(len(spacer) for spacer in self.spacers) + sum(len(repeat) for repeat in self.repeats)
    def __bool__(self):
        return (len(self) == (self.end - self.start + 1) and 
                type(self.file_name) is str and #self.file_name is not None and
                type(self.contig_name) is str and #self.contig_name is not None and
                type(self.start) is int and self.start >= 0 and
                type(self.end) is int and self.end >= self.start
                )
    def __eq__(self, other):
        return self.file_name == other.file_name and self.contig_name == other.contig_name and self.start == other.start and self.end == other.end
    
    def setFile_name(self, file_name):
        self.file_name = file_name
    def setContig_name(self, contig_name):
        self.contig_name = contig_name
    def setPos(self, start, end):
        self.start = start
        self.end = end
    def addRepeat(self, repeat):
        self.repeats.append(repeat)
    def addSpacer(self, spacer):
        self.spacers.append(spacer)

def parse_minced(file_path):
    crisprs = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("Sequence '"):
                contig_name = line.split("'")[1]
            elif line.startswith("CRISPR"):
                start, end = map(int, line.split()[3:6:2]) # Take from 4th to 6th element, step 2
                crispr_tmp = CRISPR()
                crispr_tmp.setFile_name(file_path.split('/')[-1].split('.')[0])
                crispr_tmp.setContig_name(contig_name)
                crispr_tmp.setPos(start, end)
            elif line[:1].isdigit():
                seqs = line.split()
                if len(seqs) == 7:
                    crispr_tmp.addRepeat(seqs[1])
                    crispr_tmp.addSpacer(seqs[2])
                if len(seqs) == 2:
                    crispr_tmp.addRepeat(seqs[1])
            # Save the instance
            elif line.startswith("Repeats"):
                if bool(crispr_tmp):
                    crisprs.append(crispr_tmp)
                else:
                    raise ValueError(f"Invalid CRISPR format in file {file_path}")
    return crisprs


if __name__ == '__main__':

    # input_dir = '/Users/isaccocenacchi/Desktop/Tirocinio/out/MAGs_short_minced'
    # output_file=f"{input_dir}_parsed.tsv"

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

    logging.info('Running!')
    start_time = datetime.now()

    tasks_completed = 0
    # crisprs_total = [crispr for file in files for crispr in parse_minced(file)]
    crisprs_total = []
    for file in files:
        crisprs_total+=parse_minced(file)
        tasks_completed+=1

    crisprs_df = pd.DataFrame([[a.file_name, a.contig_name, a.start, a.end, ','.join(a.spacers), ','.join(a.repeats)] for a in crisprs_total],
                            columns=['MAG', 'contig', 'start', 'end', 'spacers', 'repeats'])

    crisprs_df.to_csv(output_file, sep='\t')

    end_time = datetime.now()
    logging.info('Parse {}/{} Files in {}'.format(
        tasks_completed,
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Done!')
        