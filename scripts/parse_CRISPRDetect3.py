import pandas as pd

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
                isinstance(self.end, int) and self.end > self.start and
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
            if crispr_tmp is None: # First CRISPR array
                crispr_tmp = CRISPR(file_name=file_name, contig_name=row['seqid'], start=row['start'], end=row['end'])
                crispr_id = row['ID']
            else: # Save the previous CRISPR array
                if crispr_tmp:
                    crisprs.append(crispr_tmp)
                    crispr_tmp = None
                else:
                    raise ValueError(f"Invalid CRISPR format in file {gff_file_path}, contig {row['seqid']}")
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
    file = '/Users/isaccocenacchi/Desktop/Tirocinio/tests/M1023330751/prova.gff'
    crisprs = parse_CRISPRDetect3(file)