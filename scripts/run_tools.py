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
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
from threading import Lock
import tempfile
from simple_term_menu import TerminalMenu
import pandas as pd
# import CRISPRtools as ct



# run_tools.py
# Version 2.0
# 05/10/2024
# by isacchetto


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
    tool = command_run[0]
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
    tool = command_run[0]
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
        return f'<CRISPR object: (\n{self.file_name}\n{self.contig_name}\n{self.start}\n{self.end}\n{self.repeats}\n{self.spacers})>\n'
    
    def __str__(self):
        return f'f_name: {self.file_name}\ncontig: {self.contig_name}\nstart: {self.start}\nend: {self.end}\nrepeats: {self.repeats}\nspacers: {self.spacers}\n'
    
    def __len__(self):
        return sum(len(spacer) for spacer in self.spacers) + sum(len(repeat) for repeat in self.repeats)
    
    def __bool__(self):
        return (isinstance(self.file_name, str) and self.file_name != '' and
                isinstance(self.contig_name, str) and self.contig_name != '' and
                isinstance(self.start, int) and self.start > 0 and
                isinstance(self.end, int) and self.end >= self.start and
                len(self) == (self.end - self.start + 1) and 
                len(self.repeats) == len(self.spacers) + 1)
    
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
                    contig_name = None
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
            elif crispr_tmp is not None: # Check if the previous CRISPR array was finished
                raise ValueError(f"CRISPR not finished in file {gff_file_path}, contig {crispr_tmp.contig_name}")
            crispr_tmp = CRISPR(file_name=file_name, contig_name=row['seqid'], start=row['start'], end=row['end'])
            crispr_id = row['ID']
        elif row['type'] == 'direct_repeat' and row['Parent'] == crispr_id:  # Add a repeat
            crispr_tmp.addRepeat(row['Note'])
        elif row['type'] == 'binding_site' and row['Parent'] == crispr_id:  # Add a spacer
            crispr_tmp.addSpacer(row['Note'])
    # Add the last CRISPR array if one was being built
    if crispr_tmp:
        crisprs.append(crispr_tmp)
    else:
        raise ValueError(f"CRISPR not finished in file {gff_file_path}, contig {row['seqid']}")
    return crisprs


if __name__ == '__main__':

    # Argument parser
    parser = argparse.ArgumentParser(prog='run_tools', formatter_class=argparse.RawTextHelpFormatter, description=textwrap.dedent("""
                                    Run minced/pilercr/CRISPRDetect3 on a directory of MAGs,
                                    and create a file.tsv of CRISPRs found with this column:
                                    'MAG', 'Contig', 'Start', 'End', 'Spacers', 'Repeats', 'ToolCodename'
                                    ['Cas_0-1000', 'Cas_1000-10000', 'Cas_>100000', 'Cas_overlayed'] (if --cas_database is used)."""))
    parser.add_argument("input_directory", type=str, help="The input directory of the MAGs (in .fna or .bz2 format, see --decompress)")
    parser.add_argument("-d", "--decompress", action="store_true", help="Use this flag if the MAGs are compressed in .bz2 format (default: False)")
    parser.add_argument("-out", "--output-dir", type=str, help="The output directory, default is './out/<input_directory>_<tool>_<commandCodename>' \n(see --inplace for more info)", default=None, dest="output_directory", metavar='OUTPUT_DIR')
    parser.add_argument("-i", "--inplace", action="store_true", help="Created output directory near the input directory, \ninstead into the 'out' directory of the current working directory (default: False)")
    parser.add_argument("-cas", "--cas_database", type=str, help="The file.tsv where are stored the cas genes (created by CRISPCasFinder). \nBy adding this, the columns 'Cas_0-1000', 'Cas_1000-10000', 'Cas_>100000', 'Cas_overlayed' \nwill be added to the file.tsv", default=None, dest="cas_database", metavar='CAS_DB')
    parser.add_argument("-t", "--threads", type=int, help=f"Number of threads to use (default: ALL/3 = {mp.cpu_count()//3})", default=mp.cpu_count()//3, dest="num_cpus", metavar='N_CPUS')
    parser.add_argument("-n", "--dry-run", action="store_true", help="Print information about what would be done without actually doing it (default: False)")
    args = parser.parse_args()

    # Check if input directory exists or not
    if os.path.exists(args.input_directory):
        input_dir = os.path.abspath(args.input_directory)
    else:
        print("The input directory does not exist", file=sys.stderr)
        exit()
    
    # Check if cas database file exists or not
    if args.cas_database is not None:
        if os.path.exists(args.cas_database):
            cas_database = os.path.abspath(args.cas_database)
        else:
            print("The cas database file does not exist, check the path", file=sys.stderr)
            exit()
    
    # Verify the presence of the tools and create the commands
    commands = {}
    if shutil.which("minced"):
        # minced default parameters:
            # -searchWL 8 -minNR 3
            # -minRL 23 -maxRL 47
            # -minSL 26 -maxSL 50
        commands["minced_Default"]="minced -minNR 3 -minRL 23 -maxRL 47 -minSL 26 -maxSL 50" # Default command
        commands["minced_Paper"]="minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128" # Parameters on Paper PMCID: PMC10910872
    if shutil.which("pilercr"):
        # pilercr default parameters:
            # -minarray 3 -mincons 0.9 
            # -minrepeat 16 -maxrepeat 64 
            # -minspacer 8 -maxspacer 64 
            # -minrepeatratio 0.9 -minspacerratio 0.75 
            # -minhitlength 16 -minid 0.94
        commands["pilercr_PILER1"]="pilercr -noinfo -quiet" # Default command
        commands["pilercr_PILER2"]="pilercr -noinfo -quiet -minarray 3 -mincons 0.8 -minid 0.85 -maxrepeat 128 -maxspacer 128" # Parameters on Paper PMCID: PMC10910872
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
        commands["CRISPRDetect3"]=f"CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -q 1 -T {args.num_cpus} -left_flank_length 0 -right_flank_length 0"
    if not commands:
        print("No tools found: minced, pilercr, CRISPRDetect3", file=sys.stderr)
        exit()

    # Select the command to use
    commands_menu = TerminalMenu(commands, title="Select the command to use:  (Press Q or Esc to quit) \n",
                                menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                                menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                                clear_screen=False, raise_error_on_interrupt=True, preview_command=show_preview)
    try: menu_command_index = commands_menu.show()
    except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
    if menu_command_index is None: 
        print("No command selected", file=sys.stderr); exit()
    else:
        command = list(commands.values())[menu_command_index]
        tool_codename = list(commands.keys())[menu_command_index]

    # Split the command
    command_run=command.split()

    # Create output directory
    if args.inplace:
        if args.output_directory==None:
            # Create output directory with unique name near the input directory
            output_dir = f"{input_dir}_{tool_codename}"
        else:
            # Create output directory with name specified by the user near the input directory
            output_dir = os.path.join(input_dir.removesuffix(os.path.basename(input_dir)), os.path.basename(args.output_directory))
    else:
        if args.output_directory==None:
            # Create output directory with unique name in the out directory of the current working directory
            output_dir = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_dir)}_{tool_codename}")
        else:
            # Create output directory with name specified by the user in the out directory of the current working directory
            output_dir = os.path.join(os.getcwd(), "out", os.path.basename(args.output_directory))

    # Check if the output directory exists and ask the user if they want to rename it or overwrite it
    if os.path.exists(output_dir):
        outdir_menu = TerminalMenu(["Rename (Incremental)", "Overwrite", "Exit"], title=f"The output directory already exists. What do you want to do?", 
                                menu_cursor="> ", menu_cursor_style=("fg_red", "bold"), 
                                menu_highlight_style=("bg_red", "fg_yellow", "bold"), 
                                clear_screen=False, raise_error_on_interrupt=True)
        try: outdir_index = outdir_menu.show()
        except KeyboardInterrupt: print("Interrupted by the user", file=sys.stderr); exit()
        if outdir_index == 0:
            output_dir = output_dir + '_1'
            while os.path.exists(output_dir):
                output_dir = "_".join(output_dir.split('_')[:-1]) + '_' + str(int(output_dir.split('_')[-1]) + 1)
        elif outdir_index == 1:
            if not args.dry_run:
                shutil.rmtree(output_dir)
        else:
            exit()

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
    tool=tool_codename.split('_')
    logging.info("Tool: " + ' -> '.join(tool))
    tool=tool[0]
    match tool:
        case "minced":
            logging.info("Command: " + ' '.join(command_run + ['<mag>', '>', '<out.minced>']))
        case "pilercr":
            logging.info("Command: " + ' '.join(command_run + ['-in', '<mag>', '-out', '<out.pilercr>']))
        case "CRISPRDetect3":
            logging.info("Command: " + ' '.join(command_run + ['-f', '<mag>', '-o', '<out.CRISPRDetect3>']))
    logging.info("Input directory: " + input_dir)
    if args.cas_database is not None:
        logging.info("Cas database: " + cas_database)
    logging.info("Output directory: ./" + os.path.relpath(output_dir))
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
        logging.info(f'RUNNING {"UNZIP +" if args.decompress else ""} TOOL... ')
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
    logging.info('RUNNING PARSE...')
    start_time = datetime.now()

    tasks_total = len(output_files)  
    parsed_file = os.path.join(output_dir, os.path.basename(input_dir)+'_'+tool_codename+'_parsed.tsv')
    logging.info('Parsed file: ./' + os.path.relpath(parsed_file))

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
            for file in output_files:
                crisprs_total+=parse_CRISPRDetect3(file+'.gff')
                tasks_completed+=1
                print(f' Parsed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)


    crisprs_df = pd.DataFrame([[a.file_name, a.contig_name, a.start, a.end, ','.join(a.spacers), ','.join(a.repeats), tool_codename] for a in crisprs_total],
                                columns=['MAG', 'Contig', 'Start', 'End', 'Spacers', 'Repeats', 'ToolCodename'])

    crisprs_df.to_csv(parsed_file, sep='\t')

    end_time = datetime.now()
    logging.info('Parse {}/{} Files in {}'.format(
        tasks_completed,
        tasks_total, 
        datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))  
    logging.info('Found {} CRISPRs'.format(len(crisprs_total)))
    logging.info('Done!')

    # Add Cas Distance
    if args.cas_database is None:
        exit()
    
    logging.info('RUNNING CAS DISTANCE...')
    start_time = datetime.now()

    # Output file
    cas_file = os.path.join(output_dir, os.path.basename(input_dir)+'_'+tool_codename+'_parsed_cas.tsv')
    logging.info("Output cas file: ./" + os.path.relpath(cas_file))

    # Upload the TSV files
    try:
        cas_df = pd.read_csv(cas_database, delimiter='\t', usecols=['MAG', 'Contig', 'Start', 'End'], dtype={'MAG': str, 'Contig': str, 'Start': int, 'End': int})
    except ValueError as e:
        logging.error('Errore: ', e)
        logging.error('Check the column names in the input file (MAG, Contig, Start, End), and secure that file is a TSV file')
        logging.error('Done, without adding Cas Distance!')
        exit()

    # Create a DataFrame with the data of the CRISPR and Cas combined
    merged_df = crisprs_df.drop(columns=['Spacers', 'Repeats', 'ToolCodename']).reset_index().merge(cas_df, on=['MAG', 'Contig'], how="inner", suffixes=('_CRISPR', '_Cas')).set_index('index')

    # Add columns to the DataFrame
    crisprs_df['Cas_0-1000']=0
    crisprs_df['Cas_1000-10000']=0
    crisprs_df['Cas_>100000']=0
    crisprs_df['Cas_overlayed']=0

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
            crisprs_df.at[index, 'Cas_0-1000'] += 1
        elif distance > 1000 and distance <= 10000:
            crisprs_df.at[index, 'Cas_1000-10000'] += 1
        elif distance > 10000:
            crisprs_df.at[index, 'Cas_>100000'] += 1
        elif distance == -1:
            crisprs_df.at[index, 'Cas_overlayed'] += 1
        else:
            logging.error(f'Error: Distance of MAG: {row["MAG"]} and Contig: {row["Contig"]} is {distance}')

    # Save the DataFrame in a TSV file
    crisprs_df.to_csv(cas_file, sep='\t')

    end_time = datetime.now()
    logging.info('Add Cas Distance in {}'.format(datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))
    logging.info('Done!')
    
