import argparse
import os
import sys
import subprocess
import multiprocessing
import uuid
import time
import textwrap

try:
    import pandas as pd
except:
    print("Pandas module is not installed! Please install Pandas and try again.")
    sys.exit()

try:
    import tqdm
except:
    print("tqdm module is not installed! Please install tqdm and try again.")
    sys.exit()

parser = argparse.ArgumentParser(prog='python CRISPRtoolcomp.py',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=textwrap.dedent('''\

# CRISPRtoolcomp

Author: Murat Buyukyoruk

        CRISPRtoolcomp help:

This script is developed to compare CRISPR hits coming from different detection software (i.e., CRISPRDetect, CRISPRClassify, CRISPRCASFinder, etc). 

Syntax:

        python CRISPRtoolcomp.py -i demo_CRISPR_list.txt

### Input file example:

Example Dataframe for the demo_CRISPR_list.txt file (tab separated excel file is required):

    Accession   Start   Stop    Tool
    NC_000853.1	412     3106	CRISPRDetect
    NC_000853.1	369170	369732	CRISPRDetect
    NC_000853.1	396568	397134	CRISPRDetect
    NC_000853.1	409295	410924	CRISPRDetect
    NC_000853.1	1519912	1520476	CRISPRDetect
    NC_000853.1	1631789	1632017	CRISPRDetect
    NC_000853.1	1779875	1780702	CRISPRDetect
    NC_000853.1	412     3105	CRISPRCASFinder
    NC_000853.1	369170	369731	CRISPRCASFinder
    NC_000853.1	396568	397133	CRISPRCASFinder
    NC_000853.1	409295	410923	CRISPRCASFinder
    NC_000853.1	1519912	1520474	CRISPRCASFinder
    NC_000853.1	1779810	1780701	CRISPRCASFinder

### Output files

A .clstr file will be generated to report the clusters of common CRISPRs detected from different software. Additionally, .log file will be generated to report unique occurences of each CRISPR arrays and first occurences in any given detection tool (lines with '*' in the .clstr file).

The format of .clst file will look like:
    (Accession) (Start) (Stop)  (Tool)          ... (Cluster_id)    (Similarity)    ... (Coverage)
    NC_000853.1	412     3106	CRISPRDetect	...	1	            *
    NC_000853.1	412     3105	CRISPRCASFinder	...	1	            0.9996288047512992	...	1.0
    NC_000853.1	369170	369732	CRISPRDetect	...	2	            *
    NC_000853.1	369170	369731	CRISPRCASFinder	...	2	            0.998220640569395	...	1.0
    NC_000853.1	396568	397134	CRISPRDetect	...	3	            *
    NC_000853.1	396568	397133	CRISPRCASFinder	...	3	            0.9982332155477032	...	1.0
    NC_000853.1	409295	410924	CRISPRDetect	...	4	            *
    NC_000853.1	409295	410923	CRISPRCASFinder	...	4	            0.9993861264579497	...	1.0
    NC_000853.1	1519912	1520476	CRISPRDetect	...	5	            *
    NC_000853.1	1519912	1520474	CRISPRCASFinder	...	5	            0.9964539007092199	...	1.0
    NC_000853.1	1631789	1632017	CRISPRDetect	...	6	            *
    NC_000853.1	1779810	1780701	CRISPRCASFinder	...	7	            *
    NC_000853.1	1779875	1780702	CRISPRDetect	...	7	            0.9270482603815937	...	0.9987908101571947

Finally, a venn diagram will be generated if the input file contains data from a maximum of 4 unique CRISPR detection tools.

R is required to generate plots with various CRAN packages (i.e., ggvenn and its depencencies). 
The R script is generated to install CRAN packages if they were not available in the system, 

CRISPRtoolcomp dependencies:

R                                       refer to https://rstudio-education.github.io/hopr/starting.html

tqdm                                    refer to https://pypi.org/project/tqdm/

Input Paramaters (REQUIRED):
----------------------------
	-i/--input      Filename		    Specify input file contain CRISPR array informations (with following headers separated with tab: Accession, Start, Stop, Tool).

Basic Options:
--------------
	-h/--help		HELP		        Shows this help text and exits the run.

      	'''))

parser.add_argument('-i', '--input', required=True, type=str, dest='filename',
                        help='Specify a input file.\n')

results = parser.parse_args()
filename = results.filename

orig_stdout = sys.stdout

def overlap_look(start1, end1, start2, end2):
    return max(max((end2-start1), 0) - max((end2-end1), 0) - max((start2-start1), 0), 0)

def dataframe(filename):

    uniq_id = str(uuid.uuid4())
    tmp = "/tmp/" + uniq_id

    df = pd.read_csv(filename, sep='\t', lineterminator='\n')

    for i in range(len(df.columns)):
        if "\r" in df.iloc[:,i:i+1].columns[0]:
            df[df.iloc[:,i:i+1].columns[0]]  = df[df.iloc[:,i:i+1].columns[0]].str.replace('\r','')
            df = df.rename(columns={df.iloc[:, i:i + 1].columns[0]: df.iloc[:, i:i + 1].columns[0].replace("\r", "")})

    df = df.sort_values(['Accession', 'Start'])

    n_tool = len(df.Tool.unique())

    df.to_csv(tmp, sep="\t", index=False)
    return tmp, n_tool

def cluster(filename,out,log):

    proc = subprocess.Popen("wc -l < " + filename, shell=True, stdout=subprocess.PIPE, text=True)
    length = int(proc.communicate()[0].split('\n')[0])

    ind = 0
    previous_acc = None

    with tqdm.tqdm(range(length+1)) as pbar:
        pbar.set_description('Reading...')
        with open(filename,'r') as file:
            for line in file:
                if len(line) != 0 and line.split("\t")[0] != "Accession":
                    pbar.update()
                    arr = line.split("\n")[0]
                    acc = arr.split("\t")[0]
                    start = arr.split("\t")[1]
                    end = arr.split("\t")[2]
                    if previous_acc == None:
                        acc1 = acc
                        start1 = float(start)
                        end1 = float(end)
                        previous_acc = acc1
                        f = open(log, 'a')
                        sys.stdout = f
                        print(line.split("\n")[0])
                        sys.stdout = orig_stdout

                        ind += 1

                        f = open(out, 'a')
                        sys.stdout = f
                        print(line.split("\n")[0] + "\t...\t" + str(ind) + '\t*')
                        sys.stdout = orig_stdout

                    else:
                        acc2 = acc
                        start2 = float(start)
                        end2 = float(end)
                        if acc1==acc2:
                            intercept = float(overlap_look(start1,end1, start2, end2))
                            if intercept == 0:
                                f = open(log, 'a')
                                sys.stdout = f
                                print(line.split("\n")[0])
                                sys.stdout = orig_stdout
                                acc1 = acc2
                                start1 = start2
                                end1 = end2
                                previous_acc = acc2

                                ind += 1

                                f = open(out, 'a')
                                sys.stdout = f
                                print(line.split("\n")[0] + "\t...\t" + str(ind) + '\t*')
                                sys.stdout = orig_stdout

                            else:
                                if (intercept/(end1-start1)) >= 0.5 or (intercept/(end2-start2)) >= 0.5:
                                    f = open(out, 'a')
                                    sys.stdout = f
                                    print(line.split("\n")[0] + "\t...\t" + str(ind) + "\t" + str(
                                        (intercept / (end1 - start1))) + "\t...\t" + str((intercept / (end2 - start2))))
                                    sys.stdout = orig_stdout

                                    acc1 = acc2
                                    start1 = start2
                                    end1 = end2
                                    previous_acc = acc2

                                else:
                                    f = open(log, 'a')
                                    sys.stdout = f
                                    print(line.split("\n")[0])
                                    sys.stdout = orig_stdout
                                    ind += 1

                                    f = open(out, 'a')
                                    sys.stdout = f
                                    print(line.split("\n")[0] + "\t...\t" + str(ind) + '\t*')
                                    sys.stdout = orig_stdout

                                    acc1 = acc2
                                    start1 = start2
                                    end1 = end2
                                    previous_acc = acc2

                        else:
                            acc1 = acc
                            start1 = float(start)
                            end1 = float(end)
                            previous_acc = acc1
                            f = open(log, 'a')
                            sys.stdout = f
                            print(line.split("\n")[0])
                            sys.stdout = orig_stdout

                            ind += 1

                            f = open(out, 'a')
                            sys.stdout = f
                            print(line.split("\n")[0] + "\t...\t" + str(ind) + '\t*')
                            sys.stdout = orig_stdout
    return out

def venn(file_input,file_output,wd):
    os.system("Rscript " + wd + "/CRISPRtoolcomp.R --input " + file_input + " --output " + file_output.split(".")[0] + "_venn > /dev/null")

def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor

if __name__ == '__main__':

    out = filename.split(".")[0] + ".clstr"
    log = filename.split(".")[0] + ".log"
    os.system('> ' + out)
    os.system('> ' + log)

    tmp,n_tool = dataframe(filename)
    out = cluster(tmp,out,log)

    if n_tool <= 4:
        wd = os.getcwd()
        spinner = spinning_cursor()

        p = multiprocessing.Process(target=venn,args=(out,filename,wd))
        p.start()
        p.join(timeout=0)

        while p.is_alive():
            sys.stdout.write("Generating Phylogeny and adding genemap panel " + next(spinner))
            sys.stdout.flush()
            time.sleep(0.1)
            sys.stdout.write('\r')

        print("Raw plot is exported as PDF files and can be found in " + os.getcwd())

        if "Rplots.pdf" in os.listdir(os.getcwd()):
            os.system("rm " + os.getcwd() + "/Rplots.pdf")
    else:
        print("Input file contains " + str(n_tool) + " unique CRISPR detection tools! Venn diagram only supports four or less tools at the same time. Skipping venn diagram step!")

    os.system("rm " + tmp)