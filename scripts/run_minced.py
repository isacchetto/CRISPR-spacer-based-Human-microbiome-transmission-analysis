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
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp
from threading import Lock
import itertools
import tempfile


# run_minced.py
# Version 1.0
# 03/05/2024
# by isacchetto

# Argument parser
parser = argparse.ArgumentParser(description="Run minced on a directory of MAGs")
parser.add_argument("input_directory", type=str, help="The input directory of the MAGs")
parser.add_argument("-d", "--decompress", action="store_true", help="Use this flag if the MAGs are compressed in .bz2 format")
parser.add_argument("-out", "--output-dir", type=str, help="The output directory, default is 'out/<input_directory>_minced_<timestamp>' (see --inplace for more info)", default=None, dest="out")
parser.add_argument("-i", "--inplace", action="store_true", help="Created output directory near the input directory instead into the 'out' directory of the current working directory")
parser.add_argument("-t", "--threads", type=int, help="Number of threads to use", default=mp.cpu_count()//3, dest="num_cpus")
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
        output_dir = f"{input_dir}_minced_{time.strftime('%Y%m%d%H%M%S')}"
    else:
        # Create output directory with name specified by the user near the input directory
        output_dir = os.path.join(input_dir.removesuffix(os.path.basename(input_dir)), os.path.basename(args.out))
else:
    if args.out==None:
        # Create output directory with unique name in the out directory of the current working directory
        output_dir = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_dir)}_minced_{time.strftime('%Y%m%d%H%M%S')}")
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

def popen_progress_indicator(popens):
    global lock, tasks_total, tasks_completed
    while True:
        with lock:
            tasks_completed = sum([1 for popen in popens if popen.poll() is not None])
            if tasks_completed == tasks_total:
                break
            print(f' Completed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)
        time.sleep(1)

def batched(iterable, n):
    it = iter(iterable)
    while (batch := tuple(itertools.islice(it, n))):
        yield batch

def unzip_and_run(command_run, input_file, output_file):
    global errors, lock_errors
    with open(input_file, 'rb') as file, tempfile.NamedTemporaryFile("wb",prefix=os.path.basename(input_file)[:-8], suffix=".fna", delete=True) as tmp_file:
        decompressor = bz2.BZ2Decompressor()
        for data in iter(lambda : file.read(100 * 1024), b''):
            tmp_file.write(decompressor.decompress(data))
        completedProcess = subprocess.run(command_run + [tmp_file.name], stdout=open(output_file, 'wb'))
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}: minced returned {e.returncode}")
        return 0
    else:
        return 1

def run(command_run, input_file, output_file):
    global errors, lock_errors
    try: subprocess.run(command_run + [input_file], stdout=open(output_file, 'wb'), check=True)
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}: minced returned {e.returncode}")
        return 0
    else:
        return 1


if __name__ == '__main__':


    command="minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128" # Parameters on Paper PMCID: PMC10910872
    # command="minced -minNR 3 -minRL 23 -maxRL 47 -minSL 26 -maxSL 50" # Default command
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
    logging.info("Command: " + str(command_run + ['<mag>']))
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
            output_file=os.path.join(output_dir, os.path.relpath(mag[:-8]+".minced", input_dir))
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            if args.decompress:
                future=executor.submit(unzip_and_run, command_run, mag, output_file)
            else:
                future=executor.submit(run, command_run, mag, output_file)
            future.add_done_callback(future_progress_indicator)
    end_time = datetime.now()
    logging.info('Minced {}/{} MAGs in {}'.format(
        tasks_completed,
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    if errors:
        [logging.error(error) for error in errors]
        logging.error('Done with errors!')
    else:
        logging.info('Done!')

    # # subprocess.Popen version (!!! TOO COMPUTATIONALLY INTENSIVE !!!)
    # tasks_completed = 0
    # popens=[]
    # ThreadPoolExecutor(1).submit(popen_progress_indicator, popens)
    # logging.info('Running! subprocess.Popen version')
    # start_time = datetime.now()
    # for mag in mags:
    #     minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".minced", input_dir))
    #     os.makedirs(os.path.dirname(minced_mag), exist_ok=True)
    #     popen=subprocess.Popen(command_run + [mag], stdout=open(minced_mag, 'wb'))
    #     popens.append(popen)
    # popens_returncode=[popen.wait() for popen in popens]
    # end_time = datetime.now()
    # logging.info('Minced {}/{} MAGs in {}'.format(
    #      popens_returncode.count(0),
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # subprocess.run + ThreadPoolExecutor version
    # tasks_completed = 0
    # futures = []
    # with ThreadPoolExecutor(args.num_cpus) as executor:
    #     logging.info('Running! subprocess.run + ThreadPoolExecutor version')
    #     start_time = datetime.now()
    #     for mag in mags:
    #         minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".minced", input_dir))
    #         os.makedirs(os.path.dirname(minced_mag), exist_ok=True)
    #         future=executor.submit(subprocess.run, command_run + [mag], stdout=open(minced_mag, 'wb'))
    #         future.add_done_callback(future_progress_indicator)
    #         futures.append(future)
    # processes_returncode=[future.result().returncode for future in futures]
    # end_time = datetime.now()
    # logging.info('Minced {}/{} MAGs in {}'.format(
    #     processes_returncode.count(0),
    #     tasks_total, 
    #     datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # subprocess.Popen Batched version
    # tasks_completed = 0
    # popens=[]
    # i=1
    # logging.info('Running! subprocess.Popen Batched version')
    # start_time = datetime.now()
    # n_batchs=-(-tasks_total//args.num_cpus)
    # logging.info(f'Divided in {n_batchs} parts')
    # for batch in batched(mags, args.num_cpus):
    #     print(f' Running {i}/{n_batchs} part', end='\r', flush=True)
    #     i+=1
    #     for mag in batch:
    #         minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".minced", input_dir))
    #         os.makedirs(os.path.dirname(minced_mag), exist_ok=True)
    #         popen=subprocess.Popen(command_run + [mag], stdout=open(minced_mag, 'wb'))
    #         popens.append(popen)
    #     popens_returncode=[popen.wait() for popen in popens]
    # end_time = datetime.now()
    # logging.info('Minced {}/{} MAGs in {}'.format(
    #      popens_returncode.count(0),
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # subprocess.run + ProcessPoolExecutor version (!!! NOT WORKING !!!)
    # tasks_completed = 0
    # futures = []
    # with ProcessPoolExecutor(args.num_cpus) as executor:
    #     logging.info('Running! subprocess.run + ProcessPoolExecutor version')
    #     start_time = datetime.now()
    #     for mag in mags:
    #         minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".minced", input_dir))
    #         os.makedirs(os.path.dirname(minced_mag), exist_ok=True)
    #         future=executor.submit(subprocess.run, command_run + [mag], stdout=open(minced_mag, 'wb'))
    #         future.add_done_callback(future_progress_indicator)
    #         futures.append(future)
    # processes_returncode=[future.result().returncode for future in futures]
    # end_time = datetime.now()
    # logging.info('Minced {}/{} MAGs in {}'.format(
    #     processes_returncode.count(0),
    #     tasks_total, 
    #     datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')