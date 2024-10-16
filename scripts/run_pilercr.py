#!/usr/bin/env python3

import bz2
import os
import subprocess
import sys
import shutil
import time
from datetime import datetime
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
from threading import Lock
import tempfile


# run_pilercr.py
# Version 1.0
# 31/05/2024
# by isacchetto

# Argument parser
parser = argparse.ArgumentParser(description="Run pilercr on a directory of MAGs")
parser.add_argument("input_directory", type=str, help="The input directory of the MAGs")
parser.add_argument("-d", "--decompress", action="store_true", help="Use this flag if the MAGs are compressed in .bz2 format")
parser.add_argument("-out", "--output-dir", type=str, help="The output directory, default is 'out/<input_directory>_pilercr_<timestamp>' (see --inplace for more info)", default=None, dest="out")
parser.add_argument("-i", "--inplace", action="store_true", help="Created output directory near the input directory instead into the 'out' directory of the current working directory")
parser.add_argument("-t", "--threads", type=int, help="Number of threads to use (default ALL/3)", default=mp.cpu_count()//3, dest="num_cpus")
parser.add_argument("-n", "--dry-run", action="store_true", help="Print information about what would be done without actually doing it")
args = parser.parse_args()

# Check if input directory exists or not
if os.path.exists(args.input_directory):
    input_dir = os.path.abspath(args.input_directory)
else:
    print("The input directory does not exist", file=sys.stderr)
    exit()

# Create output directory
if args.inplace:
    if args.out==None:
        # Create output directory with unique name near the input directory
        output_dir = f"{input_dir}_pilercr_{time.strftime('%Y%m%d%H%M%S')}"
    else:
        # Create output directory with name specified by the user near the input directory
        output_dir = os.path.join(input_dir.removesuffix(os.path.basename(input_dir)), os.path.basename(args.out))
else:
    if args.out==None:
        # Create output directory with unique name in the out directory of the current working directory
        output_dir = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_dir)}_pilercr_{time.strftime('%Y%m%d%H%M%S')}")
    else:
        # Create output directory with name specified by the user in the out directory of the current working directory
        output_dir = os.path.join(os.getcwd(), "out", os.path.basename(args.out))

# Check if output directory exists and ask the user if they want to overwrite it
if os.path.exists(output_dir) and not args.dry_run:
    print(f"The output directory already exists: '{output_dir}'\nOVERWRITING IT? [y/N]", file=sys.stderr)
    overwrite = input()
    if overwrite.lower() != 'y':
        exit()
    else:
        shutil.rmtree(output_dir)


def future_progress_indicator(future):
    global lock_tasks, tasks_total, tasks_completed
    # obtain the lock
    with lock_tasks:
        if future.result() == 1:
            # update the counter on
            tasks_completed += 1
        # report progress
        print(f' Completed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)

def unzip_and_run(command_run, input_file, output_file):
    global errors, lock_errors
    with open(input_file, 'rb') as file, tempfile.NamedTemporaryFile("wb", suffix="_" + os.path.basename(input_file)[:-8]+".fna", delete=True) as tmp_file:
        decompressor = bz2.BZ2Decompressor()
        for data in iter(lambda : file.read(100 * 1024), b''):
            tmp_file.write(decompressor.decompress(data))
        completedProcess = subprocess.run(command_run + ['-in', tmp_file.name, '-out', output_file])
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}: pilercr returned {e.returncode}")
        return 0
    else:
        return 1

def run(command_run, input_file, output_file):
    global errors, lock_errors
    try: subprocess.run(command_run + ['-in', input_file, '-out', output_file], check=True)
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}: pilercr returned {e.returncode}")
        return 0
    else:
        return 1


if __name__ == '__main__':

    # Default parameters:
    # -minarray 3 -mincons 0.9 
    # -minrepeat 16 -maxrepeat 64 
    # -minspacer 8 -maxspacer 64 
    # -minrepeatratio 0.9 -minspacerratio 0.75 
    # -minhitlength 16 -minid 0.94
    
    # command="pilercr -noinfo -quiet" # PILER_1 (default)
    command= "pilercr -noinfo -quiet -minarray 3 -mincons 0.8 -minid 0.85 -maxrepeat 128 -maxspacer 128" # PILER_2

    command_run=command.split()


    if args.decompress:
        mags = [os.path.join(dirpath,filename)
                for dirpath, _, filenames in os.walk(input_dir)
                for filename in filenames
                if filename.endswith('.bz2')
               ]
    else:
        mags = [os.path.join(dirpath,filename) 
                    for dirpath, _, filenames in os.walk(input_dir) 
                    for filename in filenames 
                    if filename.endswith('.fna')
                ]
    tasks_total = len(mags)
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    logging.info("Input: " + input_dir)
    logging.info("Output: " + output_dir)
    logging.info("Command: " + str(command_run + ['-in','<mag>', '-out', '<out.pilercr>' ]))
    logging.info(f"Found {tasks_total} MAGs")
    logging.info(f"Using {args.num_cpus} threads")
    if args.dry_run:
        logging.info('Dry run, exiting...')
        exit()

    # ThreadPoolExecutor + subprocess.run  version
    lock_tasks = Lock()
    lock_errors = Lock()
    tasks_completed = 0
    errors = []
    with ThreadPoolExecutor(args.num_cpus) as executor:
        logging.info(f'Running! {"unzip + " if args.decompress else ""} subprocess.run + ThreadPoolExecutor version')
        start_time = datetime.now()
        for mag in mags:
            output_file=os.path.join(output_dir, os.path.relpath(mag[:-8]+".pilercr", input_dir))
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            if args.decompress:
                future=executor.submit(unzip_and_run, command_run, mag, output_file)
            else:
                future=executor.submit(run, command_run, mag, output_file)
            future.add_done_callback(future_progress_indicator)
    end_time = datetime.now()
    logging.info('Pilercr {}/{} MAGs in {}'.format(
        tasks_completed,
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    if errors:
        [logging.error(error) for error in errors]
        logging.error('Done with errors!')
    else:
        logging.info('Done!')
