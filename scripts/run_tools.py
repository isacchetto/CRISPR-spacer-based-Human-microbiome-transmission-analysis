#!/usr/bin/env python3

import os
import sys
import shutil
import bz2
import subprocess
import time
from datetime import datetime
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
from threading import Lock
import tempfile
from simple_term_menu import TerminalMenu
import pandas as pd



# run_tools.py
# Version 1.0
# 01/10/2024
# by isacchetto

# Argument parser
parser = argparse.ArgumentParser(description="Run minced/pilercr/CRISPRDetect3 on a directory of MAGs, and create a file.tsv of CRISPRs found with this column: MAG, Contig, Start, End, Spacers, Repeats, Cas_0-1000, Cas_1000-10000, Cas_>100000, Cas_overlayed")
parser.add_argument("input_directory", type=str, help="The input directory of the MAGs")
parser.add_argument("-d", "--decompress", action="store_true", help="Use this flag if the MAGs are compressed in .bz2 format")
parser.add_argument("-out", "--output-dir", type=str, help="The output directory, default is './out/<input_directory>_CRISPRDetect3_<timestamp>' (see --inplace for more info)", default=None, dest="out")
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

# Verify the presence of the tools
tools = []
if shutil.which("minced"):
    tools.append("minced")
if shutil.which("pilercr"):
    tools.append("pilercr")
if shutil.which("CRISPRDetect3"):
    tools.append("CRISPRDetect3")
if not tools:
    print("No tools found: minced, pilercr, CRISPRDetect3", file=sys.stderr)
    exit()

# Select the tool to use
tools_menu = TerminalMenu(tools, title="Select the tool to use:  (Press Q or Esc to quit) \n", 
                             menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                             menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                             clear_screen=True, raise_error_on_interrupt=True)
try: menu_tool_index = tools_menu.show()
except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
if menu_tool_index is None: 
    print("No tool selected", file=sys.stderr); exit()
else:
    tool=tools[menu_tool_index]

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
                completedProcess = subprocess.run(command_run + [tmp_file.name], stdout=open(output_file, 'wb'), stderr=subprocess.DEVNULL)
            case "pilercr":
                completedProcess = subprocess.run(command_run + ['-in', tmp_file.name, '-out', output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            case "CRISPRDetect3":
                # completedProcess = subprocess.run(['conda', 'run', '-n', 'CRISPRDetect'] + command_run + ['-f', tmp_file.name, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                completedProcess = subprocess.run(command_run + ['-f', tmp_file.name, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            completedProcess = subprocess.run(command_run + [input_file], check=True, stdout=open(output_file, 'wb'), stderr=subprocess.DEVNULL)
        case "pilercr":
            completedProcess = subprocess.run(command_run + ['-in', input_file, '-out', output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        case "CRISPRDetect3":
            # completedProcess = subprocess.run(['conda', 'run', '-n', 'CRISPRDetect'] + command_run + ['-f', input_file, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            completedProcess = subprocess.run(command_run + ['-f', input_file, '-o', output_file], check=True, stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}:  {tool} returned {e.returncode}")
        return 0
    else:
        return 1

# Function to show the command preview for TerminalMenu
def show_preview(command):
    return commands[command]


class CRISPR:
    '''
    A class used to represent a CRISPR array

    Attributes:
        file_name (str): the name of the file that the CRISPR was found in (MAG name)
        contig_name (str): the name of the contig that the CRISPR was found in
        start (int): Position of the first base in the CRISPR (one-indexed, inclusive)
        end (int): position of the last base in the CRISPR (one-indexed, inclusive)
        spacers (list): a list of the ordered spacers in the CRISPR
        repeats (list): a list of the ordered repeats in the CRISPR
        flankers (dict): a dictionary with the left and right flankers of the CRISPR
    
    Methods:
        __init__(): Constructor
        __len__(): Returns the length of the CRISPR calculated as the sum of the lengths of the spacers and repeats
        __bool__(): Returns True if the CRISPR is valid, False otherwise
        setFile_name(file_name): Sets the file_name attribute
        setContig_name(contig_name): Sets the contig_name attribute
        setStart(start): Sets the start attribute
        setEnd(end): Sets the end attribute
        addRepeat(repeat): Adds a repeat to the repeats list
        addSpacer(spacer): Adds a spacer to the spacers list
        setFlankerLeft(left): Sets the left flanker
        setFlankerRight(right): Sets the right flanker
    '''
    def __init__(self, file_name=None, contig_name=None, start=None, end=None):
        self.file_name = file_name
        self.contig_name = contig_name
        self.start = start
        self.end = end
        self.spacers = []
        self.repeats = []
        self.flankers = {'left': '', 'right': ''}
    
    def __repr__(self):
        return f'<CRISPR object: (\n{self.file_name}\n{self.contig_name}\n{self.start}\n{self.end}\n{self.spacers}\n{self.repeats}\n{self.flankers})>\n'
    
    def __str__(self):
        return f'f_name: {self.file_name}\ncontig: {self.contig_name}\nstart: {self.start}\nend: {self.end}\nspacers: {self.spacers}\nrepeats: {self.repeats}\nflankers: {self.flankers}\n'
    
    def __len__(self):
        return sum(len(spacer) for spacer in self.spacers) + sum(len(repeat) for repeat in self.repeats)
    
    def __bool__(self):
        return (isinstance(self.file_name, str) and self.file_name != '' and
                isinstance(self.contig_name, str) and self.contig_name != '' and
                isinstance(self.start, int) and self.start >= 0 and
                isinstance(self.end, int) and self.end >= self.start and
                len(self) == (self.end - self.start + 1))
    
    def __eq__(self, other):
        return self.file_name == other.file_name and self.contig_name == other.contig_name and self.start == other.start and self.end == other.end
    
    def setFile_name(self, file_name):
        self.file_name = file_name
    
    def setContig_name(self, contig_name):
        self.contig_name = contig_name
    
    def setStart(self, start):
        self.start = start

    def setEnd(self, end):
        self.end = end
    
    def addRepeat(self, repeat):
        self.repeats.append(repeat)
    
    def addSpacer(self, spacer):
        self.spacers.append(spacer)

    def setFlankerLeft(self, left):
        self.flankers['left'] = left

    def setFlankerRight(self, right):
        self.flankers['right'] = right

def parse_minced(file_path):
    crisprs = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("Sequence '"):
                contig_name = line.split("'")[1]
            elif line.startswith("CRISPR"):
                start, end = map(int, line.split()[3:6:2]) # Take from 4th to 6th element, step 2
                crispr_tmp = CRISPR(file_name=file_path.split('/')[-1].split('.')[0], contig_name=contig_name, start=start, end=end)
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

def develop_repeats(repeats, reference):
    developed_repeats = []
    for repeat in repeats:
        repeat = list(repeat)
        for i in range(len(reference)):
            if repeat[i] == '.': 
                repeat[i] = reference[i]
        repeat = ''.join(repeat)
        repeat = repeat.replace('-', '')
        developed_repeats.append(repeat)
    return developed_repeats

def parse_pilercr(file_path):
    crisprs = []
    with open(file_path, 'r') as file:
        crispr_tmp = None
        for line in file:
            line = line.strip()
            if line.startswith("Array"):
                if crispr_tmp is not None:
                    raise ValueError(f"CRISPR not finished in file {file_path}, contig {crispr_tmp.contig_name}")
            elif line.startswith(">"):
                contig_name = line[1:]
            elif line[:1].isdigit():
                seqs = line.split()
                if len(seqs) == 7 and crispr_tmp is None: # first line: flankerLeft - repeat - spacer
                    start=int(seqs[0]) + seqs[5][:seqs[5].find(".")].count("-") # adjust start position if there are gaps in the repeat
                    crispr_tmp = CRISPR(file_name=file_path.split('/')[-1].split('.')[0], contig_name=contig_name, start=start, end=None)
                    crispr_tmp.setFlankerLeft(seqs[4])
                    repeats = [seqs[5]]
                    crispr_tmp.addSpacer(seqs[6])
                elif len(seqs) == 7 and crispr_tmp is not None: # next line: repeat - spacer
                    repeats.append(seqs[5])
                    crispr_tmp.addSpacer(seqs[6])
                elif len(seqs) == 6 and crispr_tmp is not None: # last line: repeat - flankerRight
                    repeats.append(seqs[4])
                    crispr_tmp.setFlankerRight(seqs[5])
                elif len(seqs) == 4 and crispr_tmp is not None: # consensus repeat
                    consensus = seqs[3]
                    for repeat in develop_repeats(repeats, consensus):
                        crispr_tmp.addRepeat(repeat)
                    repeats = []
                    crispr_tmp.setEnd(crispr_tmp.start + len(crispr_tmp) - 1)
                    if bool(crispr_tmp):
                        crisprs.append(crispr_tmp)
                        crispr_tmp = None
                    else:
                        raise ValueError(f"Invalid CRISPR format in file {file_path}")
            elif line.startswith("SUMMARY"):
                break
        return crisprs

if __name__ == '__main__':

    # COMMANDS
    match tool:
        case "minced":
            # minced default parameters:
            # -searchWL 8 -minNR 3
            # -minRL 23 -maxRL 47
            # -minSL 26 -maxSL 50

            commands = {"Paper":"minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128", # Parameters on Paper PMCID: PMC10910872
                        "Default":"minced -minNR 3 -minRL 23 -maxRL 47 -minSL 26 -maxSL 50"} # Default command
            commands_menu = TerminalMenu(commands, title="minced command:\n", 
                             menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                             menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                             clear_screen=True, raise_error_on_interrupt=True, preview_command=show_preview)
            try: menu_command_index = commands_menu.show()
            except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
            if menu_command_index is None: 
                print("No command selected, ", file=sys.stderr); exit()
            else:
                command=list(commands.values())[menu_command_index]
        case "pilercr":
            # pilercr default parameters:
            # -minarray 3 -mincons 0.9 
            # -minrepeat 16 -maxrepeat 64 
            # -minspacer 8 -maxspacer 64 
            # -minrepeatratio 0.9 -minspacerratio 0.75 
            # -minhitlength 16 -minid 0.94
            
            commands = {"PILER_1 (default)":"pilercr -noinfo -quiet",
                        "PILER_2":"pilercr -noinfo -quiet -minarray 3 -mincons 0.8 -minid 0.85 -maxrepeat 128 -maxspacer 128"}
            commands_menu = TerminalMenu(commands, title="pilercr command:\n", 
                             menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                             menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                             clear_screen=True, raise_error_on_interrupt=True, preview_command=show_preview)
            try: menu_command_index = commands_menu.show()
            except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
            if menu_command_index is None: 
                print("No command selected, ", file=sys.stderr); exit()
            else:
                command=list(commands.values())[menu_command_index]
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
            commands = {"CRISPRDetect3":"CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -T 0 -left_flank_length 0 -right_flank_length 0"}
            commands_menu = TerminalMenu(commands, title="CRISPRDetect3 command:\n", 
                             menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                             menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                             clear_screen=True, raise_error_on_interrupt=True, preview_command=show_preview)
            try: menu_command_index = commands_menu.show()
            except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
            if menu_command_index is None: 
                print("No command selected, ", file=sys.stderr); exit()
            else:
                command=list(commands.values())[menu_command_index]

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
    logging.info("Input directory: " + input_dir)
    logging.info("Output directory: " + output_dir)
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
    errors = [] # used for catch subprocess errors
    output_files = [] # used for parsing
    with ThreadPoolExecutor(args.num_cpus) as executor:
        logging.info(f'RUNNING TOOL... ({"unzip +" if args.decompress else ""} subprocess.run + ThreadPoolExecutor version)')
        start_time = datetime.now()
        for mag in mags:
            output_file=os.path.join(output_dir, os.path.relpath(mag.rsplit('.', 2 if args.decompress else 1)[0]+"."+tool, input_dir))
            output_files.append(output_file)
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            future=executor.submit(unzip_and_run if args.decompress else run, command_run, mag, output_file)
            # if args.decompress:
                # future=executor.submit(unzip_and_run, command_run, mag, output_file)
                
            # else:
                # future=executor.submit(run, command_run, mag, output_file)
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

    # Parsing files
    tasks_total = len(output_files)  
    parsed_file = os.path.join(output_dir, os.path.basename(input_dir)+'_'+tool+'_parsed.tsv')

    logging.info('RUNNING PARSE...')
    start_time = datetime.now()


    # match tool:
    #     case "minced":
    #         crisprs_total = [crispr for file in output_files for crispr in parse_minced(file)]
    #     case "pilercr":
    #         crisprs_total = [crispr for file in output_files for crispr in parse_pilercr(file)]
    #     case "CRISPRDetect3":
    #         crisprs_total = [crispr for file in output_files for crispr in parse_CRISPRDetect3(file)]
    
    tasks_completed = 0
    crisprs_total = []
    match tool:
        case "minced":
            for file in output_files:
                crisprs_total+=parse_minced(file)
                tasks_completed+=1
                print(f' Parsed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)
        case "pilercr":
            for file in output_files:
                crisprs_total+=parse_pilercr(file)
                tasks_completed+=1
                print(f' Parsed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)
        case "CRISPRDetect3":
            pass

    crisprs_df = pd.DataFrame([[a.file_name, a.contig_name, a.start, a.end, ','.join(a.spacers), ','.join(a.repeats)] for a in crisprs_total],
                                columns=['MAG', 'Contig', 'Start', 'End', 'Spacers', 'Repeats'])

    crisprs_df.to_csv(parsed_file, sep='\t')

    end_time = datetime.now()
    logging.info('Parse {}/{} Files in {}'.format(
        tasks_completed,
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Done!')

