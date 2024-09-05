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
from simple_term_menu import TerminalMenu



# run_tools.py
# Version 1.0
# 18/06/2024
# by isacchetto

# Argument parser
parser = argparse.ArgumentParser(description="Run minced/pilercr/CRISPRDetect3 on a directory of MAGs")
parser.add_argument("input_directory", type=str, help="The input directory of the MAGs")
parser.add_argument("-d", "--decompress", action="store_true", help="Use this flag if the MAGs are compressed in .bz2 format")
parser.add_argument("-out", "--output-dir", type=str, help="The output directory, default is 'out/<input_directory>_CRISPRDetect3_<timestamp>' (see --inplace for more info)", default=None, dest="out")
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

# Select the tool to use
tools = ["minced", "pilercr", "CRISPRDetect3"]
terminal_menu = TerminalMenu(tools, title="Select the tool to use:  (Press Q or Esc to quit) \n", 
                             menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                             menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                             clear_screen=True, raise_error_on_interrupt=True,)
try: menu_entry_index = terminal_menu.show()
except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
if menu_entry_index is None: 
    print("No tool selected, ", file=sys.stderr); exit()
else:
    tool=tools[menu_entry_index]

# Create output directory
if args.inplace:
    if args.out==None:
        # Create output directory with unique name near the input directory
        output_dir = f"{input_dir}_{tool}_{time.strftime('%Y%m%d%H%M%S')}"
    else:
        # Create output directory with name specified by the user near the input directory
        output_dir = os.path.join(input_dir.removesuffix(os.path.basename(input_dir)), os.path.basename(args.out))
else:
    if args.out==None:
        # Create output directory with unique name in the out directory of the current working directory
        output_dir = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_dir)}_{tool}_{time.strftime('%Y%m%d%H%M%S')}")
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

# Function to report progress
def future_progress_indicator(future):
    global lock_tasks, tasks_total, tasks_completed
    # obtain the lock
    with lock_tasks:
        if future.result() == 1:
            # update the counter on
            tasks_completed += 1
        # report progress
        print(f' Completed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)

# Function to unzip and run the tool
def unzip_and_run(command_run, input_file, output_file):
    global errors, lock_errors
    with open(input_file, 'rb') as file, tempfile.NamedTemporaryFile("wb", suffix="_" + os.path.basename(input_file)[:-8]+".fna", delete=True) as tmp_file:
        decompressor = bz2.BZ2Decompressor()
        for data in iter(lambda : file.read(100 * 1024), b''):
            tmp_file.write(decompressor.decompress(data))
        match tool:
            case "minced":
                completedProcess = subprocess.run(command_run + [tmp_file.name], stdout=open(output_file, 'wb'))
            case "pilercr":
                completedProcess = subprocess.run(command_run + ['-in', tmp_file.name, '-out', output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            case "CRISPRDetect3":
                completedProcess = subprocess.run(['conda', 'run', '-n', 'CRISPRDetect'] + command_run + ['-f', tmp_file.name, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}: {tool} returned {e.returncode}")
        return 0
    else:
        return 1

# Function to run the tool
def run(command_run, input_file, output_file):
    global errors, lock_errors
    match tool:
        case "minced":
            completedProcess = subprocess.run(command_run + [input_file], check=True, stdout=open(output_file, 'wb'))
        case "pilercr":
            completedProcess = subprocess.run(command_run + ['-in', input_file, '-out', output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        case "CRISPRDetect3":
            completedProcess = subprocess.run(['conda', 'run', '-n', 'CRISPRDetect'] + command_run + ['-f', input_file, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}:  {tool} returned {e.returncode}")
        return 0
    else:
        return 1


if __name__ == '__main__':

    # COMMANDS
    match tool:
        case "minced":
            # minced default parameters:
            # -searchWL 8 -minNR 3
            # -minRL 23 -maxRL 47
            # -minSL 26 -maxSL 50

            commands = {"Paper":"minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128", 
                        "Default":"minced -minNR 3 -minRL 23 -maxRL 47 -minSL 26 -maxSL 50"}
            terminal_menu = TerminalMenu(commands, title="minced command:\n", 
                             menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                             menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                             clear_screen=True, raise_error_on_interrupt=True, preview_command=commands[{}])
            try: menu_entry_index = terminal_menu.show()
            except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
            if menu_entry_index is None: 
                print("No command selected, ", file=sys.stderr); exit()
            else:
                command=commands[menu_entry_index]
            exit()
            command="minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128" # Parameters on Paper PMCID: PMC10910872
            # command="minced -minNR 3 -minRL 23 -maxRL 47 -minSL 26 -maxSL 50" # Default command
        case "pilercr":
            # pilercr default parameters:
            # -minarray 3 -mincons 0.9 
            # -minrepeat 16 -maxrepeat 64 
            # -minspacer 8 -maxspacer 64 
            # -minrepeatratio 0.9 -minspacerratio 0.75 
            # -minhitlength 16 -minid 0.94
            
            # command="pilercr -noinfo -quiet" # PILER_1 (default)
            command= "pilercr -noinfo -quiet -minarray 3 -mincons 0.8 -minid 0.85 -maxrepeat 128 -maxspacer 128" # PILER_2
        case "CRISPRDetect3":
            # CRISPRDetect3 default parameters:
            # -q 0 (quiet)
            # -T 4 (number of threads)
            # -check_direction 1
            # -annotate_cas_genes 0
            # -array_quality_score_cutoff 3 (default for fasta files, "4" for GenBank files with cas annotations)

            # word_length=11
            # minimum_word_repeatation=3

            # repeat_length_cutoff=17
            # minimum_no_of_repeats=3
            # minimum_repeat_length=23

            # max_gap_between_crisprs=500
            # left_flank_length=500
            # right_flank_length=500

            # minimum_spacer_gap=50-word_length
            # maximum_spacer_gap=100+word_length

            # remove_insertion_from_repeat=1

            # fix_gaps_in_repeats=1
            
            command= "CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -T 0 -left_flank_length 0 -right_flank_length 0"

    command_run=command.split()

    # Find all MAGs in the input directory
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

    # Set up logging
    if args.dry_run:
        logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    else:
        os.makedirs(output_dir, exist_ok=True)
        logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO', handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(output_dir, 'run_crisprdetect3.log'))])
    logging.info("Tool: " + tool)
    logging.info("Input: " + input_dir)
    logging.info("Output: " + output_dir)
    match tool:
        case "minced":
            logging.info("Command: " + str(command_run + ['<mag>', '>', '<out.minced>' ]))
        case "pilercr":
            logging.info("Command: " + str(command_run + ['-in','<mag>', '-out', '<out.pilercr>' ]))
        case "CRISPRDetect3":
            logging.info("Command: " + str(command_run + ['-f','<mag>', '-o', '<out.CRISPRDetect3>' ]))
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
            output_file=os.path.join(output_dir, os.path.relpath(mag.rsplit('.', 2 if args.decompress else 1)[0]+"."+tool, input_dir))
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            if args.decompress:
                future=executor.submit(unzip_and_run, command_run, mag, output_file)
            else:
                future=executor.submit(run, command_run, mag, output_file)
            future.add_done_callback(future_progress_indicator)
    end_time = datetime.now()
    logging.info('Runned {}/{} MAGs in {}'.format(
        tasks_completed,
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    if errors:
        [logging.error(error) for error in errors]
        logging.error('Done with errors!')
    else:
        logging.info('Done!')
