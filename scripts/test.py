#!/usr/bin/env python3

import os
import argparse
import subprocess
from threading import Lock
import time
import logging
import bz2
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from glob import glob
import matplotlib.pyplot as plt
import pandas as pd
import shutil
import multiprocessing as mp
import itertools
import io
from datetime import datetime


# run_minced.py
# Version 0.1
# 18/04/2024
# by isacchetto

def progress_thread_indicator(future):
    global lock, tasks_total, tasks_completed
    # obtain the lock
    with lock:
        # update the counter
        tasks_completed += 1
        # report progress
        print(f'Running {tasks_completed} of {tasks_total} ...', end='\r', flush=True)

def progress_process_indicator(popens):
    global lock, tasks_total, tasks_completed
    while True:
        with lock:
            tasks_completed = sum([1 for popen in popens if popen.poll() is not None])
            if tasks_completed == tasks_total:
                break
            print(f'Running {tasks_completed} of {tasks_total} ...', end='\r', flush=True)
        time.sleep(1)

def unzip1(mag, unzipped_mag):
    with bz2.BZ2File(mag) as file, open(unzipped_mag,"wb") as new_file:
        shutil.copyfileobj(file,new_file)
    return 1

def unzip2(mag, unzipped_mag):
    with open(unzipped_mag, 'wb') as new_file, bz2.BZ2File(mag, 'rb') as file:
            for data in iter(lambda : file.read(100 * 1024), b''):
                new_file.write(data)
    return 1

def unzip3(mag, unzipped_mag):
    with open(unzipped_mag, 'wb') as new_file, open(mag, 'rb') as file:
            decompressor = bz2.BZ2Decompressor()
            for data in iter(lambda : file.read(100 * 1024), b''):
                new_file.write(decompressor.decompress(data))
    return 1

def batched(iterable, n):
    it = iter(iterable)
    while (batch := tuple(itertools.islice(it, n))):
        yield batch


if __name__ == '__main__':
    input_dir = '/Users/isaccocenacchi/Desktop/Tirocinio/MAGs_short'
    output_dir = "{}_crispr_{}".format(input_dir, time.strftime("%Y%m%d%H%M%S"))
    mags = [os.path.join(dirpath,filename) 
             for dirpath, _, filenames in os.walk(input_dir) 
             for filename in filenames 
             if filename.endswith('.bz2')
            ]
    num_cpus = mp.cpu_count()
    lock = Lock()
    tasks_total = len(mags)
    tasks_completed = 0
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    

    # ThreadPoolExecutor + unzip1 version
    futures = []
    with ThreadPoolExecutor(num_cpus) as executor:
        logging.info('Running!')
        start_time = datetime.now()
        for mag in mags:
            unzipped_mag=os.path.join(output_dir, os.path.relpath(mag[:-4], input_dir))
            os.makedirs(os.path.dirname(unzipped_mag), exist_ok=True)
            future=executor.submit(unzip1, mag, unzipped_mag)
            future.add_done_callback(progress_thread_indicator)
            futures.append(future)
    end_time = datetime.now()
    logging.info('Unzipped {}/{} MAGs in {}'.format(
         sum([future.result() for future in as_completed(futures)]), 
         tasks_total, 
         datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Done!')
        
    # # # Popen version
    # popens=[]
    # ThreadPoolExecutor(1).submit(progress_process_indicator, popens)
    # logging.info('Running!')
    # start_time = datetime.now()
    # for mag in mags:
    #     unzipped_mag=os.path.join(output_dir, os.path.relpath(mag[:-4], input_dir))
    #     os.makedirs(os.path.dirname(unzipped_mag), exist_ok=True)
    #     popen=subprocess.Popen(['bunzip2', '-kc', mag], stdout=open(unzipped_mag, 'wb'))
    #     popens.append(popen)
    # popens_returncode=[popen.wait() for popen in popens]
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} MAGs in {}'.format(
    #      popens_returncode.count(0),
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # Popen Batched version
    # popens=[]
    # i=1
    # logging.info('Running!')
    # start_time = datetime.now()
    # n_batchs=-(-tasks_total//num_cpus)
    # logging.info(f'Divided in {n_batchs} parts')
    # for batch in batched(mags, num_cpus):
    #     for mag in batch:
    #         unzipped_mag=os.path.join(output_dir, os.path.relpath(mag[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_mag), exist_ok=True)
    #         popen=subprocess.Popen(['bunzip2', '-kc', mag], stdout=open(unzipped_mag, 'wb'))
    #         popens.append(popen)
    #     popens_returncode=[popen.wait() for popen in popens]
    #     logging.info(f'Unzipped {i}/{n_batchs} part')
    #     i+=1
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} MAGs in {}'.format(
    #      popens_returncode.count(0),
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # ProcessPoolExecutor + unzip1 version
    # futures = []
    # with ProcessPoolExecutor(num_cpus) as executor:
    #     logging.info('Running!')
    #     start_time = datetime.now()
    #     for mag in mags:
    #         unzipped_mag=os.path.join(output_dir, os.path.relpath(mag[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_mag), exist_ok=True)
    #         future=executor.submit(unzip1, mag, unzipped_mag)
    #         future.add_done_callback(progress_thread_indicator)
    #         futures.append(future)
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} MAGs in {}'.format(
    #      sum([future.result() for future in as_completed(futures)]), 
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')

    # # Popen + ThreadPoolExecutor version
    # futures = []
    # with ThreadPoolExecutor(num_cpus) as executor:
    #     logging.info('Running!')
    #     start_time = datetime.now()
    #     for mag in mags:
    #         unzipped_mag=os.path.join(output_dir, os.path.relpath(mag[:-4], input_dir))
    #         os.makedirs(os.path.dirname(unzipped_mag), exist_ok=True)
    #         future=executor.submit(subprocess.Popen, ['bunzip2', '-kc', mag], stdout=open(unzipped_mag, 'wb'))
    #         future.add_done_callback(progress_thread_indicator)
    #         futures.append(future)
    # process_returncode=[future.result().wait() for future in futures]
    # end_time = datetime.now()
    # logging.info('Unzipped {}/{} MAGs in {}'.format(
    #      process_returncode.count(0), 
    #      tasks_total, 
    #      datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    # logging.info('Done!')