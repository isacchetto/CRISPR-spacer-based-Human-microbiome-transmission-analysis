import os
import glob
import pandas as pd
import re

class CRISPR(object):
    def __init__(self, sequence, MAG):
        self.sequence = sequence.rstrip()
        self.repeats = []
        self.spacers = []
        self.mag = MAG
    def setPos(self, start, end):
        self.start = int(start.rstrip())
        self.end = int(end.rstrip())
    def addRepeat(self, repeat):
        self.repeats.append(repeat.rstrip())
    def addSpacer(self, spacer):
        put_spacer = spacer.rstrip()
        if len(put_spacer) > 0:
            self.spacers.append(put_spacer)

def parse_minced(path):
    file = open(path, 'r')

    crisprs = []
    for ll in file:
        # Record sequence accession
        if ll.startswith('Sequence'):
            sequence_current = re.sub('\' \(.*', '', re.sub('Sequence \'', '', ll))
        # Create instance of CRISPR and add positions
        if ll.startswith('CRISPR'):
            crisp_tmp = CRISPR(sequence_current, path.split('/')[-1].split('.')[0])
            pos = re.sub('.*Range: ', '', ll)
            start = re.sub(' - .*', '', pos)
            end = re.sub('.* - ', '', pos)
            crisp_tmp.setPos(start, end)
        # Add Repeats and Spacers to the current instance
        if ll[:1].isdigit():
            lll = ll.split()
            if len(lll) == 7:
                crisp_tmp.addRepeat(lll[1])
                crisp_tmp.addSpacer(lll[2])
            if len(lll) == 2:
                crisp_tmp.addRepeat(lll[1])
        # Save the instance
        if ll.startswith('Repeats'):
            crisprs.append(crisp_tmp)

    file.close()

    return crisprs

basedir = '/Users/isaccocenacchi/Desktop/Tirocinio/out/MAGs_short_minced'
outfile = f"{basedir}_parsed_matteo.tsv"
releases = ['Aug19']

for rel in releases:
    print('Processing {}...'.format(rel))
    rel_dfs = []
    for chunk in os.listdir(os.path.join(basedir, rel)):
        crispr_paths = glob.glob(os.path.join(basedir, rel, chunk, '*.crispr')) 
        chunk_arrays = [array for path in crispr_paths for array in parse_minced(path)]
        chunk_array_df = pd.DataFrame([[a.mag, a.sequence, a.start, a.end, ','.join(a.spacers), ','.join(a.repeats)] for a in chunk_arrays])
        if chunk_array_df.shape[1]==6:
            chunk_array_df.columns = ['MAG', 'contig', 'start', 'end', 'spacers', 'repeats']
            rel_dfs.append(chunk_array_df)
    rel_data = pd.concat(rel_dfs).reset_index(drop=True)
    rel_data.to_csv(outfile, sep='\t')