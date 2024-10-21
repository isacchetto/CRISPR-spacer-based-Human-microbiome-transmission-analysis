#!/usr/bin/env python3
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
# from CRISPRtools.run import your_function_name

import os
import sys
import pandas as pd
from datetime import datetime
import argparse
import logging
import multiprocessing as mp
import run_CRISPRtools as rt



# parse_CRISPRDetect3.py
# Version 1.0
# 13/10/2024
# by isacchetto


# Argument parser
parser = argparse.ArgumentParser(description="Parse CRISPRDetect3 output files into a single TSV file")
parser.add_argument("input_directory", type=str, help="The input directory of the CRISPRDetect3 output files (file.CRISPRDetect3)")
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

if __name__ == '__main__':

    files = [os.path.join(dirpath,filename) 
             for dirpath, _, filenames in os.walk(input_dir) 
             for filename in filenames 
             if filename.endswith('.CRISPRDetect3.gff')
            ]
    tasks_total = len(files)
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    logging.info("Input: " + input_dir)
    logging.info('Parsed file: ./' + os.path.relpath(output_file))
    logging.info(f"Found {tasks_total} files")
    # logging.info(f"Using {args.num_cpus} threads")

    if args.dry_run:
        logging.info('Dry run, exiting...')
        exit()

    logging.info('RUNNING PARSE...')
    start_time = datetime.now()

    tasks_completed = 0
    # crisprs_total = [crispr for file in files for crispr in parse_minced(file)]
    crisprs_total = []
    error=0
    for file in files:
        try:
            crisprs_total+=rt.parse_CRISPRDetect3(file)
        except Exception as e:
            logging.error(f'Error parsing {file}: {e}')
            error += 1
        tasks_completed+=1
        print(f' Parsed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)

    crisprs_df = pd.DataFrame([[a.file_name, a.contig_name, a.start, a.end, ','.join(a.spacers), ','.join(a.repeats)] for a in crisprs_total],
                            columns=['MAG', 'Contig', 'Start', 'End', 'Spacers', 'Repeats'])

    crisprs_df.to_csv(output_file, sep='\t')

    end_time = datetime.now()
    logging.error(f'Errors: {error}/{tasks_total}')
    logging.info('Parse {}/{} Files in {}'.format(
        tasks_completed,
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Found {} CRISPRs'.format(len(crisprs_total)))
    logging.info('Done!')