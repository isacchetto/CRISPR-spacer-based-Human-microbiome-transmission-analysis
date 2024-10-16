#!/usr/bin/env python3

import os
import sys
import shutil
import time
from datetime import datetime
import argparse
import logging
import bz2
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp
from threading import Lock
import subprocess
import itertools



# bunzip2_dir.py
# Version 1.0
# 24/04/2024
# by isacchetto

# Argument parser
parser = argparse.ArgumentParser(description="Unzip all .bz2 files in a directory with the same structure of the input directory")
parser.add_argument("input_directory", type=str, help="The input directory")
parser.add_argument("-o", "--output-dir", type=str, help="The output directory, default is 'out/<input_directory>_unzip_<timestamp>' (see --inplace for more info)", default=None, dest="out")
parser.add_argument("-i", "--inplace", action="store_true", help="Created output directory near the input directory instead into the 'out' directory of the current working directory")
parser.add_argument("-t", "--threads", type=int, help="Number of threads to use", default=mp.cpu_count(), dest="num_cpus")
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
        output_dir = f"{input_dir}_unzip_{time.strftime('%Y%m%d%H%M%S')}"
    else:
        # Create output directory with name specified by the user near the input directory
        output_dir = os.path.join(input_dir.removesuffix(os.path.basename(input_dir)), os.path.basename(args.out))
else:
    if args.out==None:
        # Create output directory with unique name in the out directory of the current working directory
        output_dir = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_dir)}_unzip_{time.strftime('%Y%m%d%H%M%S')}")
    else:
        # Create output directory with name specified by the user in the out directory of the current working directory
        output_dir = os.path.join(os.getcwd(), "out", os.path.basename(args.out))

# Check if output directory exists and ask the user if they want to overwrite it
if os.path.exists(output_dir):
    print("The output directory already exists, OVERWRITING IT? [y/N]", file=sys.stderr)
    overwrite = input()
    if overwrite.lower() != 'y':
        exit()
    else:
        shutil.rmtree(output_dir)


def future_progress_indicator(future):
    global lock, tasks_total, tasks_completed
    # obtain the lock
    with lock:
        # update the counter
        tasks_completed += 1
        # report progress
        print(f' Running {tasks_completed} of {tasks_total} ...', end='\r', flush=True)

def popen_progress_indicator(popens):
    global lock, tasks_total, tasks_completed
    while True:
        with lock:
            tasks_completed = sum([1 for popen in popens if popen.poll() is not None])
            if tasks_completed == tasks_total:
                break
            print(f' Running {tasks_completed} of {tasks_total} ...', end='\r', flush=True)
        time.sleep(1)

def unzip1(file, unzipped_file):
    with bz2.BZ2File(file) as file, open(unzipped_file,"wb") as new_file:
        shutil.copyfileobj(file,new_file)
    return 1

def unzip2(file, unzipped_file):
    with bz2.BZ2File(file, 'rb') as file, open(unzipped_file, 'wb') as new_file:
            for data in iter(lambda : file.read(100 * 1024), b''):
                new_file.write(data)
    return 1

def unzip3(file, unzipped_file):
    with open(unzipped_file, 'wb') as new_file, open(file, 'rb') as file:
            decompressor = bz2.BZ2Decompressor()
            for data in iter(lambda : file.read(100 * 1024), b''):
                new_file.write(decompressor.decompress(data))
    return 1

def batched(iterable, n):
    it = iter(iterable)
    while (batch := tuple(itertools.islice(it, n))):
        yield batch


if __name__ == '__main__':
    files = [os.path.join(dirpath,filename) 
             for dirpath, _, filenames in os.walk(input_dir) 
             for filename in filenames 
             if filename.endswith('.bz2')
            ]
    tasks_total = len(files)
    tasks_completed = 0
    lock = Lock()
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    logging.info("Input dir: " + input_dir)
    logging.info("Output dir: " + output_dir)
    logging.info(f"Found {tasks_total} Files")
    logging.info(f"Using {args.num_cpus} threads")

    if args.dry_run:
        logging.info('Dry run, exiting...')
        exit()

    # ThreadPoolExecutor + unzip1 version
    futures = []
    tasks_completed = 0
    with ThreadPoolExecutor(args.num_cpus) as executor:
        logging.info('Running! ThreadPoolExecutor + unzip1 version')
        start_time = datetime.now()
        for file in files:
            unzipped_file=os.path.join(output_dir, os.path.relpath(file[:-4], input_dir))
            os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
            future=executor.submit(unzip1, file, unzipped_file)
            future.add_done_callback(future_progress_indicator)
            futures.append(future)
    end_time = datetime.now()
    logging.info('Unzipped {}/{} Files in {}'.format(
         sum([future.result() for future in as_completed(futures)]), 
         tasks_total, 
         datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Done!')

    # # ThreadPoolExecutor + unzip2 version
    # futures = []
    # tasks_completed = 0
    # with ThreadPoolExecutor(args.num_cpus) as executor:
    #     logging.info('Running! ThreadPoolExecutor + unzip2 version')
    #     start_time = datetime.now()
    #     for file in files:
    #         unzipped_file=os.path.join(output_dir, os.path.relpath(file[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
    #         future=executor.submit(unzip2, file, unzipped_file)
    #         future.add_done_callback(future_progress_indicator)
    #         futures.append(future)
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} Files in {}'.format(
    #      sum([future.result() for future in as_completed(futures)]), 
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # ThreadPoolExecutor + unzip3 version
    # futures = []
    # tasks_completed = 0
    # with ThreadPoolExecutor(args.num_cpus) as executor:
    #     logging.info('Running! ThreadPoolExecutor + unzip3 version')
    #     start_time = datetime.now()
    #     for file in files:
    #         unzipped_file=os.path.join(output_dir, os.path.relpath(file[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
    #         future=executor.submit(unzip3, file, unzipped_file)
    #         future.add_done_callback(future_progress_indicator)
    #         futures.append(future)
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} Files in {}'.format(
    #      sum([future.result() for future in as_completed(futures)]), 
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')
        
    # # subprocess.Popen version
    # popens=[]
    # tasks_completed = 0
    # ThreadPoolExecutor(1).submit(popen_progress_indicator, popens)
    # logging.info('Running! subprocess.Popen version')
    # start_time = datetime.now()
    # for file in files:
    #     unzipped_file=os.path.join(output_dir, os.path.relpath(file[:-4], input_dir))
    #     os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
    #     popen=subprocess.Popen(['bunzip2', '-kc', file], stdout=open(unzipped_file, 'wb'))
    #     popens.append(popen)
    # popens_returncode=[popen.wait() for popen in popens]
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} Files in {}'.format(
    #      popens_returncode.count(0),
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # subprocess.Popen Batched version
    # popens=[]
    # tasks_completed = 0
    # i=1
    # logging.info('Running! subprocess.Popen Batched version')
    # start_time = datetime.now()
    # n_batchs=-(-tasks_total//args.num_cpus)
    # logging.info(f'Divided in {n_batchs} parts')
    # for batch in batched(files, args.num_cpus):
    #     print(f' Unzipped {i}/{n_batchs} part', end='\r', flush=True)
    #     i+=1
    #     for file in batch:
    #         unzipped_file=os.path.join(output_dir, os.path.relpath(file[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
    #         popen=subprocess.Popen(['bunzip2', '-kc', file], stdout=open(unzipped_file, 'wb'))
    #         popens.append(popen)
    #     popens_returncode=[popen.wait() for popen in popens]
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} Files in {}'.format(
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
    #     for file in files:
    #         unzipped_file=os.path.join(output_dir, os.path.relpath(file[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
    #         future=executor.submit(subprocess.run, ['bunzip2', '-kc', file], stdout=open(unzipped_file, 'wb'))
    #         future.add_done_callback(future_progress_indicator)
    #         futures.append(future)
    # processes_returncode=[future.result().returncode for future in futures]
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} Files in {}'.format(
    #     processes_returncode.count(0),
    #     tasks_total, 
    #     datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # ProcessPoolExecutor + unzip1 version
    # tasks_completed = 0
    # futures = []
    # with ProcessPoolExecutor(args.num_cpus) as executor:
    #     logging.info('Running! ProcessPoolExecutor + unzip1 version')
    #     start_time = datetime.now()
    #     for file in files:
    #         unzipped_file=os.path.join(output_dir, os.path.relpath(file[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
    #         future=executor.submit(unzip1, file, unzipped_file)
    #         future.add_done_callback(future_progress_indicator)
    #         futures.append(future)
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} Files in {}'.format(
    #      sum([future.result() for future in as_completed(futures)]), 
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')