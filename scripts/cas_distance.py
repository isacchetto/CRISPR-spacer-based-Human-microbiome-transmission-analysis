#!/usr/bin/env python3

import os
import sys
import pandas as pd
from datetime import datetime
import argparse
import logging



# cas_distance.py
# Version 1.0
# 01/10/2024
# by isacchetto


# Argument parser
parser = argparse.ArgumentParser(description="Creates from an input tsv file with these columns: 'MAG', 'Contig', 'Start', 'End', 'Spacers', 'Repeats', a new tsv file adding the columns: 'Cas_0-1000', 'Cas_1000- 10000', 'Cas_>100000', 'Cas_overlayed' using a cas_database.tsv (created by CRISPCasFinder)")
parser.add_argument("input_file", type=str, help="The input file (file.tsv)")
parser.add_argument("-cas", "--cas_database", type=str, help="The file.tsv where are stored the cas genes ", default='samples/Aug19_cas_genes.tsv', dest="cas_database")
# parser.add_argument("-out", "--output", type=str, help="The output file, default is 'out/<input_file>_parsed_cas.tsv' (see --inplace for more info)", default=None, dest="out")
# parser.add_argument("-i", "--inplace", action="store_true", help="Created output file near the input file instead into the 'out' directory of the current working directory")
# parser.add_argument("-t", "--threads", type=int, help="Number of threads to use", default=mp.cpu_count()//3, dest="num_cpus")
parser.add_argument("-n", "--dry-run", action="store_true", help="Print information about what would be done without actually doing it")
args = parser.parse_args()

input_file = os.path.abspath(args.input_file)
cas_database = os.path.abspath(args.cas_database)
output_file = f"{input_file[:-4]}_cas.tsv"

# Check if input file exists or not
if not os.path.exists(input_file):
    print("The input file does not exist, check the path", file=sys.stderr)
    exit()

# Check if cas database file exists or not
if not os.path.exists(cas_database):
    print("The cas database file does not exist, check the path", file=sys.stderr)
    exit()

# Create output file
# if args.inplace:
#     if args.out==None:
#         # Create output file with unique name near the input file
#         output_file = f"{input_file[:-4]}_cas.tsv"
#     else:
#         # Create output file with name specified by the user near the input file
#         output_file = os.path.join(input_file.removesuffix(os.path.basename(input_file)), os.path.basename(args.out))
# else:
#     if args.out==None:
#         # Create output file with unique name in the out directory of the current working directory
#         output_file = os.path.join(os.getcwd(), "out", f"{os.path.basename(input_file)[:-4]}_cas.tsv")
#     else:
#         # Create output file with name specified by the user in the out directory of the current working directory
#         output_file = os.path.join(os.getcwd(), "out", os.path.basename(args.out))

# Check if output file exists and ask the user if they want to overwrite it
if os.path.exists(output_file) and not args.dry_run:
    print("The output file already exists, OVERWRITING IT? [y/N]", file=sys.stderr)
    overwrite = input()
    if overwrite.lower() != 'y':
        exit()
    else:
        os.remove(output_file)

if __name__ == '__main__':

    # Set up logging
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    logging.info("Input file: " + input_file)
    logging.info("Cas database file: " + cas_database)
    logging.info("Output file: " + output_file)
    if args.dry_run:
        logging.info('Dry run, exiting...')
        exit()

    logging.info('Running!')
    start_time = datetime.now()

    # Carica i file TSV
    try:
        CRISPR_df = pd.read_csv(os.path.abspath(args.input_file), delimiter='\t', usecols=['MAG', 'Contig', 'Start', 'End', 'Spacers', 'Repeats'], dtype={'MAG': str, 'Contig': str, 'Start': int, 'End': int}, index_col=False)
    except ValueError as e:
        print('Errore: ', e)
        print('Check the column names in the input file (MAG, Contig, Start, End, Spacers, Repeats), and secure that file is a TSV file')
        exit()
    try:
        Cas_df = pd.read_csv(os.path.abspath(args.cas_database), delimiter='\t', usecols=['MAG', 'Contig', 'Start', 'End'], dtype={'MAG': str, 'Contig': str, 'Start': int, 'End': int})
    except ValueError as e:
        print('Errore: ', e)
        print('Check the column names in the input file (MAG, Contig, Start, End), and secure that file is a TSV file')
        exit()

    # Creo un DataFrame con i dati dei CRISPR e dei Cas combinati
    merged_df = CRISPR_df.drop(columns=['Spacers', 'Repeats']).reset_index().merge(Cas_df, on=['MAG', 'Contig'], how="inner", suffixes=('_CRISPR', '_Cas')).set_index('index')

    # Aggiunge le colonne al DataFrame
    CRISPR_df['Cas_0-1000']=0
    CRISPR_df['Cas_1000-10000']=0
    CRISPR_df['Cas_>100000']=0
    CRISPR_df['Cas_overlayed']=0

    # Calcola la distanza tra i CRISPR e i Cas
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
            CRISPR_df.at[index, 'Cas_0-1000'] += 1
        elif distance > 1000 and distance <= 10000:
            CRISPR_df.at[index, 'Cas_1000-10000'] += 1
        elif distance > 10000:
            CRISPR_df.at[index, 'Cas_>100000'] += 1
        elif distance == -1:
            CRISPR_df.at[index, 'Cas_overlayed'] += 1
        else:
            print('Errore')
            print('Distanza: ', distance)

    # Salva il DataFrame in un file TSV
    CRISPR_df.to_csv(output_file, sep='\t')

    end_time = datetime.now()
    logging.info('Add Cas Distance in {}'.format(datetime.strftime(datetime.min + (end_time - start_time), '%Hh:%Mm:%S.%f')[:-3]+'s'))
    logging.info('Done!')