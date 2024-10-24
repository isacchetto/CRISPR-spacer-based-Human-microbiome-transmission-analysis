#!/usr/bin/env python3

import os
import sys
import shutil
import bz2
import subprocess
import textwrap
from datetime import datetime
import argparse
import logging
from logging import Handler
import requests
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp
from threading import Lock
import tempfile
from simple_term_menu import TerminalMenu
import pandas as pd
# import CRISPRtools as ct



# run_CRISPRtools.py
# Version 2.0
# 16/10/2024
# by isacchetto




TELEGRAM_BOT_TOKEN=os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID=os.environ.get('TELEGRAM_CHAT_ID')

# Class to send log messages to Telegram
class RequestsHandler(Handler):
	def emit(self, record):
		log_entry = self.format(record)
		payload = {
			'chat_id': TELEGRAM_CHAT_ID,
			'text': log_entry,
			'parse_mode': 'HTML'
		}
		return requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage', data=payload).content

# Function to rename a directory with an incremental number
def renamed_incremental(dir):
    i=1
    renamed_dir = f"{dir}_{i}"
    while os.path.exists(renamed_dir):
        i+=1
        renamed_dir = f"{dir}_{i}"
    return renamed_dir

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

# Function to unzip and run the tool
def unzip_and_run(command_run, input_file, output_file):
    global errors, lock_errors
    tool = command_run[0]
    with open(input_file, 'rb') as file, tempfile.NamedTemporaryFile("wb", suffix=f"_{os.path.basename(input_file)[:-8]}.fna", delete=True) as tmp_file:
        decompressor = bz2.BZ2Decompressor()
        for data in iter(lambda : file.read(100 * 1024), b''):
            tmp_file.write(decompressor.decompress(data))
        match tool:
            case "minced":
                completedProcess = subprocess.run(command_run + [tmp_file.name], 
                                                  stdout=open(output_file, 'wb'), 
                                                  stderr=subprocess.DEVNULL)
            case "pilercr":
                completedProcess = subprocess.run(command_run + ['-in', tmp_file.name, '-out', output_file], 
                                                  stdout=subprocess.DEVNULL, 
                                                  stderr=subprocess.DEVNULL)
            case "CRISPRDetect3" | "CRISPRDetect2.4":
                completedProcess = subprocess.run(command_run + ['-f', tmp_file.name, '-o', output_file], 
                                                  stdout = subprocess.DEVNULL, 
                                                  stderr=subprocess.DEVNULL)
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
    tool = command_run[0]
    match tool:
        case "minced":
            completedProcess = subprocess.run(command_run + [input_file], 
                                              stdout=open(output_file, 'wb'), 
                                              stderr=subprocess.DEVNULL)
        case "pilercr":
            completedProcess = subprocess.run(command_run + ['-in', input_file, '-out', output_file], 
                                              stdout=subprocess.DEVNULL, 
                                              stderr=subprocess.DEVNULL)
        case "CRISPRDetect3" | "CRISPRDetect2.4":
            completedProcess = subprocess.run(command_run + ['-f', input_file, '-o', output_file], 
                                              stdout = subprocess.DEVNULL, 
                                              stderr=subprocess.DEVNULL)
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}:  {tool} returned {e.returncode}")
        return 0
    else:
        return 1

class CRISPR:
    '''
    A class used to represent a CRISPR array

    Attributes:
        file_name (str): the name of the file that the CRISPR was found in (MAG name)
        contig_name (str): the name of the contig that the CRISPR was found in
        start (int): Position of the first base in the CRISPR (one-indexed, inclusive)
        end (int): position of the last base in the CRISPR (one-indexed, inclusive)
        repeats (list): a list of the ordered repeats in the CRISPR
        spacers (list): a list of the ordered spacers in the CRISPR
    
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
        sequence(): Returns the complete sequence of the CRISPR 
    '''
    def __init__(self, file_name=None, contig_name=None, start=None, end=None):
        self.file_name = file_name
        self.contig_name = contig_name
        self.start = start
        self.end = end
        self.repeats = []
        self.spacers = []
    
    def __repr__(self):
        return (f'<CRISPR object: (\n'
                f'{self.file_name}\n'
                f'{self.contig_name}\n'
                f'{self.start}\n'
                f'{self.end}\n'
                f'{self.repeats}\n'
                f'{self.spacers})>\n'
                )
    
    def __str__(self):
        return (f'f_name: {self.file_name}\n'
                f'contig: {self.contig_name}\n'
                f'start: {self.start}\n'
                f'end: {self.end}\n'
                f'repeats: {self.repeats}\n'
                f'spacers: {self.spacers}\n'
                )
    
    def __len__(self):
        return sum(len(spacer) for spacer in self.spacers) + sum(len(repeat) for repeat in self.repeats)
    
    def __bool__(self):
        return (isinstance(self.file_name, str) and self.file_name != '' and
                isinstance(self.contig_name, str) and self.contig_name != '' and
                isinstance(self.start, int) and self.start > 0 and
                isinstance(self.end, int) and self.end >= self.start and
                len(self) == (self.end - self.start + 1) and 
                len(self.repeats) == len(self.spacers) + 1 and
                all(self.repeats) and all(self.spacers)
                )
    
    def __eq__(self, other):
        return (self.file_name == other.file_name and 
                self.contig_name == other.contig_name and 
                self.start == other.start and 
                self.end == other.end)
    
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
    
    def sequence(self):
        return ''.join([sub[item] for item in range(min(len(self.repeats), len(self.spacers)))
                             for sub in [self.repeats, self.spacers]] +
                   self.repeats[len(self.spacers):] + self.spacers[len(self.repeats):])
        

def parse_minced(file_path):
    crisprs = []
    crispr_tmp = None
    file_name = file_path.split('/')[-1].split('.')[0]
    contig_name = None
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("Sequence '"):
                contig_name = line.split("'")[1]
            elif line.startswith("CRISPR"):
                if crispr_tmp is not None:
                    raise ValueError(f"CRISPR not finished in file {file_path}, contig {crispr_tmp.contig_name}")
                else:
                    start, end = map(int, line.split()[3:6:2]) # Take from 4th to 6th element, step 2
                    crispr_tmp = CRISPR(file_name=file_name, contig_name=contig_name, start=start, end=end)
            elif line[:1].isdigit():
                seqs = line.split()
                if len(seqs) == 7:
                    crispr_tmp.addRepeat(seqs[1])
                    crispr_tmp.addSpacer(seqs[2])
                if len(seqs) == 2:
                    crispr_tmp.addRepeat(seqs[1])
            # Save the instance
            elif line.startswith("Repeats"):
                if crispr_tmp:
                    crisprs.append(crispr_tmp)
                    crispr_tmp = None
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
    crispr_tmp = None
    file_name = file_path.split('/')[-1].split('.')[0]
    contig_name = None
    repeats = []
    with open(file_path, 'r') as file:
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
                    start=int(seqs[0])# + seqs[5][:seqs[5].find(".")].count("-") # adjust start position if there are gaps at the beginning of the first repeat (already works well, I was confused)
                    crispr_tmp = CRISPR(file_name=file_path.split('/')[-1].split('.')[0], contig_name=contig_name, start=start, end=None)
                    contig_name = None
                    repeats.append(seqs[5])
                    crispr_tmp.addSpacer(seqs[6])
                elif len(seqs) == 6 and crispr_tmp is None: # first line: repeat - spacer (CRISPR start at beginning of contig)
                    start=int(seqs[0]) 
                    crispr_tmp = CRISPR(file_name=file_path.split('/')[-1].split('.')[0], contig_name=contig_name, start=start, end=None)
                    contig_name = None
                    repeats.append(seqs[4])
                    crispr_tmp.addSpacer(seqs[5])
                elif len(seqs) == 7 and crispr_tmp is not None: # next line: repeat - spacer
                    repeats.append(seqs[5])
                    crispr_tmp.addSpacer(seqs[6])
                elif len(seqs) == 6 and crispr_tmp is not None: # last line: repeat - flankerRight
                    repeats.append(seqs[4])
                elif len(seqs) == 5 and crispr_tmp is not None: # last line: repeat (CRISPR end at end of contig)
                    repeats.append(seqs[4])
                elif len(seqs) == 4 and crispr_tmp is not None: # reference repeat
                    reference = seqs[3]
                    for repeat in develop_repeats(repeats, reference):
                        crispr_tmp.addRepeat(repeat)
                    repeats = []
                    crispr_tmp.setEnd(crispr_tmp.start + len(crispr_tmp) - 1)
                    if crispr_tmp:
                        crisprs.append(crispr_tmp)
                        crispr_tmp = None
                    else:
                        raise ValueError(f"Invalid CRISPR format in file {file_path}")
            elif line.startswith("SUMMARY"):
                if crispr_tmp is not None:
                    raise ValueError(f"CRISPR not finished in file {file_path}, contig {crispr_tmp.contig_name}")
                break
        return crisprs

# Function to separate the attributes and convert them into a dictionary
def parse_attributes(attr_string):
    attr_dict = {}
    attributes = attr_string.split(';')
    for attribute in attributes:
        if '=' in attribute:
            key, value = attribute.split('=')
            key = key.strip()
            value = value.strip()
            attr_dict[key] = value
    return attr_dict

# Function to extract CRISPR information from a GFF file generated by CRISPRDetect3 and return a list of CRISPR objects
def parse_CRISPRDetect3(gff_file_path):
    # Check if the GFF file is empty
    if os.path.getsize(gff_file_path) == 0:
        return []
    
    # Reading the GFF file
    try:
        gff_df = pd.read_csv(gff_file_path, sep='\t', comment='#', header=None, 
                         names=['seqid', 'source', 'type', 'start', 'end', 'score', 'strand', 'phase', 'attributes'])
    except Exception as e:
        raise ValueError(f"Error reading GFF file {gff_file_path}: {str(e)}")
    # Apply the parsing function to the 'attributes' column
    attributes_df = gff_df['attributes'].apply(parse_attributes).apply(pd.Series)
    # Merge the parsed attributes to the original DataFrame and drop the original 'attributes' column
    gff_df = pd.concat([gff_df.drop(columns=['attributes']), attributes_df], axis=1)
    crisprs = []
    crispr_tmp = None
    file_name = gff_file_path.split('/')[-1].split('.')[0]
    for _, row in gff_df.iterrows():
        if row['type'] == 'repeat_region':  # Start a new CRISPR array
            if crispr_tmp: # Save the previous CRISPR array
                crisprs.append(crispr_tmp)
            elif crispr_tmp is not None:
                raise ValueError(f"Invalid CRISPR format in file {gff_file_path}, contig {crispr_tmp.contig_name}")
            crispr_tmp = CRISPR(file_name=file_name, contig_name=row['seqid'], start=row['start'], end=None)
            crispr_id = row['ID']
        elif row['type'] == 'direct_repeat' and row['Parent'] == crispr_id:  # Add a repeat
            if row['Note'] == '':
                raise ValueError(f"Empty repeat in file {gff_file_path}, contig {row['seqid']}")
            crispr_tmp.addRepeat(row['Note'])
            crispr_tmp.setEnd(crispr_tmp.start + len(crispr_tmp) - 1)
            # if row['end'] != crispr_tmp.end:
                # raise ValueError(f"CRISPR length mismatch in file {gff_file_path}, contig {crispr_tmp.contig_name}")
        elif row['type'] == 'binding_site' and row['Parent'] == crispr_id:  # Add a spacer
            crispr_tmp.addSpacer(row['Note'])
    # Add the last CRISPR array if one was being built
    if crispr_tmp:
        crisprs.append(crispr_tmp)
    else:
        raise ValueError(f"CRISPR not finished at the end of file {gff_file_path}, contig {row['seqid']}")
    return crisprs

# Function to assign unique IDs and check for overlaps
def assign_id_and_merge_overlaps(df):
    df = df.sort_values(by=['MAG', 'Contig', 'Start']).reset_index(drop=True)
    df['ID'] = None
    current_id = 1
    
    for i in range(len(df)):
        if df.loc[i, 'ID'] is None:
            # Assign a new ID
            df.loc[i, 'ID'] = current_id
            current_id += 1
        
        # Check for overlaps with subsequent rows with the same 'MAG' and 'Contig'
        for j in range(i + 1, len(df)):
            if df.loc[i, 'MAG'] == df.loc[j, 'MAG'] and df.loc[i, 'Contig'] == df.loc[j, 'Contig']:
                # Check for overlap of intervals
                if df.loc[i, 'Start'] <= df.loc[j, 'End'] and df.loc[j, 'Start'] <= df.loc[i, 'End']:
                    # Assign the same ID to the overlapping row
                    df.loc[j, 'ID'] = df.loc[i, 'ID']
            else:
                # If 'MAG' or 'Contig' are different, break the loop
                break
    return df

if __name__ == '__main__':

    # Argument parser
    parser = argparse.ArgumentParser(prog='CRISPRtools', 
                                     formatter_class=argparse.RawTextHelpFormatter, 
                                     description=textwrap.dedent("""
                                                                 Run minced/pilercr/CRISPRDetect on a directory of MAGs,
                                                                 and create a file.tsv of CRISPRs found with this column:
                                                                 'MAG', 'Contig', 'Start', 'End', 'Spacers', 'Repeats', 'ToolCodename'
                                                                 ['Cas_0-1000', 'Cas_1000-10000', 'Cas_>100000', 'Cas_overlayed'] (if --cas_database is used).
                                                                 """)
                                    )
    parser.add_argument("input_directory", type=str, 
                        help="The input directory of the MAGs (in .fna or .bz2 format, see --decompress)")
    parser.add_argument("-d", "--decompress", action="store_true", 
                        help="Use this flag if the MAGs are compressed in .bz2 format (default: False)")
    parser.add_argument("-out", "--output-dir", type=str, 
                        help="The output directory, default is './out/<input_directory>_CRISPRtools' \n(see --inplace for more info)", 
                        default=None, dest="output_directory", metavar='OUTPUT_DIR')
    parser.add_argument("-i", "--inplace", action="store_true", 
                        help="Created output directory near the input directory, \ninstead into the 'out' directory of the current working directory (default: False)")
    parser.add_argument("-cas", "--cas_database", type=str, 
                        help="The file.tsv where are stored the cas genes (created by CRISPCasFinder). \nBy adding this, the columns 'Cas_0-1000', 'Cas_1000-10000', 'Cas_>100000', 'Cas_overlayed' \nwill be added to the file.tsv", 
                        default=None, dest="cas_database", metavar='CAS_DB')
    parser.add_argument("-t", "--threads", type=int, 
                        help=f"Number of threads to use (default: ALL/3 = {mp.cpu_count()//4})", 
                        default=mp.cpu_count()//4, dest="num_cpus", metavar='N_CPUS')
    parser.add_argument("-n", "--dry-run", action="store_true", 
                        help="Print information about what would be done without actually doing it (default: False)")
    args = parser.parse_args()
    
    # Verify the presence of the tools and create the commands
    commands = {}
    if shutil.which("minced"):
        # minced default parameters:
            # -searchWL 8 -minNR 3
            # -minRL 23 -maxRL 47
            # -minSL 26 -maxSL 50
        commands["minced_Default"]="minced -minNR 3 -minRL 23 -maxRL 47 -minSL 26 -maxSL 50" # Default command
        commands["minced_Relaxed"]="minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128" # Parameters on Paper PMCID: PMC10910872
    if shutil.which("pilercr"):
        # pilercr default parameters:
            # -minarray 3 -mincons 0.9 
            # -minrepeat 16 -maxrepeat 64 
            # -minspacer 8 -maxspacer 64 
            # -minrepeatratio 0.9 -minspacerratio 0.75 
            # -minhitlength 16 -minid 0.94
        commands["pilercr_Default"]="pilercr -noinfo -quiet" # Default command
        commands["pilercr_Relaxed"]="pilercr -noinfo -quiet -minarray 3 -mincons 0.8 -minid 0.85 -maxrepeat 128 -maxspacer 128" # Parameters on Paper PMCID: PMC10910872
    if shutil.which("CRISPRDetect3"):
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
        commands["CRISPRDetect3_nocpu"]=f"CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -left_flank_length 0 -right_flank_length 0"
        # ne torva di piu, e ci mette di piu:
        commands["CRISPRDetect3_cpu"]=f"CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -T 4 -left_flank_length 0 -right_flank_length 0"
        # ne torva di meno e ci mette simile a default:
        # commands["CRISPRDetect3_nocpu"]=f"CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -left_flank_length 0 -right_flank_length 0"
        # commands["CRISPRDetect3_online"]=f"CRISPRDetect3 -array_quality_score_cutoff 2.5 -check_direction 0 -q 1 -T 0 -left_flank_length 0 -right_flank_length 0 -repeat_length_cutoff 11"
    # if shutil.which("CRISPRDetect2.4"):
    #     commands["CRISPRDetect2"]=f"CRISPRDetect2.4 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -T {args.num_cpus} -left_flank_length 0 -right_flank_length 0"
    #     commands["CRISPRDetect2_cpu"]=f"CRISPRDetect2.4 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -T 0 -left_flank_length 0 -right_flank_length 0"
    #     commands["CRISPRDetect2_nocpu"]=f"CRISPRDetect2.4 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -left_flank_length 0 -right_flank_length 0"
    if not commands:
        print("No tools found: minced, pilercr, CRISPRDetect. Exiting...", file=sys.stderr)
        exit()

    # Check if input directory exists or not
    if os.path.exists(args.input_directory):
        input_dir = os.path.abspath(args.input_directory)
    else:
        print("The input directory does not exist! Exiting...", file=sys.stderr)
        exit()

    # Create output root directory
    if args.inplace:
        if args.output_directory==None:
            # Create output root directory with unique name near the input directory
            output_root_dir = f"{input_dir}_CRISPRtools"
        else:
            # Create output root directory with name specified by the user near the input directory
            output_root_dir = os.path.join(input_dir.removesuffix(os.path.basename(input_dir)), os.path.basename(args.output_directory))
    else:
        if args.output_directory==None:
            # Create output root directory with unique name in the out directory of the current working directory
            output_root_dir = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_dir)}_CRISPRtools")
        else:
            # Create output root directory with name specified by the user in the out directory of the current working directory
            output_root_dir = os.path.join(os.getcwd(), "out", os.path.basename(args.output_directory))

    # Check if cas database file exists or not
    if args.cas_database is not None:
        if os.path.exists(args.cas_database):
            cas_database = os.path.abspath(args.cas_database)
        else:
            print("The cas database file does not exist, check the path! Exiting...", file=sys.stderr)
            exit()
        
        # Create the output file for the cas distance
        cas_output_file = os.path.join(output_root_dir, f"{os.path.basename(cas_database).rsplit('.', 1)[0]}_CRISPRtools.tsv")

        # Upload the TSV files
        if os.path.exists(cas_output_file): # Update the file already created
            try:
                cas_df = pd.read_csv(cas_output_file, sep='\t')
            except ValueError as e:
                print('Error in cas database file: ', e, file=sys.stderr)
                print('Exiting...', file=sys.stderr)
                exit()
            cas_database = cas_output_file
        else: # Operate on the file for the first time
            try:
                cas_df = pd.read_csv(cas_database, sep='\t')
            except ValueError as e:
                print('Error in cas database file: ', e, file=sys.stderr)
                print('Exiting...', file=sys.stderr)
                exit()

    # select multi command to use
    commands_menu = TerminalMenu(commands, title="Select the command to use:  (Press Q or Esc to quit)", 
                                 menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                                 menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                                 clear_screen=False, raise_error_on_interrupt=True, 
                                 preview_command=lambda command: commands[command], 
                                 preview_title="Command Preview", multi_select=True, 
                                 show_multi_select_hint=True, multi_select_cursor_style=("fg_red", "bold"), 
                                 multi_select_empty_ok=False, multi_select_select_on_accept=False)
    try: commands_menu.show()
    except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
    if commands_menu.chosen_menu_indices is None:
        print("No command selected, exiting...", file=sys.stderr); exit()
    else:
        commands={list(commands.keys())[i]: list(commands.values())[i] for i in commands_menu.chosen_menu_indices}

    # Create output directories
    output_dirs = {}
    for tool_codename in list(commands.keys()):
        output_dir = os.path.join(output_root_dir, f"{os.path.basename(input_dir)}_{tool_codename}")
        # Check if the output directory exists and ask the user if they want to rename it or overwrite it or skip
        if os.path.exists(output_dir):
            outdir_menu = TerminalMenu(["Rename (Incremental)", "Overwrite", "Not run this command", "Exit"],
                                        title=f"The output directory ./{os.path.relpath(output_dir)} already exists. What do you want to do?", 
                                        menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                                        menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                                        clear_screen=False, raise_error_on_interrupt=True)
            try: outdir_menu.show()
            except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
            if outdir_menu.chosen_menu_index is None:
                print("No option selected, exiting...", file=sys.stderr); exit()
            elif outdir_menu.chosen_menu_index == 0:
                output_dir = renamed_incremental(output_dir)
            elif outdir_menu.chosen_menu_index == 1:
                if not args.dry_run:
                    shutil.rmtree(output_dir)
            elif outdir_menu.chosen_menu_index == 2:
                commands.pop(tool_codename)
                continue
            else:
                print("Exiting...", file=sys.stderr); exit()
        output_dirs[tool_codename] = output_dir

    # Set up logging
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    logger=logging.getLogger(__name__)
    if not args.dry_run:
        os.makedirs(output_root_dir, exist_ok=True)
        log_handler=logging.FileHandler(os.path.join(output_root_dir, f'run_CRISPRtools.log'))
        log_handler.setLevel('INFO')
        log_formatter=logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)
        if TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN:
            telegram_handler = RequestsHandler()
            telegram_handler.setLevel('CRITICAL')
            telegram_handler.setFormatter(log_formatter)
            logger.addHandler(telegram_handler)

    # Find all MAGs in the input directory (and unzip them if needed)
    if args.decompress:
        files = [os.path.join(dirpath,filename)
                for dirpath, _, filenames in os.walk(input_dir)
                for filename in filenames
                if filename.endswith('.bz2')
            ]
        tasks_total = len(files)
        if not args.dry_run:
            # Unzip mag files (if needed)
            # ThreadPoolExecutor + unzip1 version
            tasks_completed = 0
            lock_tasks = Lock()
            unzip_dir = os.path.join(output_root_dir, f"{os.path.basename(input_dir)}_unzipped")
            with ThreadPoolExecutor(args.num_cpus) as executor:
                logger.info('UNZIPPING FILES... ')
                start_time = datetime.now()
                for file in files:
                    unzipped_file=os.path.join(unzip_dir, os.path.relpath(file.rsplit('.', 1)[0], input_dir))
                    os.makedirs(os.path.dirname(unzipped_file), exist_ok=True)
                    if os.path.exists(unzipped_file):
                        tasks_completed += 1
                    else:
                        future=executor.submit(unzip1, file, unzipped_file)
                        future.add_done_callback(future_progress_indicator)
            end_time = datetime.now()
            logger.info(f'  Unzipped {tasks_completed}/{tasks_total} files in {datetime.strftime(
                datetime.min + (end_time - start_time), "%Hh:%Mm:%S.%f")[:-3]}s')
            if tasks_completed < tasks_total:
                logger.critical(f'Unzipping done with errors ({tasks_completed}/{tasks_total} unzipped)!\n')
            else:
                logger.info('  Unzipping done!\n')
            mags = [os.path.join(dirpath,filename) 
                    for dirpath, _, filenames in os.walk(unzip_dir) 
                    for filename in filenames 
                    if filename.endswith('.fna')
                ]
            tasks_total = len(mags)
    else:
        mags = [os.path.join(dirpath,filename) 
                    for dirpath, _, filenames in os.walk(input_dir) 
                    for filename in filenames 
                    if filename.endswith('.fna')
                ]
        tasks_total = len(mags)

    if tasks_total == 0 and not args.dry_run:
        logger.critical('No MAGs found in the input directory! Exiting...')
        exit()

    first=True
    i=len(commands)
    for tool_codename, command in commands.items():
        i-=1

        # Get the output directory
        output_dir = output_dirs[tool_codename]
        # Split the command
        command_run=command.split()

        # Create .log file for every tool 
        if not args.dry_run:
            os.makedirs(output_dir, exist_ok=True)
            log_handler_tool=logging.FileHandler(os.path.join(output_dir, f'run_{tool_codename}.log'))
            log_handler_tool.setLevel('INFO')
            log_handler_tool.setFormatter(log_formatter)
            logger.addHandler(log_handler_tool)
        
        tool=tool_codename.split('_')
        logger.info(f"TOOL: {' -> '.join(tool)}")
        tool = tool[0]
        match tool:
            case "minced":
                logger.info(f"  Command: {' '.join(command_run + ['<mag>', '>', '<out.minced>'])}")
            case "pilercr":
                logger.info(f"  Command: {' '.join(command_run + ['-in', '<mag>', '-out', '<out.pilercr>'])}")
            case "CRISPRDetect3" | "CRISPRDetect2":
                logger.info(f"  Command: {' '.join(command_run + ['-f', '<mag>', '-o', '<out.CRISPRDetect3>' 
                                                                if tool == 'CRISPRDetect3' else '<out.CRISPRDetect2>'])}")
            
        logger.info(f"  Input directory: {input_dir}")
        if args.cas_database is not None:
            logger.info(f"  Cas database: {cas_database}")
        logger.info(f"  Output directory: ./{os.path.relpath(output_dir)}")
        logger.info(f"  Found {tasks_total} MAGs")
        logger.info(f"  Using {args.num_cpus} threads{'\n' if args.dry_run else ''}")
        if args.dry_run:
            if i == 0:
                logger.info('Dry run completed, no files were created. Exiting...'); exit()
            continue

        # ThreadPoolExecutor + subprocess.run  version
        lock_tasks = Lock()
        lock_errors = Lock()
        tasks_completed = 0
        errors = [] # used for catch subprocess errors
        output_files = [] # used for parsing
        rel_path = unzip_dir if args.decompress else input_dir
        with ThreadPoolExecutor(args.num_cpus) as executor:
            logger.info(f'RUNNING TOOL... ')
            start_time = datetime.now()
            for mag in mags:
                output_file = os.path.join(output_dir, os.path.relpath(f"{mag.rsplit('.', 1)[0]}.{tool}", rel_path))
                output_files.append(output_file)
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                future=executor.submit(run, command_run, mag, output_file)
                future.add_done_callback(future_progress_indicator)
        end_time = datetime.now()
        logger.info(f'  Runned {tasks_completed}/{tasks_total} MAGs in {datetime.strftime(
            datetime.min + (end_time - start_time), "%Hh:%Mm:%S.%f")[:-3]}s')
        if errors:
            [logger.error(error) for error in errors]
            logger.critical(f'Running done with {len(errors)} errors!')
        else:
            logger.info('  Running done!')

        # Parsing files
        logger.info('PARSING FILES...')
        start_time = datetime.now()

        tasks_total = len(output_files)  
        parsed_file = os.path.join(output_dir, f"{os.path.basename(input_dir)}_{tool_codename}_parsed.tsv")
        logger.info(f'  Parsed file: ./{os.path.relpath(parsed_file)}')

        # match tool:
        #     case "minced":
        #         crisprs_total = [crispr for file in output_files for crispr in parse_minced(file)]
        #     case "pilercr":
        #         crisprs_total = [crispr for file in output_files for crispr in parse_pilercr(file)]
        #     case "CRISPRDetect3":
        #         crisprs_total = [crispr for file in output_files for crispr in parse_CRISPRDetect3(file)]
        tasks_completed = 0
        crisprs_total = []
        errors = []
        match tool:
            case "minced":
                for file in output_files:
                    try:
                        crisprs_total+=parse_minced(file)
                    except Exception as e:
                        errors.append(f'Error parsing: {e}')
                    tasks_completed+=1
                    print(f' Parsed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)
            case "pilercr":
                for file in output_files:
                    try:
                        crisprs_total+=parse_pilercr(file)
                    except Exception as e:
                        errors.append(f'Error parsing: {e}')
                    tasks_completed+=1
                    print(f' Parsed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)
            case "CRISPRDetect3" | "CRISPRDetect2":
                for file in output_files:
                    try:
                        crisprs_total+=parse_CRISPRDetect3(f"{file}.gff")
                    except Exception as e:
                        errors.append(f'Error parsing: {e}')
                    tasks_completed+=1
                    print(f' Parsed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)


        crisprs_df = pd.DataFrame(
            [[a.file_name, a.contig_name, a.start, a.end, ','.join(a.repeats), ','.join(a.spacers), tool_codename] for a in crisprs_total],
            columns=['MAG', 'Contig', 'Start', 'End', 'Repeats', 'Spacers', 'ToolCodename']
            )

        crisprs_df.to_csv(parsed_file, sep='\t')

        end_time = datetime.now()
        logger.info(f'  Parsed {tasks_completed}/{tasks_total} Files in {datetime.strftime(
            datetime.min + (end_time - start_time), "%Hh:%Mm:%S.%f")[:-3]}s')
        logger.info(f'  Found {len(crisprs_total)} CRISPRs')
        if errors:
            [logger.error(error) for error in errors]
            logger.critical(f'Parsing done with {len(errors)} errors!{"" if args.cas_database else os.linesep}')
        else:
            logger.info(f'  Parsing done!{"" if args.cas_database else os.linesep}')

        # Add Cas Distance
        if args.cas_database:
            logger.info('ADDING CAS DISTANCE...')
            start_time = datetime.now()
            # Output file
            logger.info(f'  Add Cas Distance to ./{os.path.relpath(parsed_file)}')
            logger.info(f'  Cas database updated: ./{os.path.relpath(cas_output_file)}')

            # Save a column with the indices to make the merge
            crisprs_df['index'] = crisprs_df.index
            cas_df['index'] = cas_df.index

            # Create a DataFrame with the data of the CRISPR and Cas combined
            try:
                merged_df = crisprs_df.merge(cas_df, on=['MAG', 'Contig'], how="inner", suffixes=('_CRISPR', '_Cas'))
            except Exception as e:
                logger.critical(f"Error merging the DataFrames: {e}")
                logger.critical(f'Adding Cas distance NOT DONE!\n')
                continue

            # Add columns to the DataFrame
            crisprs_df['Cas_0-1000']=0
            crisprs_df['Cas_1000-10000']=0
            # crisprs_df['Cas_0-10000']=0
            crisprs_df['Cas_>100000']=0
            crisprs_df['Cas_overlayed']=0

            # Add columns to cas_df to count the number of single spacers are near to a Cas for each Tool
            cas_df[tool_codename] = 0

            errors = []
            # Calculate the distance between CRISPR and Cas
            for index, row in merged_df.iterrows():
                if row['Start_Cas'] >= row['End_CRISPR']:
                    # print('Cas davati al CRISPR')
                    distance = row['Start_Cas'] - row['End_CRISPR']
                elif row['End_Cas'] <= row['Start_CRISPR']:
                    # print('Cas prima il CRISPR')
                    distance = row['Start_CRISPR'] - row['End_Cas']
                else:
                    # print('Cas che sovrappone al CRISPR')
                    distance = -1
                
                if distance >= 0 and distance <= 1000:
                    crisprs_df.at[row['index_CRISPR'], 'Cas_0-1000'] += 1
                    cas_df.at[row['index_Cas'], tool_codename] += len(row['Spacers'].split(','))
                elif distance > 1000 and distance <= 10000:
                    crisprs_df.at[row['index_CRISPR'], 'Cas_1000-10000'] += 1
                    # cas_df.at[row['index_Cas'], "minced_Paper"] += 1
                    cas_df.at[row['index_Cas'], tool_codename] += len(row['Spacers'].split(','))
                # if distance >= 0 and distance <= 10000:
                #     crisprs_df.at[row['index_CRISPR'], 'Cas_0-10000'] += 1
                #     cas_df.at[row['index_Cas'], "Minced_Default"] += 1
                elif distance > 10000:
                    crisprs_df.at[row['index_CRISPR'], 'Cas_>100000'] += 1
                elif distance == -1:
                    crisprs_df.at[row['index_CRISPR'], 'Cas_overlayed'] += 1
                else:
                    errors.append(f'Error: Distance of MAG: {row["MAG"]} and Contig: {row["Contig"]} is {distance}')

            # Remove the index columns
            crisprs_df = crisprs_df.drop(columns=['index'])
            cas_df = cas_df.drop(columns=['index'])

            # Save the DataFrame in a TSV file
            crisprs_df.to_csv(parsed_file, sep='\t')
            cas_df.to_csv(cas_output_file, sep='\t')

            end_time = datetime.now()
            logger.info(f'  Added Cas Distance in {datetime.strftime(datetime.min + (end_time - start_time), "%Hh:%Mm:%S.%f")[:-3]}s')
            if errors:
                [logger.error(error) for error in errors]
                logger.critical(f'Adding Cas distance done with {len(errors)} errors!\n')
            else:
                logger.info('  Adding Cas distance done!\n')

        logger.removeHandler(log_handler_tool)
        

    # Tool comparison
    logger.info('RUNNING TOOL COMPARISON...')

    parsed_files = [os.path.join(dirpath,filename)
                for dirpath, _, filenames in os.walk(output_root_dir)
                for filename in filenames
                if filename.endswith('_parsed.tsv')
            ]
    
    if len(parsed_files) < 2:
        logger.error('No files to compare')
        telegram_handler.setLevel('INFO')
        logger.info('DONE without comparison!\n\n')
        exit()

    comparison_file = os.path.join(output_root_dir, f"{os.path.basename(input_dir)}_tools_comparison.tsv")
    logger.info(f'  Found {len(parsed_files)} files to compare')
    logger.info(f'  Comparison file: ./{os.path.relpath(comparison_file)}')
    start_time = datetime.now()
    parsed_dfs = []

    columns={'MAG': str, 'Contig': str, 'Start': int, 'End': int, 'Repeats': str, 'Spacers': str, 'ToolCodename': str}
    if args.cas_database:
        columns.update({'Cas_0-1000': int, 'Cas_1000-10000': int, 'Cas_>100000': int, 'Cas_overlayed': int})
    


    # Upload the TSV files
    for file in parsed_files:
        try:
            parsed_dfs.append(pd.read_csv(file, delimiter='\t',
                                          usecols=list(columns.keys()),
                                          dtype=columns,
                                          index_col=False))
        except FileNotFoundError as e:
            logger.error(f"The parsing file '{file}' does not exist, there was a problem with the parsing")
            continue
        except ValueError as e:
            logger.error(f'Check the column names in the parsed file {file}: {e}')
            continue

    if not parsed_dfs and len(parsed_dfs) < 2:
        logger.error('No files to compare')
        telegram_handler.setLevel('INFO')
        logger.info('DONE without comparison!\n\n')
        exit()

    # Concat the DataFrames
    all_df = pd.concat([parsed_df for parsed_df in parsed_dfs], ignore_index=True)

    columns_groupby = list(columns.keys())
    columns_groupby.remove('ToolCodename')

    # Remove duplicates based on all columns and keep one row, concatening 'ToolCodename' values
    combined_df = all_df.groupby(columns_groupby, as_index=False).agg({'ToolCodename': lambda x: ','.join(sorted(set(x)))}) 
                                                                # Use set to remove duplicates and sorted for consistent order 

    # Apply the function to assign IDs and check for overlaps
    final_df = assign_id_and_merge_overlaps(combined_df)

    # Save the final DataFrame to a TSV file
    final_df.to_csv(comparison_file, sep='\t')

    end_time = datetime.now()
    logger.info(f'  Tool comparison in {datetime.strftime(datetime.min + (end_time - start_time), "%Hh:%Mm:%S.%f")[:-3]}s')
    telegram_handler.setLevel('INFO')
    logger.info('DONE!\n\n')


