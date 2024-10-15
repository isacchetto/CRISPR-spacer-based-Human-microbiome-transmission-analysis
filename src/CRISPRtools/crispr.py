
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
    