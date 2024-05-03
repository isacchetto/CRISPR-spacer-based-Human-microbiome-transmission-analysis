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

def batched(iterable, n):
    it = iter(iterable)
    while (batch := tuple(itertools.islice(it, n))):
        yield batch


if __name__ == '__main__':
    input_dir = '/Users/isaccocenacchi/Desktop/Tirocinio/MAGs_short_unzip'
    output_dir = "{}_crispr_{}".format(input_dir, time.strftime("%Y%m%d%H%M%S"))
    command="minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128"
    command_run=command.split()

    mags = [os.path.join(dirpath,filename) 
             for dirpath, _, filenames in os.walk(input_dir) 
             for filename in filenames 
             if filename.endswith('.fna')
            ]
    num_cpus = mp.cpu_count()
    lock = Lock()
    tasks_total = len(mags)
    tasks_completed = 0
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    logging.info("Command: " + str(command_run + ['<mag>']))


    # subprocess.Popen version
    tasks_completed = 0
    popens=[]
    ThreadPoolExecutor(1).submit(popen_progress_indicator, popens)
    logging.info('Running! subprocess.Popen version')
    start_time = datetime.now()
    for mag in mags:
        minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".crispr1", input_dir))
        os.makedirs(os.path.dirname(minced_mag), exist_ok=True)
        popen=subprocess.Popen(command_run + [mag], stdout=open(minced_mag, 'wb'))
        popens.append(popen)
    popens_returncode=[popen.wait() for popen in popens]
    end_time = datetime.now()
    logging.info('Minced {}/{} MAGs in {}'.format(
         popens_returncode.count(0),
         tasks_total, 
         datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Done!')

    # subprocess.Popen Batched version
    tasks_completed = 0
    popens=[]
    i=1
    logging.info('Running! subprocess.Popen Batched version')
    start_time = datetime.now()
    n_batchs=-(-tasks_total//num_cpus)
    logging.info(f'Divided in {n_batchs} parts')
    for batch in batched(mags, num_cpus):
        print(f' Running {i}/{n_batchs} part', end='\r', flush=True)
        i+=1
        for mag in batch:
            minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".crispr2", input_dir))
            os.makedirs(os.path.dirname(minced_mag), exist_ok=True)
            popen=subprocess.Popen(command_run + [mag], stdout=open(minced_mag, 'wb'))
            popens.append(popen)
        popens_returncode=[popen.wait() for popen in popens]
    end_time = datetime.now()
    logging.info('Minced {}/{} MAGs in {}'.format(
         popens_returncode.count(0),
         tasks_total, 
         datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Done!')

    # subprocess.run + ThreadPoolExecutor version
    tasks_completed = 0
    futures = []
    with ThreadPoolExecutor(num_cpus) as executor:
        logging.info('Running! subprocess.run + ThreadPoolExecutor version')
        start_time = datetime.now()
        for mag in mags:
            minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".crispr3", input_dir))
            os.makedirs(os.path.dirname(minced_mag), exist_ok=True)
            future=executor.submit(subprocess.run, command_run + [mag], stdout=open(minced_mag, 'wb'))
            future.add_done_callback(future_progress_indicator)
            futures.append(future)
    processes_returncode=[future.result().returncode for future in futures]
    end_time = datetime.now()
    logging.info('Minced {}/{} MAGs in {}'.format(
        processes_returncode.count(0),
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Done!')

    # # subprocess.run + ProcessPoolExecutor version (!!! NOT WORKING !!!)
    # tasks_completed = 0
    # futures = []
    # with ProcessPoolExecutor(num_cpus) as executor:
    #     logging.info('Running! subprocess.run + ProcessPoolExecutor version')
    #     start_time = datetime.now()
    #     for mag in mags:
    #         minced_mag=os.path.join(output_dir, os.path.relpath(mag[:-4]+".crispr4", input_dir))
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